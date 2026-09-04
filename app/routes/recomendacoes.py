from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_servico_exportai
from app.presentation import traduzir_recomendacoes
from app.schemas import ConsultaRecomendacaoRequest, ConsultaRecomendacaoResponse, ErroResponse
from app.services.servico_consulta_exportai import BaseConsultaError, CodigoInvalidoError, CodigoNaoEncontradoError, ServicoConsultaExportAI

router = APIRouter(prefix="/api/v1", tags=["Recomendacoes"])
RESPOSTAS_ERRO = {
    400: {"model": ErroResponse, "description": "Codigo ou parametro invalido."},
    404: {"model": ErroResponse, "description": "NCM, HS6 ou mercados nao encontrados."},
    422: {"model": ErroResponse, "description": "Requisicao fora do contrato."},
    500: {"model": ErroResponse, "description": "Falha na base do ExportAI."},
}

def detalhe_erro(codigo, mensagem):
    return {"erro": {"codigo": codigo, "mensagem": mensagem}}

@router.post("/recomendacoes", response_model=ConsultaRecomendacaoResponse, responses=RESPOSTAS_ERRO, summary="Recomenda mercados internacionais")
def recomendar_mercados(entrada: ConsultaRecomendacaoRequest, servico: ServicoConsultaExportAI = Depends(get_servico_exportai)):
    try:
        resultado = servico.consultar(
            ncm=entrada.ncm,
            hs6=entrada.hs6,
            paises_excluidos=entrada.paises_ja_exportados,
            quantidade=entrada.quantidade,
            confianca_minima=entrada.confianca_minima,
            somente_novas=entrada.somente_novas,
        )
        resultado = traduzir_recomendacoes(resultado)
        return ConsultaRecomendacaoResponse.model_validate(resultado)
    except CodigoInvalidoError as erro:
        raise HTTPException(400, detail=detalhe_erro("CODIGO_INVALIDO", str(erro))) from erro
    except CodigoNaoEncontradoError as erro:
        raise HTTPException(404, detail=detalhe_erro("CODIGO_NAO_ENCONTRADO", str(erro))) from erro
    except BaseConsultaError as erro:
        raise HTTPException(500, detail=detalhe_erro("BASE_CONSULTA_INVALIDA", str(erro))) from erro
