<div align="center">

# Sistema de Presupuestos Editorial

### Firmamento / Orbita Studio

<p>
  Aplicacion interna para presupuestos editoriales construida con <strong>FastAPI</strong>, <strong>SQLite</strong>, <strong>Jinja2</strong> y arquitectura <strong>MVC estricta</strong>.
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.10%2B-1f4b99?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/FastAPI-MVC-0b7a75?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI MVC">
  <img src="https://img.shields.io/badge/SQLite-Liviano-3b5b92?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Jinja2-Templates-8a3b2e?style=for-the-badge" alt="Jinja2 Templates">
  <img src="https://img.shields.io/badge/Release-v0.1.0-244839?style=for-the-badge" alt="Release v0.1.0">
</p>

</div>

---

## Vision

Este proyecto resuelve una necesidad concreta de una editorial pequena: crear, comparar, actualizar y exportar presupuestos con criterio comercial, sin perder orden ni mezclar responsabilidades tecnicas.

La aplicacion esta pensada para uso interno y prioriza:

- rapidez operativa
- claridad visual
- reglas de negocio explicitas
- mantenibilidad real cuando el proyecto crece

---

## Lo Que Ya Hace

| Area | Capacidad |
| --- | --- |
| Dashboard | Lista presupuestos, busca por proyecto o cliente y muestra escenario base + rango |
| Formulario | Crea o edita presupuestos con hasta 2 escenarios |
| Calculo | Previsualiza subtotal, total, precio por ejemplar, USD y ganancia neta en tiempo real |
| Configuracion | Administra tipo de cambio, tarifas por pagina y presets inteligentes |
| Presets | Inserta o actualiza ISBN, banner y diseno de tapas con un clic |
| Exportacion | Genera `.xlsx` por escenario y comparacion lado a lado |
| Seguridad | Login fuerte con hash Argon2, sesion segura y bloqueo por intentos fallidos |
| Operacion | Tiene endpoint `/health`, tests automatizados con `pytest` y stack Docker para VPS |

---

## Presets Inteligentes

El formulario ahora incluye presets de costos para:

- `ISBN`
- `Banner`
- `Diseno tapas`

Cada preset toma su monto desde la configuracion global y:

- inserta el item si todavia no existe
- actualiza el item si ya estaba cargado
- evita duplicados innecesarios

Esto acelera el armado de presupuestos repetitivos y mantiene consistencia entre proyectos.

---

## Arquitectura

```text
editorial_presupuestos/
|
+-- main.py                  -> inicia FastAPI y registra routers
+-- database.py              -> conexion SQLite + tablas + defaults
|
+-- controllers/            -> HTTP, coordinacion, responses
|   +-- presupuesto_controller.py
|   +-- config_controller.py
|   +-- system_controller.py
|
+-- models/                 -> validacion, calculos y acceso a datos
|   +-- schemas.py
|   +-- calculations.py
|   +-- presupuesto_model.py
|   +-- config_model.py
|
+-- views/                  -> templates Jinja2 y filtros de presentacion
|   +-- template_engine.py
|   +-- templates/
|
+-- services/               -> integraciones internas como exportacion XLSX
|   +-- export_service.py
|
+-- static/                 -> estilos
+-- tests/                  -> cobertura automatizada con pytest
+-- data/                   -> base SQLite local
```

### Regla central

- `Model` accede a datos y calcula.
- `View` muestra.
- `Controller` coordina.

Sin mezclar capas.

---

## Flujo Operativo

```text
Usuario
  |
  v
Controller
  |
  +--> Model (SQLite + calculos)
  |
  +--> View (Jinja2)
  |
  v
HTML / JSON / XLSX
```

---

## Stack

- Python 3.10+
- FastAPI
- SQLite nativo con `sqlite3`
- Jinja2
- openpyxl
- Tailwind CSS via CDN
- JavaScript vanilla
- pytest

---

## Arranque Rapido

### 1. Instalar dependencias

```bash
python -m pip install -r requirements.txt
```

### 2. Levantar la aplicacion

```bash
python -m uvicorn main:app --reload
```

### 3. Abrir en el navegador

```text
http://127.0.0.1:8000
```

---

## Despliegue En VPS

El proyecto ya incluye:

- `Dockerfile`
- `docker-compose.yml`
- `Caddyfile`
- `.env.example`
- `docs/DEPLOY_VPS.md`

Esto deja lista una publicacion sobre VPS con:

- `https://presupuesto.ediccc.com`
- TLS automatico con Caddy
- persistencia de SQLite
- login administrativo endurecido

Para el paso a paso completo:

```text
docs/DEPLOY_VPS.md
```

---

## Endpoints Principales

| Metodo | Ruta | Funcion |
| --- | --- | --- |
| `GET` | `/` | Dashboard |
| `GET` | `/presupuestos/nuevo` | Formulario de alta |
| `POST` | `/presupuestos` | Crear presupuesto |
| `GET` | `/presupuestos/{id}` | Ver detalle |
| `GET` | `/presupuestos/{id}/editar` | Editar presupuesto |
| `PUT` | `/presupuestos/{id}` | Actualizar presupuesto |
| `DELETE` | `/presupuestos/{id}` | Eliminar presupuesto |
| `POST` | `/presupuestos/{id}/duplicar` | Clonar presupuesto |
| `GET` | `/presupuestos/{id}/export` | Descargar Excel |
| `POST` | `/api/calcular` | Preview de calculos |
| `GET` | `/config` | Configuracion global |
| `PUT` | `/config` | Guardar configuracion |
| `GET` | `/health` | Healthcheck operativo |

---

## Tests

Ejecutar la suite automatizada:

```bash
pytest
```

La cobertura actual valida:

- calculos puros
- configuracion y presets
- endpoints principales
- reglas de negocio criticas

---

## Criterios De Negocio Ya Implementados

- Cada escenario debe incluir `Impresion`.
- El item `Impresion` fuerza la nota manual de Livriz.
- Los nombres de escenarios deben ser unicos por presupuesto.
- El dashboard toma como referencia el escenario con menor cantidad de copias.
- Si hay dos escenarios, muestra rango ARS y USD para lectura rapida.
- El acceso queda protegido por login con hash fuerte y bloqueo temporal por abuso.

---

## Estado Del Proyecto

`v0.1.0` deja una base solida para seguir creciendo sobre:

- autenticacion interna
- historico de cambios
- exportaciones mas complejas
- presets por tipo de proyecto
- reportes comerciales

---

## Licencia

Proyecto de uso interno. Ajustar la licencia segun la politica de publicacion que quieras aplicar mas adelante.
