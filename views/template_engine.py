from __future__ import annotations

from fastapi.templating import Jinja2Templates


def formatear_numero(valor: float | int | None) -> str:
    numero = float(valor or 0)
    texto = f"{numero:,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def formatear_moneda_ars(valor: float | int | None) -> str:
    return f"$ {formatear_numero(valor)}"


def formatear_moneda_usd(valor: float | int | None) -> str:
    return f"USD {formatear_numero(valor)}"


def formatear_porcentaje(valor: float | int | None) -> str:
    return f"{formatear_numero(valor)}%"


templates = Jinja2Templates(directory="views/templates")
templates.env.filters["numero"] = formatear_numero
templates.env.filters["ars"] = formatear_moneda_ars
templates.env.filters["usd"] = formatear_moneda_usd
templates.env.filters["porcentaje"] = formatear_porcentaje
