from functools import lru_cache
import re

import pandas as pd
from fastapi import APIRouter, HTTPException, Path

from app.catalog_schemas import (
    HS6InfoResponse,
    ListaPaisesResponse,
    NCMInfoResponse,
    PaisCatalogo,
)
from app.config import BASE_CONSULTA, CATALOGO_HS6, INDICE_NCM_HS6
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
def carregar_paises() -> ListaPaisesResponse:
    df = pd.read_parquet(BASE_CONSULTA, columns=["ISO3", "pais"])
    df["ISO3"] = df["ISO3"].astype("string").str.upper()
    df = df.dropna(subset=["ISO3"]).drop_duplicates("ISO3")
    itens = []
    for iso3, nome_atual in df[["ISO3", "pais"]].itertuples(index=False):
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
