from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import API_TITLE, API_VERSION, CORS_ORIGINS
from app.errors import registrar_tratadores_erros
from app.observability import configurar_logging, registrar_middleware_observabilidade
from app.routes.catalogos import router as catalogos_router
from app.routes.health import router as health_router
from app.routes.recomendacoes import router as recomendacoes_router

configurar_logging()
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description="API do ExportAI para recomendacao personalizada de mercados internacionais por NCM ou HS6.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Process-Time-Ms"],
)
registrar_middleware_observabilidade(app)
registrar_tratadores_erros(app)
app.include_router(health_router)
app.include_router(catalogos_router)
app.include_router(recomendacoes_router)


@app.get("/", tags=["Raiz"], summary="Apresenta a API")
def raiz():
    return {
        "aplicacao": API_TITLE,
        "versao": API_VERSION,
        "status": "online",
        "documentacao": "/docs",
        "health": "/health",
        "recomendacoes": "/api/v1/recomendacoes",
        "paises": "/api/v1/paises",
    }
