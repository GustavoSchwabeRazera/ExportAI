from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_lista_paises_ordenada_e_com_portugues():
    resposta = client.get("/api/v1/paises")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["total"] > 0
    por_iso = {item["iso3"]: item["nome"] for item in corpo["paises"]}
    assert por_iso["DEU"] == "Alemanha"
    assert por_iso["USA"] == "Estados Unidos"
    nomes = [item["nome"].casefold() for item in corpo["paises"]]
    assert nomes == sorted(nomes)


def test_consulta_ncm_valida():
    resposta = client.get("/api/v1/ncm/09011110")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["ncm"] == "09011110"
    assert corpo["hs6"] == "090111"
    assert corpo["descricao_ncm"]
    assert corpo["existe_no_motor"] is True
    assert corpo["paises_avaliados"] == 232


def test_consulta_ncm_com_pontuacao():
    resposta = client.get("/api/v1/ncm/09.01.11.10")
    assert resposta.status_code == 200
    assert resposta.json()["ncm"] == "09011110"


def test_ncm_invalida_retorna_400_padronizado():
    resposta = client.get("/api/v1/ncm/123")
    assert resposta.status_code == 400
    assert resposta.json()["erro"]["codigo"] == "CODIGO_INVALIDO"


def test_ncm_ausente_retorna_404_padronizado():
    resposta = client.get("/api/v1/ncm/99999999")
    assert resposta.status_code == 404
    assert resposta.json()["erro"]["codigo"] == "NCM_NAO_ENCONTRADA"


def test_consulta_hs6_valido():
    resposta = client.get("/api/v1/hs6/090111")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["hs6"] == "090111"
    assert corpo["quantidade_ncm_bridge"] >= 1
    assert corpo["paises_avaliados"] == 232
    assert corpo["tem_score_exportai"] is True
    assert 0 <= corpo["score_minimo"] <= corpo["score_mediano"] <= corpo["score_maximo"] <= 100


def test_hs6_invalido_retorna_400():
    resposta = client.get("/api/v1/hs6/123")
    assert resposta.status_code == 400
    assert resposta.json()["erro"]["codigo"] == "CODIGO_INVALIDO"


def test_openapi_documenta_catalogos():
    openapi = client.get("/openapi.json").json()
    caminhos = openapi["paths"]
    assert "/api/v1/paises" in caminhos
    assert "/api/v1/ncm/{ncm}" in caminhos
    assert "/api/v1/hs6/{hs6}" in caminhos
