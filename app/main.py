"""Main FastAPI application."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import SECRET_KEY, BASE_DIR
from app.database.database import init_db
from app.auth.routes import router as auth_router
from app.services.cronjob.routes import router as cronjob_router
from app.services.dashboard.routes import router as dashboard_router
from app.services.cronjob.scheduler import start_scheduler, shutdown_scheduler, load_cronjobs_into_scheduler
from app.init_db import ensure_default_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Startup
    await init_db()
    await ensure_default_user()
    start_scheduler()
    await load_cronjobs_into_scheduler()
    logger.info("Application started")
    yield
    # Shutdown
    shutdown_scheduler()
    logger.info("Application shutdown")


app = FastAPI(title="Control Server Web GUI", lifespan=lifespan)

# Session middleware (32 bytes = 256 bits for secret)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=86400 * 7)  # 7 days

# Mount static files
static_path = BASE_DIR / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# API routes
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(cronjob_router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve SPA - redirect to login or dashboard."""
    return RedirectResponse(url="/login", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    """Setup page (password change + 2FA)."""
    return templates.TemplateResponse("setup.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/cronjobs", response_class=HTMLResponse)
async def cronjobs_page(request: Request):
    """Cronjob manager page."""
    return templates.TemplateResponse("cronjobs.html", {"request": request})
