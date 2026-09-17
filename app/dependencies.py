from functools import lru_cache

from app.config import BASE_CONSULTA, INDICE_NCM_HS6
from app.services.servico_consulta_exportai import ServicoConsultaExportAI


@lru_cache(maxsize=1)
def get_servico_exportai() -> ServicoConsultaExportAI:
    return ServicoConsultaExportAI(
        caminho_base=BASE_CONSULTA,
        caminho_indice=INDICE_NCM_HS6,
    )
