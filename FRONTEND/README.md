# Trener Frontend

## Installace

```bash
npm ci
```

## Spuštění

```bash
npm run dev
```

## Google OAuth konfigurace

1. V Google Cloud Console vytvoř OAuth 2.0 Client ID (typ Web application).
2. Přidej `Authorized redirect URI` stejné jako `VITE_GOOGLE_REDIRECT_URI`
   (např. `http://localhost:5173`).
3. Zkopíruj `.env.example` do `.env` a vyplň hodnoty.

Příklad:

```bash
cp .env.example .env
```

Používané proměnné:

- `VITE_GOOGLE_CLIENT_ID` – OAuth client ID z Google Cloud.
- `VITE_GOOGLE_REDIRECT_URI` – URL, kam Google vrátí uživatele s tokenem.
- `VITE_GOOGLE_OAUTH_SCOPE` – požadované scopes.
- `VITE_GOOGLE_AUTH_URL` – Google OAuth authorize URL.

Frontend při startu:

- načte token z `localStorage` (`trainer_google_auth_token`),
- nebo převezme `access_token` z URL hash po návratu z Google,
- a když token chybí, přesměruje uživatele na Google OAuth.

Backend endpoint `GET /user/settings` poskytuje e-mail (`login_hint`) pro Google přihlášení.
