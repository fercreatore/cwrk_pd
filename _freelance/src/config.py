# -*- coding: utf-8 -*-
"""
Configuración del sistema Vendedor Freelance — FastAPI
Conexión a SQL Server (mismas bases que web2py)
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # ── SQL Server ──────────────────────────────────────
    DB_SERVER: str = "192.168.2.111"
    DB_USER: str = "am"
    DB_PASSWORD: str = "dl"
    DB_PORT: int = 1433

    # Bases de datos
    DB_COMPRAS: str = "msgestionC"
    DB_ARTICULOS: str = "msgestion01art"
    DB_ANALITICA: str = "omicronvt"
    DB_AUTH: str = "clz_ventas_sql"

    # ── App ──────────────────────────────────────────────
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8001
    APP_TITLE: str = "H4 - Sistema Vendedor Freelance"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ── Fotos ────────────────────────────────────────────
    FOTOS_BASE_PATH: str = r"C:\fotos_catalogo"

    # ── Fee defaults ─────────────────────────────────────
    FEE_STD: float = 0.05       # 5%
    FEE_PREMIUM: float = 0.08   # 8%

    # ── URL base para links de atribución ────────────────
    LINK_BASE: str = "https://h4calzados.com/p"

    # ── MySQL Auth (clz_ventas_mysql en .109) ──────────────
    MYSQL_AUTH_HOST: str = "192.168.2.109"
    MYSQL_AUTH_USER: str = "root"
    MYSQL_AUTH_PASSWORD: str = "cagr$2011"
    MYSQL_AUTH_DATABASE: str = "clz_ventas_mysql"
    MYSQL_AUTH_CHARSET: str = "utf8mb4"

    class Config:
        env_file = ".env"
        env_prefix = "CLZ_"


settings = Settings()
