from pydantic import BaseModel, ConfigDict, Field


class CatalogoSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaisCatalogo(CatalogoSchema):
    iso3: str = Field(pattern=r"^[A-Z]{3}$")
    nome: str


class ListaPaisesResponse(CatalogoSchema):
    total: int = Field(ge=0)
    paises: list[PaisCatalogo]


class NCMInfoResponse(CatalogoSchema):
    ncm: str = Field(pattern=r"^\d{8}$")
    descricao_ncm: str | None = None
    hs6: str = Field(pattern=r"^\d{6}$")
    existe_no_motor: bool
    paises_avaliados: int = Field(ge=0)


class HS6InfoResponse(CatalogoSchema):
    hs6: str = Field(pattern=r"^\d{6}$")
    quantidade_ncm_bridge: int = Field(ge=0)
    ncm_exemplo: str | None = None
    descricoes_disponiveis: int = Field(ge=0)
    paises_avaliados: int = Field(ge=0)
    score_minimo: float | None = Field(default=None, ge=0, le=100)
    score_mediano: float | None = Field(default=None, ge=0, le=100)
    score_maximo: float | None = Field(default=None, ge=0, le=100)
    tem_ncm_na_bridge: bool
    tem_score_exportai: bool
