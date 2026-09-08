from __future__ import annotations

from typing import Any

import httpx

from app.config import (
    AI_PROVIDER,
    AI_TIMEOUT_SECONDS,
    GROQ_API_KEY,
    GROQ_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
)


PESOS_SCORE = {
    "COMEX": 0.25,
    "WITS": 0.25,
    "Econômico": 0.20,
    "Futuro": 0.15,
    "Acordos": 0.15,
}


def _fmt_numero(valor: Any) -> str:
    """Formata números para leitura humana, sem inventar precisão."""
    if valor is None:
        return "sem dado"
    try:
        return f"{float(valor):.1f}".replace(".", ",")
    except (TypeError, ValueError):
        return str(valor)


def _status_dado(nome: str, valor: Any) -> str:
    return f"{nome}: {_fmt_numero(valor)}"


def gerar_explicacao_deterministica(
    *,
    consulta: dict[str, Any],
    recomendacao: dict[str, Any],
) -> str:
    """
    Gera uma explicação local, auditável e sem chamada externa.

    Ela é usada como fallback quando não há chave de IA ou quando a chamada
    externa falha. A lógica não recalcula o ranking; só interpreta os campos já
    retornados pelo motor ExportAI.
    """
    pais = recomendacao.get("pais") or recomendacao.get("ISO3") or "este país"
    produto = consulta.get("descricao_ncm") or f"HS6 {consulta.get('hs6')}"
    score = _fmt_numero(recomendacao.get("score_exportai"))
    ranking = recomendacao.get("ranking_personalizado")
    confianca = recomendacao.get("faixa_confianca", "não informada")
    tipo = recomendacao.get("tipo_oportunidade", "não informado")

    componentes = [
        _status_dado("COMEX", recomendacao.get("score_comex_usado")),
        _status_dado("WITS", recomendacao.get("score_wits_usado")),
        _status_dado("Econômico", recomendacao.get("score_economico_usado")),
        _status_dado("Futuro", recomendacao.get("score_futuro_usado")),
        _status_dado("Acordos", recomendacao.get("score_acordo_usado")),
    ]

    alertas: list[str] = []
    if recomendacao.get("comex_imputado"):
        alertas.append("o componente COMEX foi estimado por falta de dado direto")
    if recomendacao.get("wits_imputado"):
        alertas.append("o componente WITS foi estimado por falta de dado direto")
    if recomendacao.get("acordo_neutro"):
        alertas.append("acordos comerciais foram tratados como neutros")
    if confianca == "LIMITADA":
        alertas.append("a confiança é limitada e pede validação complementar")

    tipo_texto = {
        "MERCADO_ATUAL_COM_WITS": "mercado com histórico exportador brasileiro e inteligência de demanda WITS",
        "NOVA_OPORTUNIDADE_WITS": "nova oportunidade identificada pela base WITS, sem histórico COMEX observado",
        "HISTORICO_SEM_WITS": "mercado com histórico COMEX, mas sem confirmação WITS direta",
    }.get(str(tipo), str(tipo))

    texto = (
        f"{pais} aparece na posição {ranking} para {produto} com Score ExportAI "
        f"{score} e confiança {confianca}. O resultado combina cinco blocos: "
        f"COMEX e WITS têm peso de 25% cada, Econômico pesa 20%, Futuro pesa 15% "
        f"e Acordos pesa 15%. Componentes usados: {', '.join(componentes)}. "
        f"Na leitura do sistema, este é um {tipo_texto}."
    )

    if alertas:
        texto += " Atenção: " + "; ".join(alertas) + "."

    texto += (
        " A IA não altera o score; ela apenas explica os dados calculados pelo "
        "motor ExportAI."
    )
    return texto


def _montar_prompt(consulta: dict[str, Any], recomendacao: dict[str, Any]) -> str:
    return (
        "Explique a recomendação abaixo para um usuário brasileiro de comércio "
        "exterior. Use somente os dados fornecidos. Não invente tarifas, acordos, "
        "notícias, tendências externas, score nem posição no ranking. Não trate o "
        "resultado como garantia de venda; trate como indicação baseada em dados. "
        "Se houver dado imputado, acordo neutro ou confiança limitada, avise de "
        "forma clara. Seja objetivo, com 1 ou 2 parágrafos.\n\n"
        f"Consulta: {consulta}\n"
        f"Recomendação: {recomendacao}\n"
        f"Pesos do score: {PESOS_SCORE}"
    )


async def gerar_explicacao_ia(
    *,
    consulta: dict[str, Any],
    recomendacao: dict[str, Any],
) -> tuple[str, str]:
    """
    Retorna (texto, origem), onde origem é 'groq', 'openai' ou 'fallback_local'.
    """
    fallback = gerar_explicacao_deterministica(
        consulta=consulta,
        recomendacao=recomendacao,
    )
    if AI_PROVIDER == "openai":
        api_key = OPENAI_API_KEY
        modelo = OPENAI_MODEL
        origem = "openai"
    else:
        api_key = GROQ_API_KEY
        modelo = GROQ_MODEL
        origem = "groq"

    if not api_key:
        return fallback, "fallback_local"

    try:
        async with httpx.AsyncClient(timeout=AI_TIMEOUT_SECONDS) as client:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            if origem == "groq":
                # A Groq usa a API OpenAI-compatible de Chat Completions.
                resposta = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": modelo,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "Você é um analista de comércio exterior. "
                                    "Explique sem inventar dados."
                                ),
                            },
                            {
                                "role": "user",
                                "content": _montar_prompt(consulta, recomendacao),
                            },
                        ],
                        "temperature": 0.2,
                        "max_completion_tokens": 280,
                    },
                )
            else:
                resposta = await client.post(
                    "https://api.openai.com/v1/responses",
                    headers=headers,
                    json={
                        "model": modelo,
                        "store": False,
                        "temperature": 0.2,
                        "max_output_tokens": 280,
                        "input": _montar_prompt(consulta, recomendacao),
                    },
                )

            resposta.raise_for_status()
            dados = resposta.json()
    except Exception:
        return fallback, "fallback_local"

    if origem == "groq":
        escolhas = dados.get("choices") or []
        texto = ""
        if escolhas:
            texto = str(
                escolhas[0].get("message", {}).get("content") or ""
            ).strip()
    else:
        texto = str(dados.get("output_text") or "").strip()

    if not texto:
        return fallback, "fallback_local"
    return texto, origem
