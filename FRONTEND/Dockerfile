# syntax=docker/dockerfile:1.7
# Trener FRONTEND — Vite React SPA, optimised for Railway.app

# ─── Stage 1: build the SPA bundle with Node 22 ──────────────────────────────
FROM node:22-alpine AS builder

# Railway (and any CI) passes these as Docker build-args so that Vite can bake
# them into the bundle at build time.  Set these variables in the Railway
# service → Variables panel for the frontend service.
ARG VITE_GOOGLE_CLIENT_ID
ARG VITE_GOOGLE_REDIRECT_URI
ARG VITE_GOOGLE_OAUTH_SCOPE="openid email profile"
ARG VITE_GOOGLE_AUTH_URL="https://accounts.google.com/o/oauth2/v2/auth"
ARG VITE_API_BASE_URL

# Expose them as ENV so `npm run build` (Vite) picks them up via import.meta.env.
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID \
    VITE_GOOGLE_REDIRECT_URI=$VITE_GOOGLE_REDIRECT_URI \
    VITE_GOOGLE_OAUTH_SCOPE=$VITE_GOOGLE_OAUTH_SCOPE \
    VITE_GOOGLE_AUTH_URL=$VITE_GOOGLE_AUTH_URL \
    VITE_API_BASE_URL=$VITE_API_BASE_URL

WORKDIR /app

# Install deps from lockfile (deterministic, fast).  Cached until either
# package.json or package-lock.json change.
COPY package.json package-lock.json ./
RUN --mount=type=cache,id=s/94cd0ef2-8d19-439c-ab49-bc033f586504-/root/.npm,target=/root/.npm \
    npm ci --no-audit --no-fund --prefer-offline

# Build the SPA.
COPY . .
RUN npm run build


# ─── Stage 2: serve with nginx (unprivileged image, listens as uid 101) ──────
FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

# Default values; override via Railway env vars.
ENV PORT=8080 \
    BACKEND_URL=http://backend:8080 \
    NGINX_ENVSUBST_FILTER="^(PORT|BACKEND_URL)$"

# Site config — base image runs envsubst on /etc/nginx/templates/*.template
# at container start, rendering into /etc/nginx/conf.d/.  The FILTER above
# limits substitution to PORT/BACKEND_URL so nginx variables ($host etc.)
# are left intact.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Static bundle.  --chown matches the unprivileged 'nginx' user (uid 101).
COPY --from=builder --chown=nginx:nginx /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- "http://127.0.0.1:${PORT}/healthz" | grep -q ok || exit 1

# CMD is inherited from the base image (`nginx -g 'daemon off;'`).
