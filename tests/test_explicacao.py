from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _primeira_recomendacao():
    resposta = client.post(
        "/api/v1/recomendacoes",
        json={"ncm": "09011110", "quantidade": 1},
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    return corpo["consulta"], corpo["recomendacoes"][0]


def test_explicacao_sem_chave_usa_fallback_local():
    consulta, recomendacao = _primeira_recomendacao()

    resposta = client.post(
        "/api/v1/explicacao",
        json={"consulta": consulta, "recomendacao": recomendacao},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["origem"] == "fallback_local"
    assert recomendacao["pais"] in corpo["explicacao"]
    assert "nao recalcula" in corpo["aviso"].lower()


def test_openapi_documenta_endpoint_explicacao():
    resposta = client.get("/openapi.json")
    assert resposta.status_code == 200
    assert "/api/v1/explicacao" in resposta.json()["paths"]
