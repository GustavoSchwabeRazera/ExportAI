from fastapi import APIRouter

from app.schemas import ExplicacaoRequest, ExplicacaoResponse
from app.services.explicador_ia import gerar_explicacao_ia

router = APIRouter(prefix="/api/v1", tags=["Explicacao"])


@router.post(
    "/explicacao",
    response_model=ExplicacaoResponse,
    summary="Explica uma recomendacao ExportAI em linguagem natural",
)
async def explicar_recomendacao(entrada: ExplicacaoRequest):
    explicacao, origem = await gerar_explicacao_ia(
        consulta=entrada.consulta.model_dump(),
        recomendacao=entrada.recomendacao.model_dump(),
    )
    return ExplicacaoResponse(
        explicacao=explicacao,
        origem=origem,
        aviso=(
            "A IA apenas explica os dados calculados pelo motor ExportAI; "
            "ela nao recalcula nem altera o score."
        ),
    )
