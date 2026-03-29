# Despliegue en VPS

## Objetivo

Publicar la aplicacion en:

- `https://presupuesto.ediccc.com`

con:

- Docker
- Caddy como reverse proxy
- TLS automatico
- persistencia de SQLite
- login fuerte con cookie de sesion segura

## 1. Requisitos del VPS

- Docker Engine
- Docker Compose Plugin
- puertos `80` y `443` abiertos
- DNS `A` de `presupuesto.ediccc.com` apuntando a la IP del VPS

## 2. Clonar el proyecto

```bash
git clone https://github.com/juanpablobaez1992/editorial-presupuestos-mvc.git
cd editorial-presupuestos-mvc
```

## 3. Preparar variables de entorno

Copiar el ejemplo:

```bash
cp .env.example .env
```

## 4. Generar una contraseña fuerte

Generar el hash:

```bash
python scripts/generar_password_hash.py "TuPasswordMuyFuerte_Aqui"
```

Pegar el resultado en:

```env
AUTH_PASSWORD_HASH=...
```

Tambien definir:

- `SESSION_SECRET_KEY` con un valor largo y aleatorio
- `AUTH_ADMIN_USERNAME` con el usuario real de acceso
- `APP_DOMAIN=presupuesto.ediccc.com`
- `APP_ALLOWED_HOSTS=presupuesto.ediccc.com`

## 5. Levantar el stack

```bash
docker compose up -d --build
```

## 6. Verificar

```bash
docker compose ps
docker compose logs -f app
docker compose logs -f caddy
```

La app deberia quedar disponible en:

- `https://presupuesto.ediccc.com`

## 7. Persistencia

La base SQLite queda persistida en:

- `./data/editorial.db`

Haz backup periodico de esa carpeta.

## 8. Seguridad recomendada

- usar una contraseña larga, unica y aleatoria
- no reutilizar credenciales
- limitar acceso SSH por llave
- mantener Docker y el sistema actualizados
- dejar el subdominio sin proteccion de cache intermedia durante la primera emision del certificado
- considerar fail2ban y firewall del VPS

## 9. Actualizacion

```bash
git pull
docker compose up -d --build
```
