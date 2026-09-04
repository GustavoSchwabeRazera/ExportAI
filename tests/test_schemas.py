import pytest
from pydantic import ValidationError

from app.schemas import (
    ConsultaRecomendacaoRequest,
    ConsultaRecomendacaoResponse,
)


def test_request_ncm_valida_e_normaliza_pontuacao():
    entrada = ConsultaRecomendacaoRequest(
        ncm="09.01.11.10",
        paises_ja_exportados=[
            "Argentina",
            "Estados Unidos",
            "argentina",
            "",
        ],
        quantidade=5,
    )
    assert entrada.ncm == "09011110"
    assert entrada.hs6 is None
    assert entrada.paises_ja_exportados == [
        "Argentina",
        "Estados Unidos",
    ]


def test_request_hs6_valido():
    entrada = ConsultaRecomendacaoRequest(hs6="090111")
    assert entrada.hs6 == "090111"
    assert entrada.ncm is None


@pytest.mark.parametrize(
    "dados",
    [
        {},
        {"ncm": "09011110", "hs6": "090111"},
        {"ncm": "123"},
        {"hs6": "123"},
        {"ncm": "09011110", "quantidade": 0},
        {"ncm": "09011110", "quantidade": 259},
        {"ncm": "09011110", "confianca_minima": "MEDIA"},
        {"ncm": "09011110", "campo_desconhecido": True},
    ],
)
def test_requests_invalidos(dados):
    with pytest.raises(ValidationError):
        ConsultaRecomendacaoRequest(**dados)


def test_response_valida_retorno_do_servico():
    resposta = ConsultaRecomendacaoResponse.model_validate(
        {
            "consulta": {
                "ncm": "09011110",
                "descricao_ncm": "Cafe nao torrado",
                "hs6": "090111",
                "quantidade_solicitada": 1,
                "confianca_minima": "LIMITADA",
                "somente_novas": False,
            },
            "exclusoes": {
                "informadas": ["Argentina"],
                "iso3_reconhecidos": ["ARG"],
                "nao_reconhecidas": [],
            },
            "cobertura": {
                "paises_avaliados_inicialmente": 232,
                "paises_apos_exclusoes": 231,
                "paises_apos_todos_filtros": 231,
                "recomendacoes_retornadas": 1,
            },
            "metodologia": {
                "fonte": "base completa HS6 + pais",
                "exclusao_antes_da_ordenacao": True,
                "ranking_personalizado_recalculado": True,
                "pais_excluido_reintroduzido": False,
                "ordenacao": ["score_exportai desc"],
            },
            "recomendacoes": [
                {
                    "ranking_personalizado": 1,
                    "ranking_global_no_hs6": 2,
                    "HS6": "090111",
                    "ISO3": "CHN",
                    "pais": "China",
                    "score_exportai": 56.4,
                    "indice_cobertura": 85.0,
                    "faixa_confianca": "ALTA",
                    "tipo_oportunidade": "MERCADO_ATUAL_COM_WITS",
                    "motivo_recomendacao": "historico e WITS",
                    "aviso_confianca": None,
                    "score_comex_usado": 83.3,
                    "score_wits_usado": 19.0,
                    "score_economico_usado": 91.8,
                    "score_futuro_usado": 33.0,
                    "score_acordo_usado": 50.0,
                    "comex_imputado": False,
                    "wits_imputado": False,
                    "acordo_neutro": True,
                    "VL_FOB": 1000.0,
                }
            ],
        }
    )
    assert resposta.recomendacoes[0].ISO3 == "CHN"
    assert resposta.cobertura.recomendacoes_retornadas == 1
