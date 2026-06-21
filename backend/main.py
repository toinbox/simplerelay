from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from backend.database import init_db
from backend.config import settings
from backend.i18n import get_all_translations
from backend.routers import providers, clients, dashboard, auth, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="SimpleRelay",
    version="1.1.0",
    lifespan=lifespan,
)

# API routes
app.include_router(auth.router)
app.include_router(providers.router)
app.include_router(clients.router)
app.include_router(dashboard.router)
app.include_router(admin.router)


# --- i18n endpoint (public) ---

@app.get("/api/i18n/{lang}")
def get_translations(lang: str):
    if lang not in settings.supported_languages:
        lang = settings.default_language
    return get_all_translations(lang)


@app.get("/api/languages")
def get_languages():
    language_names = {
        "en": "English",
        "cs": "Čeština",
        "de": "Deutsch",
        "ru": "Русский",
        "es": "Español",
    }
    return [
        {"code": lang, "name": language_names.get(lang, lang)}
        for lang in settings.supported_languages
    ]


@app.get("/api/relay-info")
def get_relay_info():
    """Public endpoint: relay connection details for users."""
    return {
        "hostname": settings.hostname,
        "port": settings.port,
    }


# --- Test email (authenticated) ---

@app.post("/api/test-email")
async def send_test_email(request: Request):
    import uuid
    import aiosmtplib
    from email.message import EmailMessage
    from backend.services.auth import get_current_user
    from backend.database import get_db

    data = await request.json()
    to_email = data.get("to")
    from_email = data.get("from")

    if not to_email or not from_email:
        return JSONResponse({"error": "Missing 'to' or 'from'"}, status_code=400)

    # Extract sender domain for Message-ID
    sender_domain = from_email.split("@")[-1] if "@" in from_email else "localhost"

    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = "SimpleRelay Test"
    msg["Message-Id"] = f"<{uuid.uuid4()}@{sender_domain}>"
    msg.set_content(
        "This is a test email from SimpleRelay.\n"
        "If you received this, your relay is working correctly.\n\n"
        "— SimpleRelay",
        cte="quoted-printable",
    )

    try:
        await aiosmtplib.send(
            msg,
            hostname="127.0.0.1",
            port=settings.port,
        )
        return {"success": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# --- Serve frontend ---

frontend_dir = Path("/app/frontend/dist")

if frontend_dir.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dir / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = frontend_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dir / "index.html")
