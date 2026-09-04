from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_exclusao_de_todos_paises_disponiveis_nao_reintroduz_mercados():
    catalogo = client.get("/api/v1/paises").json()["paises"]
    todos_iso3 = [item["iso3"] for item in catalogo]
    resposta = client.post(
        "/api/v1/recomendacoes",
        json={
            "ncm": "09011110",
            "paises_ja_exportados": todos_iso3,
            "quantidade": 5,
        },
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["cobertura"]["paises_apos_exclusoes"] == 0
    assert corpo["cobertura"]["recomendacoes_retornadas"] == 0
    assert corpo["recomendacoes"] == []
    assert corpo["metodologia"]["pais_excluido_reintroduzido"] is False
