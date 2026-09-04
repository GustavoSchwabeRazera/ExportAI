from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
import json
import re
import unicodedata

import pandas as pd


# ============================================================
# CONFIGURACAO PADRAO
# Este arquivo e um modulo reutilizavel pelo backend do MVP.
# Tambem executa testes rapidos quando chamado diretamente.
# ============================================================

RAIZ = Path(__file__).resolve().parent
CONSULTA_DIR = RAIZ / "dados_processados" / "integracao" / "consulta_mvp_v2"
BASE_PADRAO = CONSULTA_DIR / "base_consulta_hs6_pais_completa.parquet"
INDICE_PADRAO = CONSULTA_DIR / "indice_ncm_hs6.parquet"

ORDEM_CONFIANCA = {"LIMITADA": 1, "MODERADA": 2, "ALTA": 3}

ALIASES_MANUAIS = {
    "eua": "USA",
    "usa": "USA",
    "estados unidos": "USA",
    "estados unidos da america": "USA",
    "united states": "USA",
    "reino unido": "GBR",
    "gra bretanha": "GBR",
    "inglaterra": "GBR",
    "united kingdom": "GBR",
    "uk": "GBR",
    "alemanha": "DEU",
    "germany": "DEU",
    "china": "CHN",
    "argentina": "ARG",
    "chile": "CHL",
    "italia": "ITA",
    "italy": "ITA",
    "japao": "JPN",
    "japan": "JPN",
    "coreia do sul": "KOR",
    "south korea": "KOR",
    "republic of korea": "KOR",
    "coreia do norte": "PRK",
    "north korea": "PRK",
    "russia": "RUS",
    "federacao russa": "RUS",
    "russian federation": "RUS",
    "vietna": "VNM",
    "vietnam": "VNM",
    "viet nam": "VNM",
    "tchequia": "CZE",
    "republica tcheca": "CZE",
    "czechia": "CZE",
    "paises baixos": "NLD",
    "holanda": "NLD",
    "netherlands": "NLD",
    "espanha": "ESP",
    "spain": "ESP",
    "franca": "FRA",
    "france": "FRA",
    "belgica": "BEL",
    "belgium": "BEL",
    "suica": "CHE",
    "switzerland": "CHE",
    "austria": "AUT",
    "canada": "CAN",
    "mexico": "MEX",
    "portugal": "PRT",
    "uruguai": "URY",
    "uruguay": "URY",
    "paraguai": "PRY",
    "paraguay": "PRY",
    "brasil": "BRA",
    "brazil": "BRA",
    "singapura": "SGP",
    "singapore": "SGP",
    "india": "IND",
    "arabia saudita": "SAU",
    "saudi arabia": "SAU",
    "emirados arabes unidos": "ARE",
    "united arab emirates": "ARE",
    "uae": "ARE",
    "africa do sul": "ZAF",
    "south africa": "ZAF",
    "nova zelandia": "NZL",
    "new zealand": "NZL",
    "australia": "AUS",
    "turquia": "TUR",
    "turkiye": "TUR",
    "turkey": "TUR",
    "taiwan": "TWN",
    "hong kong": "HKG",
    "bolivia": "BOL",
    "colombia": "COL",
    "peru": "PER",
    "equador": "ECU",
    "venezuela": "VEN",
    "costa rica": "CRI",
    "panama": "PAN",
    "republica dominicana": "DOM",
    "dominican republic": "DOM",
}


class ErroConsultaExportAI(Exception):
    """Erro controlado do servico de consulta."""


class CodigoInvalidoError(ErroConsultaExportAI):
    pass


class CodigoNaoEncontradoError(ErroConsultaExportAI):
    pass


class BaseConsultaError(ErroConsultaExportAI):
    pass


@dataclass(frozen=True)
class ParametrosConsulta:
    ncm: str | None = None
    hs6: str | None = None
    paises_excluidos: tuple[str, ...] = ()
    quantidade: int = 5
    confianca_minima: str = "LIMITADA"
    somente_novas: bool = False


class ServicoConsultaExportAI:
    """
    Servico reutilizavel para consulta personalizada do ExportAI.

    Fluxo:
      NCM -> HS6 -> todos os paises -> exclusoes -> filtros -> ranking.
    """

    def __init__(
        self,
        caminho_base: Path | str = BASE_PADRAO,
        caminho_indice: Path | str = INDICE_PADRAO,
    ) -> None:
        self.caminho_base = Path(caminho_base)
        self.caminho_indice = Path(caminho_indice)
        self._indice: pd.DataFrame | None = None
        self._base_cache: pd.DataFrame | None = None
        self._aliases_cache: dict[str, str] | None = None
        self._validar_arquivos()

    def _validar_arquivos(self) -> None:
        if not self.caminho_base.exists():
            raise BaseConsultaError(
                f"Base de consulta nao encontrada: {self.caminho_base}"
            )
        if not self.caminho_indice.exists():
            raise BaseConsultaError(
                f"Indice NCM-HS6 nao encontrado: {self.caminho_indice}"
            )

    @staticmethod
    def _normalizar_texto(valor: Any) -> str:
        if valor is None or pd.isna(valor):
            return ""
        texto = unicodedata.normalize("NFKD", str(valor).strip())
        texto = "".join(c for c in texto if not unicodedata.combining(c))
        texto = texto.casefold()
        texto = re.sub(r"[^a-z0-9]+", " ", texto)
        return re.sub(r"\s+", " ", texto).strip()

    @staticmethod
    def _normalizar_codigo(valor: Any, tamanho: int, descricao: str) -> str:
        digitos = re.sub(r"\D", "", str(valor).strip())
        if len(digitos) != tamanho:
            raise CodigoInvalidoError(
                f"{descricao} invalido: {valor}. Informe exatamente {tamanho} digitos."
            )
        return digitos

    def _carregar_indice(self) -> pd.DataFrame:
        if self._indice is None:
            indice = pd.read_parquet(self.caminho_indice)
            obrigatorias = {"NCM", "HS6"}
            faltantes = obrigatorias - set(indice.columns)
            if faltantes:
                raise BaseConsultaError(
                    f"Indice sem colunas obrigatorias: {sorted(faltantes)}"
                )
            indice = indice.copy()
            indice["NCM"] = indice["NCM"].astype("string").str.zfill(8)
            indice["HS6"] = indice["HS6"].astype("string").str.zfill(6)
            self._indice = indice
        return self._indice

    def _carregar_hs6(self, hs6: str) -> pd.DataFrame:
        try:
            candidatos = pd.read_parquet(
                self.caminho_base,
                filters=[[('HS6', '==', hs6)]],
            )
        except Exception:
            if self._base_cache is None:
                self._base_cache = pd.read_parquet(self.caminho_base)
            candidatos = self._base_cache.loc[
                self._base_cache["HS6"].astype("string").eq(hs6)
            ].copy()

        if candidatos.empty:
            raise CodigoNaoEncontradoError(
                f"Nenhum pais avaliado para o HS6 {hs6}."
            )

        obrigatorias = {
            "HS6",
            "ISO3",
            "score_exportai",
            "indice_cobertura",
            "faixa_confianca",
            "tipo_oportunidade",
            "ranking_global_no_hs6",
        }
        faltantes = obrigatorias - set(candidatos.columns)
        if faltantes:
            raise BaseConsultaError(
                f"Base de consulta sem colunas obrigatorias: {sorted(faltantes)}"
            )

        candidatos = candidatos.copy()
        candidatos["ISO3"] = (
            candidatos["ISO3"].astype("string").str.upper()
        )
        return candidatos

    def _resolver_codigo(
        self,
        ncm: str | None,
        hs6: str | None,
    ) -> tuple[str, str | None, str | None]:
        if bool(ncm) == bool(hs6):
            raise CodigoInvalidoError(
                "Informe exatamente um codigo: ncm ou hs6."
            )

        if hs6:
            return self._normalizar_codigo(hs6, 6, "HS6"), None, None

        ncm_normalizada = self._normalizar_codigo(ncm, 8, "NCM")
        indice = self._carregar_indice()
        linhas = indice.loc[indice["NCM"].eq(ncm_normalizada)].copy()
        if linhas.empty:
            raise CodigoNaoEncontradoError(
                f"NCM {ncm_normalizada} nao encontrada no indice NCM-HS6."
            )

        hs6_encontrados = linhas["HS6"].dropna().astype(str).unique().tolist()
        if len(hs6_encontrados) != 1:
            raise BaseConsultaError(
                f"NCM {ncm_normalizada} possui correspondencias HS6 ambiguas: "
                f"{hs6_encontrados}"
            )

        descricao = None
        if "descricao_ncm" in linhas.columns:
            descricoes = linhas["descricao_ncm"].dropna().astype(str)
            if not descricoes.empty:
                descricao = descricoes.iloc[0]

        return hs6_encontrados[0], ncm_normalizada, descricao

    def _gerar_aliases(self, candidatos: pd.DataFrame) -> dict[str, str]:
        iso3_validos = set(
            candidatos["ISO3"].dropna().astype(str).str.upper().unique()
        )
        mapa = {
            self._normalizar_texto(alias): codigo
            for alias, codigo in ALIASES_MANUAIS.items()
            if codigo in iso3_validos
        }

        for codigo in iso3_validos:
            mapa[self._normalizar_texto(codigo)] = codigo

        if "pais" in candidatos.columns:
            nomes = candidatos[["ISO3", "pais"]].dropna().drop_duplicates()
            for codigo, nome in nomes.itertuples(index=False):
                mapa[self._normalizar_texto(nome)] = str(codigo).upper()

        try:
            import pycountry
        except ImportError:
            pycountry = None

        try:
            from babel import Locale
            locale_pt = Locale("pt", "BR")
        except ImportError:
            locale_pt = None

        if pycountry is not None:
            for codigo in iso3_validos:
                pais = pycountry.countries.get(alpha_3=codigo)
                if pais is None:
                    continue
                for atributo in ("name", "official_name", "common_name"):
                    nome = getattr(pais, atributo, None)
                    if nome:
                        mapa[self._normalizar_texto(nome)] = codigo
                if locale_pt is not None:
                    nome_pt = locale_pt.territories.get(pais.alpha_2)
                    if nome_pt:
                        mapa[self._normalizar_texto(nome_pt)] = codigo

        return mapa

    def _resolver_exclusoes(
        self,
        candidatos: pd.DataFrame,
        termos: Iterable[str],
    ) -> tuple[set[str], list[str]]:
        mapa = self._gerar_aliases(candidatos)
        reconhecidos: set[str] = set()
        nao_reconhecidos: list[str] = []

        for termo in termos:
            codigo = mapa.get(self._normalizar_texto(termo))
            if codigo:
                reconhecidos.add(codigo)
            else:
                nao_reconhecidos.append(str(termo))

        return reconhecidos, nao_reconhecidos

    @staticmethod
    def _filtrar_confianca(
        candidatos: pd.DataFrame,
        confianca_minima: str,
    ) -> pd.DataFrame:
        confianca = str(confianca_minima).upper()
        if confianca not in ORDEM_CONFIANCA:
            raise CodigoInvalidoError(
                "confianca_minima deve ser LIMITADA, MODERADA ou ALTA."
            )
        niveis = candidatos["faixa_confianca"].map(ORDEM_CONFIANCA).fillna(0)
        return candidatos.loc[
            niveis.ge(ORDEM_CONFIANCA[confianca])
        ].copy()

    @staticmethod
    def _serializar_valor(valor: Any) -> Any:
        if pd.isna(valor):
            return None
        if hasattr(valor, "item"):
            return valor.item()
        return valor

    def consultar(
        self,
        *,
        ncm: str | None = None,
        hs6: str | None = None,
        paises_excluidos: Iterable[str] | None = None,
        quantidade: int = 5,
        confianca_minima: str = "LIMITADA",
        somente_novas: bool = False,
    ) -> dict[str, Any]:
        """Executa a consulta e retorna uma estrutura pronta para JSON/API."""
        if quantidade <= 0:
            raise CodigoInvalidoError("quantidade deve ser maior que zero.")

        hs6_resolvido, ncm_resolvida, descricao = self._resolver_codigo(ncm, hs6)
        candidatos = self._carregar_hs6(hs6_resolvido)
        total_inicial = int(len(candidatos))

        excluidos, desconhecidos = self._resolver_exclusoes(
            candidatos,
            paises_excluidos or (),
        )
        candidatos = candidatos.loc[
            ~candidatos["ISO3"].isin(excluidos)
        ].copy()
        total_apos_exclusoes = int(len(candidatos))

        candidatos = self._filtrar_confianca(
            candidatos,
            confianca_minima,
        )
        if somente_novas:
            candidatos = candidatos.loc[
                candidatos["tipo_oportunidade"].eq(
                    "NOVA_OPORTUNIDADE_WITS"
                )
            ].copy()

        candidatos = candidatos.sort_values(
            [
                "score_exportai",
                "indice_cobertura",
                "ranking_global_no_hs6",
                "ISO3",
            ],
            ascending=[False, False, True, True],
            kind="mergesort",
        )
        candidatos["ranking_personalizado"] = range(
            1,
            len(candidatos) + 1,
        )
        selecionados = candidatos.head(quantidade).copy()

        colunas_saida = [
            "ranking_personalizado",
            "ranking_global_no_hs6",
            "HS6",
            "ISO3",
            "pais",
            "score_exportai",
            "indice_cobertura",
            "faixa_confianca",
            "tipo_oportunidade",
            "motivo_recomendacao",
            "aviso_confianca",
            "score_comex_usado",
            "score_wits_usado",
            "score_economico_usado",
            "score_futuro_usado",
            "score_acordo_usado",
            "comex_imputado",
            "wits_imputado",
            "acordo_neutro",
            "VL_FOB",
        ]
        colunas_saida = [c for c in colunas_saida if c in selecionados.columns]

        recomendacoes = []
        for registro in selecionados[colunas_saida].to_dict(orient="records"):
            recomendacoes.append({
                chave: self._serializar_valor(valor)
                for chave, valor in registro.items()
            })

        return {
            "consulta": {
                "ncm": ncm_resolvida,
                "descricao_ncm": descricao,
                "hs6": hs6_resolvido,
                "quantidade_solicitada": quantidade,
                "confianca_minima": str(confianca_minima).upper(),
                "somente_novas": bool(somente_novas),
            },
            "exclusoes": {
                "informadas": list(paises_excluidos or ()),
                "iso3_reconhecidos": sorted(excluidos),
                "nao_reconhecidas": desconhecidos,
            },
            "cobertura": {
                "paises_avaliados_inicialmente": total_inicial,
                "paises_apos_exclusoes": total_apos_exclusoes,
                "paises_apos_todos_filtros": int(len(candidatos)),
                "recomendacoes_retornadas": int(len(recomendacoes)),
            },
            "metodologia": {
                "fonte": "base completa HS6 + pais",
                "exclusao_antes_da_ordenacao": True,
                "ranking_personalizado_recalculado": True,
                "pais_excluido_reintroduzido": False,
                "ordenacao": [
                    "score_exportai desc",
                    "indice_cobertura desc",
                    "ranking_global_no_hs6 asc",
                    "ISO3 asc",
                ],
            },
            "recomendacoes": recomendacoes,
        }


# Instancia unica para importacao simples pelo backend.
servico_exportai = ServicoConsultaExportAI


def consultar_exportai(**parametros: Any) -> dict[str, Any]:
    """Atalho funcional para backends que nao desejam gerenciar a classe."""
    servico = ServicoConsultaExportAI()
    return servico.consultar(**parametros)


def _teste_local() -> None:
    servico = ServicoConsultaExportAI()
    resultado = servico.consultar(
        ncm="09011110",
        paises_excluidos=["Argentina", "Estados Unidos", "Chile"],
        quantidade=5,
    )
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        _teste_local()
    except ErroConsultaExportAI as erro:
        print(f"ERRO CONTROLADO: {erro}")
        sys.exit(1)
