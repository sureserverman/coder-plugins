# Django — `locale/<lang>/LC_MESSAGES/django.po`

Standard gettext .po — see [gettext.md](gettext.md). Specifics:

- Extract with `python manage.py makemessages -l es` (template `{% trans %}` and `{% blocktrans %}`, Python `gettext`/`gettext_lazy`/`ngettext`).
- Compile with `python manage.py compilemessages` (produces `.mo`).
- Locale codes are CLDR (`es`, `es-mx` — note lowercase region).
