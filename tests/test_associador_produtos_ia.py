import httpx

from app import config
from app.busca_produtos import BuscaCatalogo, normalizar
from app.services.associador_produtos_ia import AssociadorProdutosIA


def associador(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "chave-ficticia-de-teste")
    monkeypatch.setattr(config, "BUSCA_IA_ENABLED", True)
    registros = [
        {"NCM": "16010000", "descricao_ncm": "Enchidos de carne"},
        {"NCM": "61091000", "descricao_ncm": "Camisetas de algodão"},
    ]
    return AssociadorProdutosIA(BuscaCatalogo([normalizar(r["descricao_ncm"]) for r in registros]), registros)


def test_ia_recupera_nome_popular_e_rejeita_ids_inventados(monkeypatch):
    servico = associador(monkeypatch)
    chamadas = []

    def chamar(instrucao, dados):
        chamadas.append(dados)
        if "candidatos" not in dados:
            return {"buscas": ["enchidos carne"]}
        assert dados["candidatos"] == [{"id": 0, "ncm": "16010000", "descricao": "Enchidos de carne"}]
        return {"ids": [99999999, 1, "0", True, 0, 0]}

    monkeypatch.setattr(servico, "_chamar", chamar)
    assert servico.buscar("salame artesanal", []) == [(0, 2.0)]
    assert servico.buscar("SALAME ARTESANAL", []) == [(0, 2.0)]
    assert len(chamadas) == 2  # A repetição veio do cache.


def test_sem_chave_nao_chama_provedor(monkeypatch):
    servico = associador(monkeypatch)
    monkeypatch.setattr(config, "GROQ_API_KEY", None)
    monkeypatch.setattr(servico, "_chamar", lambda *args: (_ for _ in ()).throw(AssertionError("Não deveria chamar")))
    assert servico.buscar("salame artesanal", []) == []


def test_resultado_local_bom_nao_consume_ia(monkeypatch):
    servico = associador(monkeypatch)
    monkeypatch.setattr(servico, "_chamar", lambda *args: (_ for _ in ()).throw(AssertionError("Não deveria chamar")))
    assert servico.buscar("camiseta algodao", [(1, 1.1)]) == [(1, 1.1)]


def test_timeout_preserva_resultados_locais_e_pausa_provedor(monkeypatch):
    servico = associador(monkeypatch)
    chamadas = []

    def falhar(*args):
        chamadas.append(1)
        raise httpx.ReadTimeout("timeout de teste")

    monkeypatch.setattr(servico, "_chamar", falhar)
    assert servico.buscar("salame artesanal", [(0, 0.7)]) == [(0, 0.7)]
    assert servico.buscar("outro produto", []) == []
    assert len(chamadas) == 1


def test_json_invalido_preserva_busca_local(monkeypatch):
    servico = associador(monkeypatch)
    monkeypatch.setattr(servico, "_chamar", lambda *args: {"buscas": "não é uma lista"})
    assert servico.buscar("salame artesanal", [(0, 0.7)]) == [(0, 0.7)]


def test_ia_sem_candidato_compativel_nao_cria_produto(monkeypatch):
    servico = associador(monkeypatch)
    respostas = iter([{"buscas": ["enchidos carne"]}, {"ids": [999]}])
    monkeypatch.setattr(servico, "_chamar", lambda *args: next(respostas))
    assert servico.buscar("salame artesanal", []) == []


def test_ia_rejeita_correspondencias_locais_fracas(monkeypatch):
    servico = associador(monkeypatch)
    respostas = iter([{"buscas": []}, {"ids": []}])
    monkeypatch.setattr(servico, "_chamar", lambda *args: next(respostas))
    assert servico.buscar("enchidos desconhecidos", [(0, 0.6)]) == []


def test_rota_retorna_ncm_e_descricao_originais_do_catalogo(monkeypatch):
    from app.routes import catalogos

    servico = catalogos.carregar_associador_produtos()
    monkeypatch.setattr(config, "GROQ_API_KEY", "chave-ficticia-de-teste")
    monkeypatch.setattr(config, "BUSCA_IA_ENABLED", True)
    servico._resolver.cache_clear()
    servico.pausa_ate = 0

    def chamar(instrucao, dados):
        if "candidatos" not in dados:
            return {"buscas": ["enchidos carne"]}
        return {"ids": [c["id"] for c in dados["candidatos"] if c["ncm"] == "16010000"]}

    monkeypatch.setattr(servico, "_chamar", chamar)
    try:
        resposta = catalogos.buscar_produtos(q="salame artesanal", limite=10)
        item = resposta.model_dump()["resultados"][0]
        assert item["codigo"] == item["ncm"] == "16010000"
        assert item["hs6"] == "160100"
        catalogo = catalogos.carregar_catalogo_produtos()
        assert item["descricao"] == catalogo.loc[catalogo.NCM.eq("16010000"), "descricao_ncm"].iloc[0]
    finally:
        servico._resolver.cache_clear()
