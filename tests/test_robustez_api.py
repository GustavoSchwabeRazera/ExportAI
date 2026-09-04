from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
ENDPOINT = "/api/v1/recomendacoes"


def post(payload):
    return client.post(ENDPOINT, json=payload)


def test_ncm_com_letras_retorna_422():
    resposta = post({"ncm": "abcdefgh"})
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "REQUISICAO_INVALIDA"


def test_quantidade_limites_validos():
    assert post({"ncm": "09011110", "quantidade": 1}).status_code == 200
    assert post({"ncm": "09011110", "quantidade": 258}).status_code == 200


def test_lista_exclusoes_remove_duplicados():
    resposta = post({
        "ncm": "09011110",
        "paises_ja_exportados": ["Argentina", "argentina", "ARG"],
        "quantidade": 2,
    })
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["exclusoes"]["iso3_reconhecidos"] == ["ARG"]
    assert all(item["ISO3"] != "ARG" for item in corpo["recomendacoes"])


def test_pais_nao_reconhecido_e_informado():
    resposta = post({
        "ncm": "09011110",
        "paises_ja_exportados": ["Atlantida"],
        "quantidade": 2,
    })
    assert resposta.status_code == 200
    assert resposta.json()["exclusoes"]["nao_reconhecidas"] == ["Atlantida"]


def test_resultado_respeita_ordenacao_e_limites():
    resposta = post({"ncm": "09011110", "quantidade": 20})
    assert resposta.status_code == 200
    itens = resposta.json()["recomendacoes"]
    assert len(itens) <= 20
    assert [x["ranking_personalizado"] for x in itens] == list(range(1, len(itens) + 1))
    assert all(0 <= x["score_exportai"] <= 100 for x in itens)
    assert all(0 <= x["indice_cobertura"] <= 100 for x in itens)
    assert all(len(x["ISO3"]) == 3 and x["ISO3"].isalpha() for x in itens)
    chaves = [
        (-x["score_exportai"], -x["indice_cobertura"], x["ranking_global_no_hs6"], x["ISO3"])
        for x in itens
    ]
    assert chaves == sorted(chaves)


def test_somente_novas_com_confianca_alta_e_consistente():
    resposta = post({
        "ncm": "09011110",
        "quantidade": 10,
        "somente_novas": True,
        "confianca_minima": "ALTA",
    })
    assert resposta.status_code == 200
    itens = resposta.json()["recomendacoes"]
    assert all(x["tipo_oportunidade"] == "NOVA_OPORTUNIDADE_WITS" for x in itens)
    assert all(x["faixa_confianca"] == "ALTA" for x in itens)


def test_request_id_recebido_e_devolvido():
    resposta = client.get("/health", headers={"X-Request-ID": "teste-exportai-123"})
    assert resposta.status_code == 200
    assert resposta.headers["X-Request-ID"] == "teste-exportai-123"
    assert float(resposta.headers["X-Process-Time-Ms"]) >= 0


def test_request_id_gerado_quando_ausente():
    resposta = client.get("/health")
    assert resposta.status_code == 200
    assert resposta.headers.get("X-Request-ID")
    assert resposta.headers.get("X-Process-Time-Ms")
