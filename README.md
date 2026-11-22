# Finanstrack

Para quien cobra **un monto fijo, en una fecha exacta** (cada mes, cada quincena o cada 14 días). El periodo va de un pago al siguiente. Con ese pago se arman cinco bolsas —cuentas, deudas, día a día, gustos y colchón— se apartan las cuotas y las cuentas fijas, y antes de anotar un gasto se ve cuánto quedaría por día.

No hay voz ni asistente. El front solo habla con esta API.

## Dónde vive cada cosa

| Pieza | Dónde | Qué copias |
| --- | --- | --- |
| Base | Supabase (Postgres) | `DATABASE_URL`, y de referencia `SUPABASE_URL` y `SUPABASE_ANON_KEY` |
| API | Render | Las variables de `.env.example` |
| Front | Vercel, repositorio aparte | `VITE_API_URL` y `VITE_GOOGLE_CLIENT_ID` |

La API es este repositorio. El front está en su propio repositorio. Los nombres de variables están en [`.env.example`](.env.example) (API, local y Render) y en el `.env.example` del front (Vercel). Copia el de la API a `.env` en esta carpeta. No subas el `.env` a git.

### Supabase

1. Crea un proyecto.
2. Project Settings → Database → Connection string → **URI** → **Session pooler** (puerto **5432**). No uses el transaction pooler (6543): Alembic no se lleva bien con él.
3. Pega esa URI en `DATABASE_URL`. Si empieza por `postgresql://`, cámbiala a `postgresql+psycopg2://` y agrega `?sslmode=require` si no viene.
4. La contraseña es la de la base (Database password), no la de tu usuario de Supabase.
5. Project Settings → API: `SUPABASE_URL` y la llave `anon`. La API no entra por esas llaves; entra por `DATABASE_URL`. La llave `service_role` no va en ningún lado de esta app, y nunca en el front.

No hace falta armar tablas a mano. Al arrancar, Render corre `alembic upgrade head`.

### Render

1. Nuevo Web Service, raíz de este repositorio.
2. Build: `pip install -r requirements.txt`
3. Start: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Health check: `/health`
5. Environment: las mismas variables del `.env`. `ENVIRONMENT=production`, `DEBUG=false`.
6. `CORS_ORIGINS` = la URL de Vercel, sin barra al final. `JWT_SECRET_KEY` = una clave larga distinta a la de tu máquina (`python -c "import secrets; print(secrets.token_urlsafe(48))"`).

`render.yaml` deja los secretos en blanco (`sync: false`) para pegarlos en el panel.

### Vercel

1. Proyecto nuevo con el repositorio del front. La raíz es ese repo.
2. Framework: Vite. Build `npm run build`, output `dist`.
3. Environment: `VITE_API_URL` = `https://tu-servicio.onrender.com` (sin barra al final). `VITE_GOOGLE_CLIENT_ID` = el mismo Client ID que `GOOGLE_CLIENT_ID` de Render.
4. Vuelve a desplegar después de poner las variables: Vite las mete en el build.

### Google

Sirve para entrar y, si el correo no tiene cuenta, para crearla. No hay voz ni otra API de Google.

1. En [Google Cloud Credentials](https://console.cloud.google.com/apis/credentials) configura la pantalla de consentimiento (Externa) y crea un **ID de cliente de OAuth** de tipo **Aplicación web**.
2. Orígenes de JavaScript autorizados, sin barra al final: `http://localhost:5173`, `http://127.0.0.1:5173` y `https://tu-proyecto.vercel.app`.
3. Copia el **Client ID** en `GOOGLE_CLIENT_ID` (este `.env` y Render) y el mismo texto en `VITE_GOOGLE_CLIENT_ID` (`front/.env` y Vercel).
4. El **Client secret** no se usa. No lo pegues en el front ni en Render.

Con el Client ID vacío la app abre igual: el botón dice que falta configurarlo.

## En tu máquina

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
copy .env.example .env
# edita .env con la URI de Supabase y una JWT_SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

En otra terminal:

```powershell
cd front
npm install
npm run dev
```

Abre `http://127.0.0.1:5173`. Pruebas del motor y de la API: `pytest`.

## Cómo está partido

La ruta no calcula plata. Entra por `app/api`, el servicio decide, el repositorio solo lee y escribe, y `app/domain` es el motor: puro, sin base y sin reloj. Igual que el reparto de bolsas de Kental, recortado a un solo pago fijo y sin la capa de voz.
