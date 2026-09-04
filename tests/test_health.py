from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_retorna_ok():
    resposta = client.get("/health")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "ok"
    assert corpo["servico_carregado"] is True
    assert all(corpo["arquivos"].values())
