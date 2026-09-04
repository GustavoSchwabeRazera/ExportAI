from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
ENDPOINT = "/api/v1/recomendacoes"

def test_cors_origem_local_permitida():
    resposta = client.options(ENDPOINT, headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    assert resposta.status_code == 200
    assert resposta.headers["access-control-allow-origin"] == "http://localhost:5173"

def test_erro_422_padronizado():
    resposta = client.post(ENDPOINT, json={"ncm": "09011110", "hs6": "090111"})
    assert resposta.status_code == 422
    corpo = resposta.json()
    assert corpo["erro"]["codigo"] == "REQUISICAO_INVALIDA"
    assert corpo["erro"]["detalhes"]

def test_erro_404_padronizado_sem_detail():
    resposta = client.post(ENDPOINT, json={"ncm": "99999999"})
    assert resposta.status_code == 404
    corpo = resposta.json()
    assert "detail" not in corpo
    assert corpo["erro"]["codigo"] == "CODIGO_NAO_ENCONTRADO"

def test_paises_retornam_em_portugues():
    resposta = client.post(ENDPOINT, json={
        "ncm": "09011110",
        "paises_ja_exportados": ["Argentina", "Estados Unidos", "Chile"],
        "quantidade": 5,
    })
    assert resposta.status_code == 200
    nomes = {item["ISO3"]: item["pais"] for item in resposta.json()["recomendacoes"]}
    assert nomes["DEU"] == "Alemanha"
    assert nomes["ITA"] == "Itália"
    assert nomes["SGP"] == "Singapura"
    assert nomes["JPN"] == "Japão"

def test_openapi_exemplo_real_e_422_padronizado():
    openapi = client.get("/openapi.json").json()
    schema = openapi["components"]["schemas"]["ConsultaRecomendacaoRequest"]
    assert schema["examples"][0]["ncm"] == "09011110"
    respostas = openapi["paths"][ENDPOINT]["post"]["responses"]
    assert respostas["422"]["content"]["application/json"]["schema"]["$ref"].endswith("/ErroResponse")
