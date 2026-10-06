"""Busca no catálogo oficial, com termos relacionados como alternativa."""
from functools import lru_cache
import re
import unicodedata

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.routes.catalogos import carregar_indice, erro

router = APIRouter(prefix="/api/v1", tags=["Catalogos"])

# Relações para descoberta; nunca substituem a classificação fiscal escolhida.
GRUPOS_RELACIONADOS = (
    ("linguica", "linguicas", "enchidos", "enchido", "embutido", "embutidos", "salsicha", "salsichas"),
    ("camiseta", "camisetas", "t shirt", "t shirts"),
    ("tenis", "sapato", "sapatos", "calcado", "calcados"),
    ("celular", "celulares", "smartphone", "smartphones", "telefone"),
    ("notebook", "laptop", "computador portatil", "maquinas automaticas para processamento de dados portateis"),
)


def normalizar_busca(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", valor.casefold())
    texto = "".join(letra for letra in texto if not unicodedata.combining(letra))
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


class ProdutoSugestao(BaseModel):
    ncm: str
    hs6: str
    descricao_ncm: str


class ProdutosResponse(BaseModel):
    total: int
    produtos: list[ProdutoSugestao]
    busca_aproximada: bool
    termos_relacionados: list[str]


@lru_cache(maxsize=1)
def indice_busca() -> pd.DataFrame:
    indice = carregar_indice().dropna(subset=["NCM", "HS6", "descricao_ncm"]).copy()
    indice = indice.drop_duplicates(["NCM", "HS6"])
    indice["_busca"] = indice["descricao_ncm"].map(normalizar_busca)
    return indice.sort_values(["descricao_ncm", "NCM"])


def selecionar_produtos(indice: pd.DataFrame, consulta: str, limite: int) -> ProdutosResponse:
    termo = normalizar_busca(consulta)
    relacionados: list[str] = []
    if not termo:
        return ProdutosResponse(total=0, produtos=[], busca_aproximada=False, termos_relacionados=[])
    if termo.isdigit():
        mascara = indice["NCM"].str.startswith(termo) | indice["HS6"].str.startswith(termo)
    else:
        mascara = indice["_busca"].str.contains(termo, regex=False)
    aproximada = False
    if not mascara.any() and not termo.isdigit():
        for grupo in GRUPOS_RELACIONADOS:
            if termo in grupo:
                relacionados = [alias for alias in grupo if alias != termo]
                break
        for alias in relacionados:
            mascara = indice["_busca"].str.contains(r"\b" + re.escape(alias) + r"\b", regex=True)
            if mascara.any():
                relacionados = [alias]
                break
        aproximada = bool(mascara.any())
    linhas = indice.loc[mascara]
    produtos = [ProdutoSugestao(ncm=str(linha.NCM), hs6=str(linha.HS6), descricao_ncm=str(linha.descricao_ncm))
                for linha in linhas.head(limite).itertuples(index=False)]
    return ProdutosResponse(total=len(linhas), produtos=produtos, busca_aproximada=aproximada,
                            termos_relacionados=relacionados if aproximada else [])


@router.get("/produtos", response_model=ProdutosResponse, summary="Busca produtos por nome ou código",
            description="Prioriza correspondências diretas. Sem resultados, busca termos relacionados conhecidos. O usuário deve confirmar o NCM/HS6 da sugestão.")
def buscar_produtos(q: str = Query(min_length=2, max_length=120), limite: int = Query(default=10, ge=1, le=50)) -> ProdutosResponse:
    try:
        return selecionar_produtos(indice_busca(), q, limite)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=erro("CATALOGO_PRODUTOS_INDISPONIVEL", "Não foi possível consultar o catálogo de produtos.")) from exc
