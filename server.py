#!/usr/bin/env python3
"""Learnwella MVP: landing + authentication + opportunities + builder workspace + funding marketplace.
Run: python3 server.py  then open http://127.0.0.1:8080
No external Python packages required.
"""
from __future__ import annotations
import base64, hashlib, html, json, mimetypes, os, re, secrets, sqlite3, sys, smtplib, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from email.message import EmailMessage
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse, urlencode

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "edubridge.sqlite3"
STATIC_DIR = ROOT / "static"
UPLOAD_DIR = ROOT / "uploads"
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))
APP_NAME = "Learnwella"
APP_VERSION = "v11-unlimited-project-uploads-profile-10mb"
COMPANY_NAME = "Nexus Company Ltd"
APP_TAGLINE = "Find the opportunity. Show the build. Start the conversation."
OWNER_ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "honoremukunzi6@gmail.com").strip().lower()
SESSION_COOKIE = "edubridge_session"
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", "0"))  # 0 means no Learnwella app limit for project/media uploads

PAYMENT_LINKS = {
    "flutterwave": os.environ.get("FLUTTERWAVE_PAYMENT_LINK", ""),
    "stripe": os.environ.get("STRIPE_PAYMENT_LINK", ""),
    "paypal": os.environ.get("PAYPAL_PAYMENT_LINK", ""),
    "momo": os.environ.get("MOMO_PAYMENT_LINK", ""),
}
MOMO_INSTRUCTIONS = os.environ.get("MOMO_PAYMENT_INSTRUCTIONS", "Set MOMO_PAYMENT_INSTRUCTIONS in your environment, for example: MTN MoMo pay merchant code XXXXX and include the pledge reference.")
RSS_SOURCES = [
    "https://www.opportunitiesforafricans.com/feed/",
    "https://www.globalsouthopportunities.com/feed/",
]

APP_BASE_URL = os.environ.get("APP_BASE_URL", f"http://{HOST}:{PORT}").rstrip("/")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER or "noreply@learnwella.local")
SMTP_TLS = os.environ.get("SMTP_TLS", "1") != "0"
# Bird / MessageBird email API. Keep the API key in environment variables, never in code.
BIRD_API_KEY = os.environ.get("BIRD_API_KEY", "")
BIRD_FROM = os.environ.get("BIRD_FROM", "onboarding@messagebird.dev")
BIRD_REGION = os.environ.get("BIRD_REGION", "")
MAIL_OUTBOX = ROOT / "mail_outbox.log"
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_UPLOAD_PRESET = os.environ.get("CLOUDINARY_UPLOAD_PRESET", "")

# ... file continues unchanged below ...
