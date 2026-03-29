# Sistema de Presupuestos Editorial

Aplicacion interna para Firmamento / Orbita Studio construida con FastAPI, SQLite y Jinja2 bajo arquitectura MVC estricta.

## Requisitos

- Python 3.10 o superior

## Instalacion

```bash
python -m pip install -r requirements.txt
```

## Ejecutar

```bash
python -m uvicorn main:app --reload
```

Abrir en el navegador:

- `http://127.0.0.1:8000`

## Estructura

- `controllers/`: rutas HTTP y coordinacion
- `models/`: validacion, acceso a datos y calculos
- `views/`: templates y filtros Jinja2
- `services/`: exportacion a Excel
- `database.py`: conexion SQLite e inicializacion

## Funcionalidades

- Dashboard con busqueda
- Alta, edicion, duplicado y borrado de presupuestos
- Hasta 2 escenarios por presupuesto
- Preview de calculos en tiempo real
- Configuracion global de tipo de cambio y tarifas base
- Exportacion `.xlsx`
- Endpoint de salud para chequeos operativos
