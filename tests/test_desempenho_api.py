import time
from statistics import median

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def medir(funcao, repeticoes=5):
    tempos = []
    for _ in range(repeticoes):
        inicio = time.perf_counter()
        resposta = funcao()
        tempos.append((time.perf_counter() - inicio) * 1000)
        assert resposta.status_code == 200
    return tempos


def test_linha_base_desempenho(capsys):
    cenarios = {
        "health": lambda: client.get("/health"),
        "paises": lambda: client.get("/api/v1/paises"),
        "ncm": lambda: client.get("/api/v1/ncm/09011110"),
        "hs6": lambda: client.get("/api/v1/hs6/090111"),
        "recomendacoes": lambda: client.post(
            "/api/v1/recomendacoes",
            json={
                "ncm": "09011110",
                "paises_ja_exportados": ["Argentina", "Estados Unidos", "Chile"],
                "quantidade": 5,
            },
        ),
    }
    metricas = {}
    for nome, chamada in cenarios.items():
        tempos = medir(chamada)
        metricas[nome] = {
            "primeira_ms": round(tempos[0], 2),
            "mediana_ms": round(median(tempos), 2),
            "maxima_ms": round(max(tempos), 2),
        }
    print("\nLINHA_BASE_DESEMPENHO_MS", metricas)

    # Limite largo para detectar travamentos, nao e um SLA de producao.
    assert all(item["maxima_ms"] < 10000 for item in metricas.values())
