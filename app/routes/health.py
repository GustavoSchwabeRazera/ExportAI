from pathlib import Path

from fastapi import APIRouter, Depends

from app.config import BASE_CONSULTA, CATALOGO_HS6, INDICE_NCM_HS6
from app.dependencies import get_servico_exportai
from app.services.servico_consulta_exportai import ServicoConsultaExportAI

router = APIRouter(tags=["Saude"])


@router.get("/health", summary="Verifica a saude da API")
def health(
    servico: ServicoConsultaExportAI = Depends(get_servico_exportai),
) -> dict:
    arquivos = {
        "base_consulta": BASE_CONSULTA.exists(),
        "indice_ncm_hs6": INDICE_NCM_HS6.exists(),
        "catalogo_hs6": CATALOGO_HS6.exists(),
    }
    saudavel = all(arquivos.values()) and servico is not None
    return {
        "status": "ok" if saudavel else "erro",
        "servico_carregado": servico is not None,
        "arquivos": arquivos,
    }
