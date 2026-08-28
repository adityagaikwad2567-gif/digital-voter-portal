"""WSGI entry point for gunicorn.

The app instance is created in app/__init__.py so both
  gunicorn app:app   (Render default / cached config)
  gunicorn wsgi:app  (explicit via Procfile)
work correctly.
"""
from app import app  # noqa: F401
