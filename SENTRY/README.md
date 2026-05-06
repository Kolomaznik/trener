# GlitchTip on Railway.app

[GlitchTip](https://glitchtip.com) is an open-source, **Sentry-compatible** error tracking platform. Because it speaks the same Sentry SDK protocol, the existing `sentry-sdk` (backend) and `@sentry/react` (frontend) integrations work with GlitchTip **without any code changes** — you only need to point the DSN at your GlitchTip instance instead of sentry.io.

This folder contains everything needed to deploy GlitchTip on Railway.app and connect it to the Trener backend and frontend.

---

## Architecture

```
Railway project
│
├── glitchtip-web     (this folder, Dockerfile)
│   └── gunicorn serving the Django app on $PORT
│
├── glitchtip-worker  (this folder, Dockerfile.worker)
│   └── Celery worker + beat scheduler (background jobs)
│
├── Postgres          (Railway plugin)
└── Redis             (Railway plugin)
```

---

## Step 1 — Create the Railway project

1. Go to [railway.app](https://railway.app) and click **New Project**.
2. Choose **Empty project**.

---

## Step 2 — Add Postgres and Redis

Inside the project:

1. Click **+ New** → **Database** → **Add PostgreSQL** → confirm.
2. Click **+ New** → **Database** → **Add Redis** → confirm.

Railway will assign each plugin a `DATABASE_URL` / `REDIS_URL` that you can reference from other services.

---

## Step 3 — Deploy the GlitchTip web service

1. Click **+ New** → **GitHub repo** → select the **trener** repository.
2. In the service settings:
   - **Root Directory**: `SENTRY`
   - **Dockerfile Path**: `Dockerfile` (default, no change needed)
3. Railway will detect `railway.json` and set the healthcheck path to `/_health/`.

---

## Step 4 — Deploy the Celery worker service

1. Click **+ New** → **GitHub repo** → select the same **trener** repository.
2. In the service settings:
   - **Root Directory**: `SENTRY`
   - **Dockerfile Path**: `Dockerfile.worker`
3. This service does **not** need a public port — leave "Generate Domain" off.

---

## Step 5 — Configure environment variables

Set the following variables in **both** services (web + worker). The easiest way is to use Railway's **Shared Variables** feature — define them once in the project and reference them from each service.

### Required variables

| Variable | Value |
|---|---|
| `SECRET_KEY` | Generate: `python -c 'import secrets; print(secrets.token_urlsafe(50))'` |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` |
| `GLITCHTIP_DOMAIN` | `https://<your-web-service-domain>.up.railway.app` (assign the domain first — see Step 6) |
| `DEFAULT_FROM_EMAIL` | e.g. `noreply@your-domain.up.railway.app` |
| `EMAIL_URL` | `consolemail://` to start (prints to logs); replace with real SMTP later |
| `DJANGO_SUPERUSER_EMAIL` | Your admin email |
| `DJANGO_SUPERUSER_PASSWORD` | A strong initial password |
| `ENABLE_OPEN_USER_REGISTRATION` | `False` (private team) or `True` (open) |
| `USE_X_FORWARDED_HOST` | `True` (Railway is a reverse proxy) |

All variables with examples are in [`.env.example`](.env.example).

> **Security**: Remove `DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD` from
> Railway Variables after the first successful deploy. The superuser is already created.

---

## Step 6 — Assign a public domain to the web service

1. Open the **web service** → **Settings** → **Networking** → **Generate Domain**.
2. Copy the generated URL (e.g. `https://glitchtip-production.up.railway.app`).
3. Set `GLITCHTIP_DOMAIN` to that URL in both services.
4. Redeploy both services.

---

## Step 7 — Create Sentry-compatible projects in GlitchTip

1. Open your GlitchTip URL and log in with the superuser account.
2. Create an **Organization** (e.g. `trener`).
3. Inside the organization, create two **Projects**:
   - `trener-backend` — choose platform **Django** or **Python**.
   - `trener-frontend` — choose platform **JavaScript / React**.
4. Open each project → **Settings** → **Client Keys (DSN)** and copy the DSN.

The DSN format looks like:
```
https://<public-key>@<your-glitchtip-domain>/<project-id>
```

---

## Step 8 — Connect the backend

In Railway, open the **Trener backend** service → **Variables** and set:

```
SENTRY_DSN=https://<key>@<glitchtip-domain>/<backend-project-id>
```

Optionally tune:

```
SENTRY_TRACES_SAMPLE_RATE=0.1
```

The backend uses `sentry-sdk[fastapi]` which is 100% compatible with GlitchTip. No code changes needed.

---

## Step 9 — Connect the frontend

In Railway, open the **Trener frontend** service → **Variables** and set:

```
VITE_SENTRY_DSN=https://<key>@<glitchtip-domain>/<frontend-project-id>
```

Optionally tune:

```
VITE_SENTRY_TRACES_SAMPLE_RATE=0.1
```

> ⚠️ `VITE_*` variables are baked into the JS bundle at **build time**.
> After setting them in Railway, trigger a redeploy so a new build runs.

The frontend uses `@sentry/react` which is 100% compatible with GlitchTip.

---

## Step 10 — Verify

1. Open the frontend in your browser and navigate around — you should see transactions appear in GlitchTip.
2. Trigger a test error in the backend:
   ```
   curl https://<backend-url>/sentry-debug  # if you added a test route
   ```
   Or simply send a bad request and check GlitchTip for the captured exception.

---

## Source map uploads (optional)

GlitchTip supports Sentry-compatible source map uploads, which makes JavaScript stack traces readable in production.

1. In GlitchTip → your frontend project → **Settings** → **Auth Tokens**, create a token.
2. Add to Railway frontend service variables (build-time only, **not** `VITE_`):
   ```
   SENTRY_AUTH_TOKEN=<token>
   SENTRY_ORG=<your-glitchtip-org-slug>
   SENTRY_PROJECT=trener-frontend
   ```
3. Also set `VITE_SENTRY_DSN` so the Vite plugin knows which project to upload to.
4. The `@sentry/vite-plugin` in `FRONTEND/vite.config.js` automatically uploads
   source maps on `npm run build` when `SENTRY_AUTH_TOKEN` is set.

> ℹ️ GlitchTip's source map upload endpoint is compatible with the Sentry upload protocol.
> No changes to `vite.config.js` are needed.

---

## Local development

To run GlitchTip locally for testing (requires Docker Compose):

```bash
cd SENTRY

# Copy and fill in the example env
cp .env.example .env
# Edit SECRET_KEY, EMAIL_URL=consolemail://, etc.

docker run --rm \
  --env-file .env \
  -e DATABASE_URL=postgresql://gt:gt@host.docker.internal:5432/gt \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  -p 8080:8000 \
  glitchtip/glitchtip:latest
```

Or use the [official docker-compose.yml](https://glitchtip.com/documentation/install) from the GlitchTip docs.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Web service crashes on startup | `SECRET_KEY`, `DATABASE_URL`, or `REDIS_URL` is missing or wrong |
| `/_health/` returns 500 | Database is unreachable — check `DATABASE_URL` and Postgres plugin status |
| Events not appearing | Celery worker is not running — check the worker service logs |
| DSN errors in frontend | `VITE_SENTRY_DSN` needs a redeploy (build-time variable) |
| Superuser already exists error | Normal — the `createsuperuser` step is idempotent; remove the variables |
| HTTPS redirect loop | Set `SECURE_SSL_REDIRECT=False` (Railway handles TLS termination) |
