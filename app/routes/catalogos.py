from functools import lru_cache
import json
import re
import unicodedata

import pandas as pd
from fastapi import APIRouter, HTTPException, Path, Query

from app.catalog_schemas import (
    BuscaProdutosResponse,
    HS6InfoResponse,
    ListaPaisesResponse,
    NCMInfoResponse,
    PaisCatalogo,
    ProdutoSugestao,
)
from app.config import BASE_CONSULTA, CATALOGO_HS6, DATA_DIR, INDICE_NCM_HS6
from app.presentation import nome_pais_portugues
from app.schemas import ErroResponse

router = APIRouter(prefix="/api/v1", tags=["Catalogos"])

RESPOSTAS_ERRO = {
    400: {"model": ErroResponse, "description": "Codigo com formato invalido."},
    404: {"model": ErroResponse, "description": "Codigo nao encontrado."},
    500: {"model": ErroResponse, "description": "Falha ao ler os catalogos."},
}


def erro(codigo: str, mensagem: str) -> dict:
    return {"erro": {"codigo": codigo, "mensagem": mensagem}}


def normalizar_codigo(valor: str, tamanho: int, nome: str) -> str:
    digitos = re.sub(r"\D", "", str(valor))
    if len(digitos) != tamanho:
        raise HTTPException(
            status_code=400,
            detail=erro(
                "CODIGO_INVALIDO",
                f"{nome} invalido. Informe exatamente {tamanho} digitos.",
            ),
        )
    return digitos


def normalizar_texto_busca(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", str(valor).strip())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.casefold()
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


@lru_cache(maxsize=1)
def carregar_indice() -> pd.DataFrame:
    df = pd.read_parquet(INDICE_NCM_HS6).copy()
    df["NCM"] = df["NCM"].astype("string").str.zfill(8)
    df["HS6"] = df["HS6"].astype("string").str.zfill(6)
    return df


@lru_cache(maxsize=1)
def carregar_catalogo_hs6() -> pd.DataFrame:
    df = pd.read_parquet(CATALOGO_HS6).copy()
    df["HS6"] = df["HS6"].astype("string").str.zfill(6)
    return df


@lru_cache(maxsize=1)
def carregar_catalogo_produtos() -> pd.DataFrame:
    indice = carregar_indice()
    catalogo = carregar_catalogo_hs6()
    colunas_catalogo = [
        "HS6",
        "paises_avaliados",
        "tem_score_exportai",
    ]
    disponiveis = [coluna for coluna in colunas_catalogo if coluna in catalogo.columns]
    produtos = indice.merge(
        catalogo[disponiveis].drop_duplicates("HS6"),
        on="HS6",
        how="left",
    )
    produtos["descricao_ncm"] = produtos.get(
        "descricao_ncm",
        pd.Series(dtype="string"),
    ).fillna("").astype(str)
    produtos["descricao_busca"] = produtos["descricao_ncm"].map(normalizar_texto_busca)
    produtos["tem_score_exportai"] = produtos.get(
        "tem_score_exportai",
        pd.Series(False, index=produtos.index),
    ).fillna(False).astype(bool)
    produtos["paises_avaliados"] = produtos.get(
        "paises_avaliados",
        pd.Series(0, index=produtos.index),
    ).fillna(0).astype(int)
    return produtos


@lru_cache(maxsize=1)
def carregar_paises() -> ListaPaisesResponse:
    catalogo_json = DATA_DIR / "catalogo_paises.json"
    itens = []
    if catalogo_json.exists():
        registros = json.loads(catalogo_json.read_text(encoding="utf-8"))
    else:
        df = pd.read_parquet(BASE_CONSULTA, columns=["ISO3", "pais"])
        df["ISO3"] = df["ISO3"].astype("string").str.upper()
        df = df.dropna(subset=["ISO3"]).drop_duplicates("ISO3")
        registros = df[["ISO3", "pais"]].to_dict(orient="records")

    for registro in registros:
        iso3 = registro.get("ISO3")
        nome_atual = registro.get("pais")
        nome = nome_pais_portugues(str(iso3), nome_atual)
        itens.append(PaisCatalogo(iso3=str(iso3), nome=nome or str(iso3)))
    itens.sort(key=lambda item: item.nome.casefold())
    return ListaPaisesResponse(total=len(itens), paises=itens)


def inteiro(valor, padrao=0) -> int:
    return padrao if pd.isna(valor) else int(valor)


def numero(valor):
    return None if pd.isna(valor) else float(valor)


def texto(valor):
    return None if pd.isna(valor) else str(valor)


def montar_sugestao_produto(linha: pd.Series, tipo_codigo: str) -> ProdutoSugestao:
    ncm = texto(linha.get("NCM"))
    hs6 = str(linha.get("HS6")).zfill(6)
    codigo = ncm if tipo_codigo == "NCM" and ncm else hs6
    descricao = texto(linha.get("descricao_ncm")) or f"Produto SH6/HS6 {hs6}"
    return ProdutoSugestao(
        tipo_codigo=tipo_codigo,
        codigo=str(codigo),
        ncm=ncm,
        hs6=hs6,
        descricao=descricao,
        existe_no_motor=bool(linha.get("tem_score_exportai", False)),
        paises_avaliados=inteiro(linha.get("paises_avaliados", 0)),
    )


@router.get(
    "/paises",
    response_model=ListaPaisesResponse,
    responses={500: RESPOSTAS_ERRO[500]},
    summary="Lista paises disponiveis",
    description="Retorna os paises do motor com ISO3 e nome em portugues.",
)
def listar_paises() -> ListaPaisesResponse:
    try:
        return carregar_paises()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=erro("CATALOGO_PAISES_INDISPONIVEL", str(exc)),
        ) from exc


@router.get(
    "/produtos",
    response_model=BuscaProdutosResponse,
    responses={500: RESPOSTAS_ERRO[500]},
    summary="Busca produtos por nome, NCM ou SH6/HS6",
    description=(
        "Retorna sugestoes para autocomplete. O usuario pode digitar parte da "
        "descricao do produto, uma NCM de 8 digitos ou um SH6/HS6 de 6 digitos."
    ),
)
def buscar_produtos(
    q: str = Query(min_length=1, max_length=80, description="Texto, NCM ou SH6/HS6."),
    limite: int = Query(default=10, ge=1, le=30),
) -> BuscaProdutosResponse:
    try:
        produtos = carregar_catalogo_produtos()
        termo = normalizar_texto_busca(q)
        digitos = re.sub(r"\D", "", q)

        if len(digitos) == 8:
            candidatos = produtos.loc[produtos["NCM"].eq(digitos)].copy()
            candidatos["prioridade_busca"] = 0
            tipo_codigo = "NCM"
        elif len(digitos) == 6:
            candidatos = produtos.loc[produtos["HS6"].eq(digitos)].copy()
            candidatos["prioridade_busca"] = 0
            tipo_codigo = "HS6"
        elif len(termo) < 2:
            return BuscaProdutosResponse(total=0, resultados=[])
        else:
            termos = termo.split()
            mascara = pd.Series(True, index=produtos.index)
            for palavra in termos:
                mascara = mascara & produtos["descricao_busca"].str.contains(
                    re.escape(palavra),
                    na=False,
                    regex=True,
                )
            candidatos = produtos.loc[mascara].copy()
            if candidatos.empty:
                return BuscaProdutosResponse(total=0, resultados=[])
            candidatos["prioridade_busca"] = candidatos["descricao_busca"].map(
                lambda descricao: 0 if descricao.startswith(termo) else 1
            )
            tipo_codigo = "NCM"

        candidatos = candidatos.sort_values(
            [
                "prioridade_busca",
                "tem_score_exportai",
                "paises_avaliados",
                "NCM",
            ],
            ascending=[True, False, False, True],
            kind="mergesort",
        ).head(limite)

        resultados = [
            montar_sugestao_produto(linha, tipo_codigo)
            for _, linha in candidatos.iterrows()
        ]
        return BuscaProdutosResponse(total=len(resultados), resultados=resultados)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=erro("BUSCA_PRODUTOS_INDISPONIVEL", str(exc)),
        ) from exc


@router.get(
    "/ncm/{ncm}",
    response_model=NCMInfoResponse,
    responses=RESPOSTAS_ERRO,
    summary="Valida e descreve uma NCM",
)
def consultar_ncm(
    ncm: str = Path(description="NCM com 8 digitos, com ou sem pontuacao."),
) -> NCMInfoResponse:
    codigo = normalizar_codigo(ncm, 8, "NCM")
    try:
        indice = carregar_indice()
        linhas = indice.loc[indice["NCM"].eq(codigo)]
        if linhas.empty:
            raise HTTPException(
                status_code=404,
                detail=erro("NCM_NAO_ENCONTRADA", f"NCM {codigo} nao encontrada."),
            )
        hs6_unicos = linhas["HS6"].dropna().astype(str).unique().tolist()
        if len(hs6_unicos) != 1:
            raise HTTPException(
                status_code=500,
                detail=erro("NCM_HS6_AMBIGUO", f"NCM {codigo} possui correspondencias ambiguas."),
            )
        hs6 = hs6_unicos[0]
        descricoes = linhas.get("descricao_ncm", pd.Series(dtype="string")).dropna()
        descricao = str(descricoes.iloc[0]) if not descricoes.empty else None
        catalogo = carregar_catalogo_hs6()
        linha_hs6 = catalogo.loc[catalogo["HS6"].eq(hs6)]
        existe = bool(not linha_hs6.empty and linha_hs6.iloc[0].get("tem_score_exportai", False))
        paises = 0 if linha_hs6.empty else inteiro(linha_hs6.iloc[0].get("paises_avaliados", 0))
        return NCMInfoResponse(
            ncm=codigo,
            descricao_ncm=descricao,
            hs6=hs6,
            existe_no_motor=existe,
            paises_avaliados=paises,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=erro("CATALOGO_NCM_INDISPONIVEL", str(exc)),
        ) from exc


@router.get(
    "/hs6/{hs6}",
    response_model=HS6InfoResponse,
    responses=RESPOSTAS_ERRO,
    summary="Consulta a cobertura de um HS6",
)
def consultar_hs6(
    hs6: str = Path(description="HS6 com exatamente 6 digitos."),
) -> HS6InfoResponse:
    codigo = normalizar_codigo(hs6, 6, "HS6")
    try:
        catalogo = carregar_catalogo_hs6()
        linhas = catalogo.loc[catalogo["HS6"].eq(codigo)]
        if linhas.empty:
            raise HTTPException(
                status_code=404,
                detail=erro("HS6_NAO_ENCONTRADO", f"HS6 {codigo} nao encontrado."),
            )
        linha = linhas.iloc[0]
        return HS6InfoResponse(
            hs6=codigo,
            quantidade_ncm_bridge=inteiro(linha.get("quantidade_ncm_bridge", 0)),
            ncm_exemplo=texto(linha.get("ncm_exemplo")),
            descricoes_disponiveis=inteiro(linha.get("descricoes_disponiveis", 0)),
            paises_avaliados=inteiro(linha.get("paises_avaliados", 0)),
            score_minimo=numero(linha.get("score_minimo")),
            score_mediano=numero(linha.get("score_mediano")),
            score_maximo=numero(linha.get("score_maximo")),
            tem_ncm_na_bridge=bool(linha.get("tem_ncm_na_bridge", False)),
            tem_score_exportai=bool(linha.get("tem_score_exportai", False)),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=erro("CATALOGO_HS6_INDISPONIVEL", str(exc)),
        ) from exc
