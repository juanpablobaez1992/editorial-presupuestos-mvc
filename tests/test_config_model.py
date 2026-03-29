from __future__ import annotations

from pathlib import Path

import pytest

import database
from models.config_model import actualizar_configuracion, obtener_catalogo_presets, obtener_configuracion
from models.schemas import ConfiguracionUpdate


@pytest.fixture()
def configurar_db_temporal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_dir = tmp_path / "data"
    db_path = data_dir / "test_editorial.db"
    monkeypatch.setattr(database, "DATA_DIR", data_dir)
    monkeypatch.setattr(database, "DB_PATH", db_path)
    database.init_database()


def test_obtener_configuracion_incluye_presets(configurar_db_temporal: None) -> None:
    config = obtener_configuracion()

    assert config["preset_isbn"] == 50000
    assert config["preset_banner"] == 70000
    assert config["preset_diseno_tapas"] == 50000


def test_actualizar_configuracion_persiste_presets(configurar_db_temporal: None) -> None:
    actualizada = actualizar_configuracion(
        ConfiguracionUpdate(
            tipo_de_cambio=1550,
            tarifa_edicion_por_pagina=900,
            tarifa_escaneo_por_pagina=350,
            preset_isbn=52000,
            preset_banner=76000,
            preset_diseno_tapas=61000,
        )
    )

    assert actualizada["preset_isbn"] == 52000
    assert actualizada["preset_banner"] == 76000
    assert actualizada["preset_diseno_tapas"] == 61000


def test_catalogo_presets_refleja_configuracion(configurar_db_temporal: None) -> None:
    config = obtener_configuracion()
    catalogo = obtener_catalogo_presets(config)

    assert [preset["clave"] for preset in catalogo] == ["isbn", "banner", "diseno_tapas"]
    assert catalogo[0]["monto"] == config["preset_isbn"]
