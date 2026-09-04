import logging
import time
import uuid

from fastapi import Request

logger = logging.getLogger("exportai.api")


def configurar_logging() -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    logger.setLevel(logging.INFO)


def registrar_middleware_observabilidade(app) -> None:
    @app.middleware("http")
    async def observabilidade(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        inicio = time.perf_counter()
        status_code = 500
        try:
            resposta = await call_next(request)
            status_code = resposta.status_code
            return resposta
        finally:
            duracao_ms = (time.perf_counter() - inicio) * 1000
            if "resposta" in locals():
                resposta.headers["X-Request-ID"] = request_id
                resposta.headers["X-Process-Time-Ms"] = f"{duracao_ms:.2f}"
            logger.info(
                "request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
                request_id,
                request.method,
                request.url.path,
                status_code,
                duracao_ms,
            )
