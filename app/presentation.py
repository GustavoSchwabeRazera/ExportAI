import pandas as pd
from babel import Locale

_LOCALE_PT = Locale("pt", "BR")

_ALIASES_EXIBICAO = {
    "XKX": "Kosovo",
}


def valor_texto_ou_none(valor) -> str | None:
    """Converte valores textuais sem avaliar pd.NA como booleano."""
    if valor is None:
        return None
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass
    texto = str(valor).strip()
    return texto or None


def nome_pais_portugues(
    iso3: str,
    nome_atual: str | None = None,
) -> str | None:
    codigo = str(iso3).strip().upper()

    try:
        import pycountry

        pais = pycountry.countries.get(alpha_3=codigo)
        if pais is not None:
            traduzido = _LOCALE_PT.territories.get(pais.alpha_2)
            traduzido = valor_texto_ou_none(traduzido)
            if traduzido is not None:
                return traduzido
    except Exception:
        pass

    alias = valor_texto_ou_none(_ALIASES_EXIBICAO.get(codigo))
    if alias is not None:
        return alias

    return valor_texto_ou_none(nome_atual)


def traduzir_recomendacoes(resultado: dict) -> dict:
    for recomendacao in resultado.get("recomendacoes", []):
        recomendacao["pais"] = nome_pais_portugues(
            recomendacao.get("ISO3", ""),
            recomendacao.get("pais"),
        )
    return resultado
