import pandas as pd
from app.routes.produtos import normalizar_busca, selecionar_produtos


def catalogo():
    df = pd.DataFrame([
        {"NCM": "16010000", "HS6": "160100", "descricao_ncm": "Enchidos e produtos semelhantes, de carne"},
        {"NCM": "09011110", "HS6": "090111", "descricao_ncm": "Café não torrado, em grão"},
    ])
    df["_busca"] = df.descricao_ncm.map(normalizar_busca)
    return df


def test_linguica_sugere_enchidos_com_codigo_real():
    resultado = selecionar_produtos(catalogo(), "Linguiça", 10)
    assert resultado.busca_aproximada
    assert resultado.produtos[0].ncm == "16010000"
    assert resultado.produtos[0].hs6 == "160100"


def test_correspondencia_direta_tem_prioridade():
    df = catalogo()
    df.loc[1, "descricao_ncm"] = "Linguiça de frango"
    df["_busca"] = df.descricao_ncm.map(normalizar_busca)
    resultado = selecionar_produtos(df, "linguiça", 10)
    assert not resultado.busca_aproximada
    assert len(resultado.produtos) == 1


def test_acento_codigo_limite_e_termo_desconhecido():
    assert selecionar_produtos(catalogo(), "cafe", 1).produtos[0].ncm == "09011110"
    assert selecionar_produtos(catalogo(), "160100", 1).produtos[0].hs6 == "160100"
    assert selecionar_produtos(catalogo(), "produto inexistente", 10).total == 0
    assert selecionar_produtos(catalogo(), "!!", 10).total == 0


def test_endpoint_com_catalogo_real():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    resposta = client.get("/api/v1/produtos", params={"q": "linguiça", "limite": 10})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["busca_aproximada"]
    assert any(item["ncm"] == "16010000" for item in corpo["produtos"])
    assert all("enchidos" in normalizar_busca(item["descricao_ncm"]) for item in corpo["produtos"])
    assert client.get("/api/v1/produtos", params={"q": "café", "limite": 1}).json()["busca_aproximada"] is False
    assert client.get("/api/v1/produtos", params={"q": "a"}).status_code == 422
    assert client.get("/api/v1/produtos", params={"q": "cafe", "limite": 51}).status_code == 422
