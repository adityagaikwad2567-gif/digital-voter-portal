"""Vercel serverless entry point — wraps the Flask WSGI app."""
from app import app  # noqa: F401 — Vercel looks for 'app' variable
