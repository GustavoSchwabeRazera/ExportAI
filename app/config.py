from pathlib import Path
import os

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("EXPORTAI_DATA_DIR", BACKEND_DIR / "data"))

BASE_CONSULTA = DATA_DIR / "base_consulta_hs6_pais_completa.parquet"
INDICE_NCM_HS6 = DATA_DIR / "indice_ncm_hs6.parquet"
CATALOGO_HS6 = DATA_DIR / "catalogo_hs6_consulta.parquet"
RESUMO_BASE = DATA_DIR / "BASE_CONSULTA_EXPORTAI_V2_RESUMO.json"

API_TITLE = "ExportAI API"
API_VERSION = "0.2.0"
API_PREFIX = "/api/v1"

_CORS_PADRAO = "http://localhost:5173,http://127.0.0.1:5173"
CORS_ORIGINS = [
    origem.strip().rstrip("/")
    for origem in os.getenv("EXPORTAI_CORS_ORIGINS", _CORS_PADRAO).split(",")
    if origem.strip()
]
