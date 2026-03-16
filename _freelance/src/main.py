# -*- coding: utf-8 -*-
"""
H4 — Sistema Vendedor Freelance
FastAPI app principal.
Corre en :8001 conviviendo con web2py en :8000.

Ejecutar:
    cd calzalindo_freelance
    python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
"""
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

from config import settings

# ── Importar routers ─────────────────────────────────────
from api.auth import router as auth_router, get_current_user
from api.vendedor import router as vendedor_router
from api.catalogo import router as catalogo_router
from api.liquidacion import router as liquidacion_router
from api.atribucion import router as atribucion_router
from api.gerencial import router as gerencial_router

# ── App ──────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# ── Static files y templates ─────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ── Registrar routers ────────────────────────────────────
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(vendedor_router, prefix="/api/v1/vendedor", tags=["Vendedor"])
app.include_router(catalogo_router, prefix="/api/v1/catalogo", tags=["Catálogo"])
app.include_router(liquidacion_router, prefix="/api/v1/liquidacion", tags=["Liquidación"])
app.include_router(atribucion_router, prefix="/api/v1/atribucion", tags=["Atribución"])
app.include_router(gerencial_router, prefix="/api/v1/gerencial", tags=["Gerencial"])


# ── Páginas HTML (panel vendedor, admin) ─────────────────
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Si ya tiene sesión, redirigir
    user = await get_current_user(request)
    if user:
        if user.get("es_admin"):
            return RedirectResponse("/admin/dashboard")
        elif user.get("codigo_vendedor"):
            return RedirectResponse("/panel/%s" % user["codigo_vendedor"])
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/panel/{codigo_vendedor}", response_class=HTMLResponse)
async def panel_vendedor(request: Request, codigo_vendedor: str):
    """Panel personal del vendedor freelance (mobile-first)."""
    return templates.TemplateResponse("panel_vendedor.html", {
        "request": request,
        "codigo": codigo_vendedor,
    })


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Dashboard gerencial de la red freelance."""
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
    })


# ── Health check ─────────────────────────────────────────
@app.get("/health")
async def health():
    from db import query_omicronvt
    try:
        rows = query_omicronvt("SELECT 1 AS ok")
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "error", "db": str(e)}
