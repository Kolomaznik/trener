# =============================================================================
# GlitchTip — web service
# =============================================================================
# This Dockerfile wraps the official GlitchTip image and adds a startup step
# that runs database migrations before starting the gunicorn web server.
#
# Railway deployment:
#   Service type : Web
#   Root Dir     : SENTRY/
#   Dockerfile   : Dockerfile          ← this file
#   Exposed port : $PORT (set automatically by Railway)
#
# Required environment variables → see .env.example
# =============================================================================

FROM glitchtip/glitchtip:latest

# Run migrations (idempotent), attempt to create the superuser if the
# DJANGO_SUPERUSER_* variables are set (fails silently if user already
# exists), then start gunicorn.
CMD sh -c "\
  python manage.py migrate --noinput && \
  python manage.py createsuperuser --noinput 2>/dev/null || true && \
  gunicorn glitchtip.wsgi \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${WEB_CONCURRENCY:-2} \
    --timeout 120 \
    --log-file - \
"
