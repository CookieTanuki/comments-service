#!/bin/sh
set -eu

mkdir -p /app/backend/staticfiles /app/backend/media

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  python manage.py shell <<'PY'
import os

from django.contrib.auth import get_user_model


User = get_user_model()
username = os.environ["DJANGO_SUPERUSER_USERNAME"]
email = os.environ["DJANGO_SUPERUSER_EMAIL"]
password = os.environ["DJANGO_SUPERUSER_PASSWORD"]

user, created = User.objects.get_or_create(
    username=username,
    defaults={
        "email": email,
        "is_staff": True,
        "is_superuser": True,
    },
)

changed = created

if user.email != email:
    user.email = email
    changed = True

if not user.is_staff:
    user.is_staff = True
    changed = True

if not user.is_superuser:
    user.is_superuser = True
    changed = True

user.set_password(password)
changed = True

if changed:
    user.save()
PY
fi

exec "$@"
