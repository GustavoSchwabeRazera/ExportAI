from __future__ import annotations
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

NCM = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{8}$")]
HS6 = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{6}$")]
ISO3 = Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Z]{3}$")]
Confianca = Literal["LIMITADA", "MODERADA", "ALTA"]
TipoOportunidade = Literal["MERCADO_ATUAL_COM_WITS", "NOVA_OPORTUNIDADE_WITS", "HISTORICO_SEM_WITS"]

class SchemaBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)

class ConsultaRecomendacaoRequest(SchemaBase):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{
                "ncm": "09011110",
                "paises_ja_exportados": ["Argentina", "Estados Unidos", "Chile"],
                "quantidade": 5,
                "confianca_minima": "LIMITADA",
                "somente_novas": False,
            }]
        },
    )
    ncm: NCM | None = Field(default=None, description="NCM brasileira com 8 digitos.")
    hs6: HS6 | None = Field(default=None, description="HS6 com 6 digitos. Use somente se ncm estiver ausente.")
    paises_ja_exportados: list[str] = Field(default_factory=list, max_length=258)
    quantidade: int = Field(default=5, ge=1, le=258)
    confianca_minima: Confianca = "LIMITADA"
    somente_novas: bool = False

    @field_validator("ncm", mode="before")
    @classmethod
    def normalizar_ncm(cls, valor):
        return None if valor is None else "".join(c for c in str(valor) if c.isdigit())

    @field_validator("hs6", mode="before")
    @classmethod
    def normalizar_hs6(cls, valor):
        return None if valor is None else "".join(c for c in str(valor) if c.isdigit())

    @field_validator("paises_ja_exportados")
    @classmethod
    def limpar_paises(cls, valores):
        resultado, vistos = [], set()
        for valor in valores:
            texto = str(valor).strip()
            chave = texto.casefold()
            if texto and chave not in vistos:
                resultado.append(texto)
                vistos.add(chave)
        return resultado

    @model_validator(mode="after")
    def validar_codigo_exclusivo(self):
        if bool(self.ncm) == bool(self.hs6):
            raise ValueError("Informe exatamente um codigo: ncm ou hs6.")
        return self

class ConsultaInfo(SchemaBase):
    ncm: NCM | None = None
    descricao_ncm: str | None = None
    hs6: HS6
    quantidade_solicitada: int = Field(ge=1, le=258)
    confianca_minima: Confianca
    somente_novas: bool

class ExclusoesInfo(SchemaBase):
    informadas: list[str]
    iso3_reconhecidos: list[ISO3]
    nao_reconhecidas: list[str]

class CoberturaInfo(SchemaBase):
    paises_avaliados_inicialmente: int = Field(ge=0)
    paises_apos_exclusoes: int = Field(ge=0)
    paises_apos_todos_filtros: int = Field(ge=0)
    recomendacoes_retornadas: int = Field(ge=0)

class MetodologiaInfo(SchemaBase):
    fonte: str
    exclusao_antes_da_ordenacao: bool
    ranking_personalizado_recalculado: bool
    pais_excluido_reintroduzido: bool
    ordenacao: list[str]

class RecomendacaoPais(SchemaBase):
    ranking_personalizado: int = Field(ge=1)
    ranking_global_no_hs6: int = Field(ge=1)
    HS6: HS6
    ISO3: ISO3
    pais: str | None = None
    score_exportai: float = Field(ge=0, le=100)
    indice_cobertura: float = Field(ge=0, le=100)
    faixa_confianca: Confianca
    tipo_oportunidade: TipoOportunidade
    motivo_recomendacao: str | None = None
    aviso_confianca: str | None = None
    score_comex_usado: float | None = Field(default=None, ge=0, le=100)
    score_wits_usado: float | None = Field(default=None, ge=0, le=100)
    score_economico_usado: float | None = Field(default=None, ge=0, le=100)
    score_futuro_usado: float | None = Field(default=None, ge=0, le=100)
    score_acordo_usado: float | None = Field(default=None, ge=0, le=100)
    comex_imputado: bool | None = None
    wits_imputado: bool | None = None
    acordo_neutro: bool | None = None
    VL_FOB: float | None = Field(default=None, ge=0)

class ConsultaRecomendacaoResponse(SchemaBase):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{
                "consulta": {"ncm": "09011110", "descricao_ncm": "Cafe nao torrado, nao descafeinado, em grao", "hs6": "090111", "quantidade_solicitada": 1, "confianca_minima": "LIMITADA", "somente_novas": False},
                "exclusoes": {"informadas": ["Argentina"], "iso3_reconhecidos": ["ARG"], "nao_reconhecidas": []},
                "cobertura": {"paises_avaliados_inicialmente": 232, "paises_apos_exclusoes": 231, "paises_apos_todos_filtros": 231, "recomendacoes_retornadas": 1},
                "metodologia": {"fonte": "base completa HS6 + pais", "exclusao_antes_da_ordenacao": True, "ranking_personalizado_recalculado": True, "pais_excluido_reintroduzido": False, "ordenacao": ["score_exportai desc"]},
                "recomendacoes": [{"ranking_personalizado": 1, "ranking_global_no_hs6": 2, "HS6": "090111", "ISO3": "CHN", "pais": "China", "score_exportai": 56.41, "indice_cobertura": 85, "faixa_confianca": "ALTA", "tipo_oportunidade": "MERCADO_ATUAL_COM_WITS"}],
            }]
        },
    )
    consulta: ConsultaInfo
    exclusoes: ExclusoesInfo
    cobertura: CoberturaInfo
    metodologia: MetodologiaInfo
    recomendacoes: list[RecomendacaoPais]

class ErroDetalhe(SchemaBase):
    codigo: str
    mensagem: str
    detalhes: list[dict] | None = None

class ErroResponse(SchemaBase):
    erro: ErroDetalhe

class HealthArquivos(SchemaBase):
    base_consulta: bool
    indice_ncm_hs6: bool
    catalogo_hs6: bool

class HealthResponse(SchemaBase):
    status: Literal["ok", "erro"]
    servico_carregado: bool
    arquivos: HealthArquivos
