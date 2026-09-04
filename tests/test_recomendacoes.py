from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
ENDPOINT = "/api/v1/recomendacoes"


def test_recomendacao_por_ncm_com_exclusoes():
    resposta = client.post(
        ENDPOINT,
        json={
            "ncm": "09011110",
            "paises_ja_exportados": [
                "Argentina",
                "Estados Unidos",
                "Chile",
            ],
            "quantidade": 5,
            "confianca_minima": "LIMITADA",
            "somente_novas": False,
        },
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["consulta"]["ncm"] == "09011110"
    assert corpo["consulta"]["hs6"] == "090111"
    assert corpo["exclusoes"]["iso3_reconhecidos"] == ["ARG", "CHL", "USA"]
    assert corpo["cobertura"]["recomendacoes_retornadas"] == 5

    iso3_retornados = {item["ISO3"] for item in corpo["recomendacoes"]}
    assert not iso3_retornados.intersection({"ARG", "CHL", "USA"})
    assert [item["ranking_personalizado"] for item in corpo["recomendacoes"]] == [1, 2, 3, 4, 5]


def test_recomendacao_por_hs6():
    resposta = client.post(
        ENDPOINT,
        json={
            "hs6": "090111",
            "quantidade": 3,
            "confianca_minima": "ALTA",
        },
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["consulta"]["ncm"] is None
    assert corpo["consulta"]["hs6"] == "090111"
    assert len(corpo["recomendacoes"]) == 3
    assert all(item["faixa_confianca"] == "ALTA" for item in corpo["recomendacoes"])


def test_recomendacao_somente_novas():
    resposta = client.post(
        ENDPOINT,
        json={
            "ncm": "09011110",
            "quantidade": 5,
            "somente_novas": True,
        },
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["recomendacoes"]
    assert all(
        item["tipo_oportunidade"] == "NOVA_OPORTUNIDADE_WITS"
        for item in corpo["recomendacoes"]
    )


def test_ncm_nao_encontrada_retorna_404():
    resposta = client.post(
        ENDPOINT,
        json={"ncm": "99999999", "quantidade": 5},
    )

    assert resposta.status_code == 404

    corpo = resposta.json()

    assert "detail" not in corpo
    assert corpo["erro"]["codigo"] == "CODIGO_NAO_ENCONTRADO"
    assert corpo["erro"]["mensagem"]


def test_request_invalido_retorna_422():
    resposta = client.post(
        ENDPOINT,
        json={
            "ncm": "09011110",
            "hs6": "090111",
            "quantidade": 0,
        },
    )
    assert resposta.status_code == 422


def test_openapi_documenta_endpoint_e_schemas():
    resposta = client.get("/openapi.json")
    assert resposta.status_code == 200
    openapi = resposta.json()
    assert ENDPOINT in openapi["paths"]
    schemas = openapi["components"]["schemas"]
    assert "ConsultaRecomendacaoRequest" in schemas
    assert "ConsultaRecomendacaoResponse" in schemas
