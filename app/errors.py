from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError


def resposta_erro(status_code: int, codigo: str, mensagem: str, detalhes=None):
    conteudo = {"erro": {"codigo": codigo, "mensagem": mensagem}}
    if detalhes is not None:
        conteudo["erro"]["detalhes"] = detalhes
    return JSONResponse(status_code=status_code, content=conteudo)


def registrar_tratadores_erros(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def tratar_validacao_requisicao(
        request: Request, erro: RequestValidationError
    ):
        detalhes = []
        for item in erro.errors():
            detalhes.append({
                "campo": ".".join(str(p) for p in item.get("loc", [])),
                "mensagem": item.get("msg", "Valor invalido"),
                "tipo": item.get("type", "validation_error"),
            })
        return resposta_erro(
            422,
            "REQUISICAO_INVALIDA",
            "A requisicao possui campos invalidos.",
            detalhes,
        )

    @app.exception_handler(HTTPException)
    async def tratar_http(request: Request, erro: HTTPException):
        detalhe = erro.detail
        if isinstance(detalhe, dict) and "erro" in detalhe:
            return JSONResponse(status_code=erro.status_code, content=detalhe)
        return resposta_erro(
            erro.status_code,
            "ERRO_HTTP",
            str(detalhe),
        )

    @app.exception_handler(ValidationError)
    async def tratar_resposta_invalida(request: Request, erro: ValidationError):
        return resposta_erro(
            500,
            "RESPOSTA_INVALIDA",
            "A API produziu uma resposta fora do contrato esperado.",
        )
