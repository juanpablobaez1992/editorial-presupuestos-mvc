from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


NOTA_IMPRESION = "Cotizado manualmente en https://print.livriz.com"


def _es_item_impresion(nombre: str) -> bool:
    texto = nombre.strip().lower()
    return "impres" in texto


class ItemBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=120)
    monto: float = Field(..., ge=0)
    nota: str | None = Field(default=None, max_length=300)

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def aplicar_regla_impresion(self) -> "ItemBase":
        if _es_item_impresion(self.nombre):
            self.nota = NOTA_IMPRESION
        elif self.nota:
            self.nota = self.nota.strip()
        return self


class ItemCreate(ItemBase):
    pass


class ItemResponse(ItemBase):
    id: str
    orden: int


class EscenarioBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=120)
    cantidad_copias: int = Field(..., gt=0)
    items: list[ItemCreate] = Field(..., min_length=1)
    porcentaje_ganancia: float = Field(..., ge=0, le=1000)
    tipo_de_cambio_snapshot: float = Field(..., gt=0)

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validar_items_requeridos(self) -> "EscenarioBase":
        if not any(_es_item_impresion(item.nombre) for item in self.items):
            raise ValueError("Cada escenario debe incluir un item de Impresion.")
        return self


class EscenarioCreate(EscenarioBase):
    pass


class EscenarioResponse(EscenarioBase):
    id: str
    orden: int
    items: list[ItemResponse]
    subtotal: float
    total: float
    precio_por_ejemplar: float
    precio_usd: float
    ganancia_neta_pesos: float


class PresupuestoBase(BaseModel):
    nombre_proyecto: str = Field(..., min_length=1, max_length=200)
    cliente: str = Field(..., min_length=1, max_length=160)
    fecha: date
    escenarios: list[EscenarioCreate] = Field(..., min_length=1, max_length=2)
    notas: str | None = Field(default=None, max_length=1000)

    @field_validator("nombre_proyecto", "cliente")
    @classmethod
    def validar_textos(cls, value: str) -> str:
        return value.strip()

    @field_validator("notas")
    @classmethod
    def limpiar_notas(cls, value: str | None) -> str | None:
        if value is None:
            return None
        limpio = value.strip()
        return limpio or None

    @model_validator(mode="after")
    def validar_nombres_escenarios(self) -> "PresupuestoBase":
        nombres = [escenario.nombre.strip().lower() for escenario in self.escenarios]
        if len(nombres) != len(set(nombres)):
            raise ValueError("Los nombres de los escenarios deben ser unicos dentro del presupuesto.")
        return self


class PresupuestoCreate(PresupuestoBase):
    pass


class PresupuestoUpdate(PresupuestoBase):
    pass


class PresupuestoResumen(BaseModel):
    id: str
    nombre_proyecto: str
    cliente: str
    fecha: date
    notas: str | None = None
    total_ars_referencia: float
    total_usd_referencia: float
    cantidad_escenarios: int
    escenarios: list[dict[str, Any]]


class PresupuestoResponse(BaseModel):
    id: str
    nombre_proyecto: str
    cliente: str
    fecha: date
    notas: str | None = None
    escenarios: list[EscenarioResponse]


class ConfiguracionBase(BaseModel):
    tipo_de_cambio: float = Field(..., gt=0)
    tarifa_edicion_por_pagina: float = Field(..., ge=0)
    tarifa_escaneo_por_pagina: float = Field(..., ge=0)
    preset_isbn: float = Field(..., ge=0)
    preset_banner: float = Field(..., ge=0)
    preset_diseno_tapas: float = Field(..., ge=0)


class ConfiguracionUpdate(ConfiguracionBase):
    pass


class ConfiguracionResponse(ConfiguracionBase):
    pass


class CalculoEscenarioRequest(EscenarioCreate):
    pass


class CalculoEscenarioResponse(BaseModel):
    subtotal: float
    total: float
    precio_por_ejemplar: float
    precio_usd: float
    ganancia_neta_pesos: float
