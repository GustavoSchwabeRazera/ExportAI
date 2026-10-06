"""Validação isolada da busca, incluindo falsos positivos e negações."""
from app.busca_produtos import BuscaCatalogo, normalizar


def motor(*descricoes: str) -> BuscaCatalogo:
    return BuscaCatalogo([normalizar(d) for d in descricoes])


def test_corrige_erro_em_vocabulario_sem_sinonimo_cadastrado():
    busca = motor("Parafusos de ferro", "Pneumáticos de borracha")
    assert busca.buscar("parafuzos ferro")[0][0] == 0


def test_prefixo_acento_e_plural():
    busca = motor("Camisetas de algodão", "Camisetas de fibras sintéticas")
    assert busca.buscar("camiseta algo")[0][0] == 0


def test_nome_popular_prioriza_produto_sobre_insumo():
    busca = motor("Misturas próprias para embutidos", "Enchidos e produtos semelhantes de carne")
    assert busca.buscar("linguiça e embutidos")[0][0] == 1


def test_nome_popular_com_descricao_tecnica():
    busca = motor("Partes de computadores", "Máquinas de processamento de dados portáteis")
    assert busca.buscar("notebook")[0][0] == 1


def test_consulta_desconhecida_nao_traz_produtos_aleatorios():
    assert motor("Café em grão", "Camisetas de algodão").buscar("zzzxqww") == []


def test_qualificador_nao_e_descartado_em_consulta_curta():
    assert motor("Camisetas de algodão").buscar("camiseta titânio") == []


def test_relaxa_apenas_consulta_longa_com_maioria_dos_termos():
    assert motor("Camisetas de malha de algodão").buscar("camiseta malha algodao premium")


def test_negacao_na_descricao_nao_recebe_mesma_prioridade():
    busca = motor("Café não torrado", "Café torrado")
    assert busca.buscar("cafe torrado")[0][0] == 1
    assert busca.buscar("cafe nao torrado")[0][0] == 0


def test_plural_existente_nao_expande_para_outro_produto():
    busca = motor("Camisetas de algodão", "Camisas de algodão")
    assert [p for p, _ in busca.buscar("camiseta algodao")] == [0]


def test_palavra_parecida_nao_equivale_a_produto_similar():
    busca = motor("Açafrão", "Painel de vidro máscara de sombra")
    assert not any(t in busca.alternativas("macarrao", False) for t in ("acafrao", "mascara"))
    assert busca.buscar("macarrão") == []


def test_macarrao_recupera_massas_e_exclui_produtos_sem_relacao():
    busca = motor("Açafrão", "Painel máscara de sombra", "Massas alimentícias que contenham ovos", "Máquinas para empacotamento de massas alimentícias")
    assert [p for p, _ in busca.buscar("macarrão")] == [2]
