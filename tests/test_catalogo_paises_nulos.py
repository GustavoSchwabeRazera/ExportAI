import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.presentation import nome_pais_portugues, valor_texto_ou_none

client = TestClient(app)


def test_valor_texto_trata_pd_na_sem_ambiguidade():
    assert valor_texto_ou_none(pd.NA) is None
    assert valor_texto_ou_none(None) is None
    assert valor_texto_ou_none("") is None
    assert valor_texto_ou_none("  Brasil  ") == "Brasil"


def test_nome_pais_com_nome_atual_nulo_nao_falha():
    resultado = nome_pais_portugues("ZZZ", pd.NA)
    assert resultado is None


def test_catalogo_paises_retorna_200_sem_nomes_vazios():
    resposta = client.get("/api/v1/paises")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["total"] == len(corpo["paises"])
    assert corpo["total"] > 0
    assert all(item["iso3"] for item in corpo["paises"])
    assert all(item["nome"] for item in corpo["paises"])


def test_catalogo_paises_mantem_traducoes_principais():
    resposta = client.get("/api/v1/paises")
    assert resposta.status_code == 200
    por_iso = {item["iso3"]: item["nome"] for item in resposta.json()["paises"]}
    assert por_iso["DEU"] == "Alemanha"
    assert por_iso["ITA"] == "Itália"
    assert por_iso["JPN"] == "Japão"
    assert por_iso["USA"] == "Estados Unidos"
