# config.py — Configuración de conexiones a SQL Server
# EDITAR antes de usar: completar usuario y contraseña

# ── FIX SSL: OpenSSL 3.x no permite TLS 1.0 (SQL Server 2012) ──
# Crear config legacy si estamos en Mac/Linux y no existe
import os as _os
import platform as _platform
import socket as _socket

_is_windows = _platform.system() == "Windows"
if not _is_windows:
    _ssl_conf = "/tmp/openssl_legacy.cnf"
    if not _os.path.exists(_ssl_conf):
        with open(_ssl_conf, "w") as _f:
            _f.write(
                "openssl_conf = openssl_init\n"
                "[openssl_init]\nssl_conf = ssl_sect\n"
                "[ssl_sect]\nsystem_default = system_default_sect\n"
                "[system_default_sect]\n"
                "MinProtocol = TLSv1\nCipherString = DEFAULT@SECLEVEL=0\n"
            )
    _os.environ.setdefault("OPENSSL_CONF", _ssl_conf)

# ── SERVIDOR ──────────────────────────────────────────
# DELL-SVR = producción (192.168.2.111) — es el que acepta login SQL
# DATASVRW = réplica (192.168.2.112) — credenciales distintas (pendiente)
# Mac/remoto — Driver 17 + fix SSL legacy
_hostname = _socket.gethostname().upper()

if _hostname in ("DELL-SVR", "DELLSVR"):
    SERVIDOR = "localhost"
    _LOCAL = True       # en el propio server de producción
    _DRIVER = "ODBC Driver 17 for SQL Server"
elif _is_windows:
    # Otro Windows en la LAN (ej: DATASVRW .112) — Driver 17
    SERVIDOR = "192.168.2.111"
    _LOCAL = False
    _DRIVER = "ODBC Driver 17 for SQL Server"
else:
    # Mac / Linux — Driver 17 (Driver 18 fuerza TLS 1.2, incompatible con SQL Server 2012)
    SERVIDOR = "192.168.2.111"
    _LOCAL = False
    _DRIVER = "ODBC Driver 17 for SQL Server"

# ── CREDENCIALES ─────────────────────────────────────
USUARIO  = "am"
PASSWORD = "dl"

# ── BASES DE DATOS ────────────────────────────────────
BD_COMPRAS   = "msgestionC"       # compras, ventas, pedidos
BD_ARTICULOS = "msgestion01art"   # maestro de artículos, marcas, etc.
BD_ANALITICA = "omicronvt"        # agrupadores, recupero de inversión, etc.

# ── STRINGS DE CONEXIÓN ───────────────────────────────
def get_conn_string(base):
    # _LOCAL (DELL-SVR): localhost sin SSL
    # Windows LAN (DATASVRW): .111 con Driver 17 sin SSL
    # Mac/remoto: .111 con Driver 18 + Encrypt=Optional
    conn = (
        f"DRIVER={{{_DRIVER}}};"
        f"SERVER={SERVIDOR};"
        f"DATABASE={base};"
        f"UID={USUARIO};"
        f"PWD={PASSWORD};"
        f"Connection Timeout=15;"
    )
    if not _is_windows:
        conn += "TrustServerCertificate=yes;Encrypt=no;"
    return conn

CONN_COMPRAS   = get_conn_string(BD_COMPRAS)
CONN_ARTICULOS = get_conn_string(BD_ARTICULOS)
CONN_ANALITICA = get_conn_string(BD_ANALITICA)

# ── CONSTANTES DE NEGOCIO ─────────────────────────────
EMPRESA_DEFAULT   = "H4"           # empresa por defecto para pedidos
BD_BASE_H4        = "MSGESTION03"  # base subyacente de H4 (para insert directo)
CODIGOS_REMITO    = (7, 36)        # excluir siempre
CODIGO_FACTURA    = 1
CODIGO_NC         = 3

# ── PROVEEDORES ─────────────────────────────────────────
# Cada proveedor define su estructura de pricing:
#   precio_fabrica (base del proveedor)
#   → descuento (%) → precio_costo = precio_fabrica × (1 - descuento/100)
#   → utilidad_1..4 (%) → precio_1..4 = precio_costo × (1 + utilidad/100)
#   formula: código de fórmula de markup en el sistema (1 = estándar)
#
# Para agregar un nuevo proveedor: copiar bloque, ajustar valores.
PROVEEDORES = {
    668: {
        "nombre":      "ALPARGATAS S.A.I.C.",
        "cuit":        "30500525327",
        "condicion_iva": "I",
        "zona":        4,
        "marca":       314,          # TOPPER
        "descuento":   6,            # descuento del proveedor sobre precio_fabrica
        "utilidad_1":  98.9,         # → precio_1 (Contado)
        "utilidad_2":  122.9,        # → precio_2 (Lista)
        "utilidad_3":  60,           # → precio_3 (Intermedio)
        "utilidad_4":  45,           # → precio_4 (Mayorista)
        "formula":     1,
        "descuento_1": 0,
        "descuento_2": 0,
    },
    104: {
        "nombre":        '"EL GITANO" - GTN',
        "cuit":          "20269920948",
        "condicion_iva": "I",
        "zona":          18,
        "marca":         104,          # GTN
        "empresa":       "CALZALINDO", # 100% base 01
        "descuento":     0,
        "utilidad_1":    0,
        "utilidad_2":    0,
        "utilidad_3":    0,
        "utilidad_4":    0,
        "formula":       1,
        "descuento_1":   0,
        "descuento_2":   0,
    },
    # ── WAKE (Industrias AS S.A.) ──
    594: {
        "nombre":      "INDUSTRIAS AS S.A.",
        "cuit":        "",                   # completar
        "condicion_iva": "I",
        "zona":        4,
        "marca":       746,          # WAKE
        "descuento":   20,           # descuento sobre precio_fabrica
        "utilidad_1":  100,          # → precio_1 (Contado)
        "utilidad_2":  124,          # → precio_2 (Lista)
        "utilidad_3":  60,           # → precio_3 (Intermedio)
        "utilidad_4":  45,           # → precio_4 (Mayorista)
        "formula":     1,
        "descuento_1": 0,
        "descuento_2": 0,
    },
    # ── DISTRINANDO DEPORTES (Reebok, Crocs, etc.) ──
    656: {
        "nombre":      "DISTRINANDO DEPORTES S.A.",
        "cuit":        "30573011879",
        "condicion_iva": "I",
        "zona":        5,
        "marca":       513,          # REEBOK (principal)
        "descuento":   0,            # sin descuento fijo — viene en cada factura
        "utilidad_1":  90,           # → precio_1 (Contado)
        "utilidad_2":  114,          # → precio_2 (Lista)
        "utilidad_3":  60,           # → precio_3 (Intermedio)
        "utilidad_4":  45,           # → precio_4 (Mayorista)
        "formula":     1,
        "descuento_1": 0,
        "descuento_2": 0,
    },
    # ── RINGO (Souter S.A.) ──
    561: {
        "nombre":        "Souter S.A.",
        "cuit":          "30707508597",
        "condicion_iva": "I",
        "zona":          5,
        "marca":         294,          # CARMEL / RINGO
        "empresa":       "H4",        # compras recientes son H4
        "descuento":     0,
        "utilidad_1":    80,           # copiado del artículo CARMEL existente
        "utilidad_2":    114,
        "utilidad_3":    60,
        "utilidad_4":    45,
        "formula":       1,
        "descuento_1":   0,
        "descuento_2":   0,
    },
    # ── CONFORTABLE SRL ──
    236: {
        "nombre":        "CONFORTABLE SRL",
        "cuit":          "30700175088",
        "condicion_iva": "I",
        "zona":          6,
        "marca":         236,          # CONFORTABLE
        "empresa":       "CALZALINDO", # 100% base 01
        "descuento":     15,
        "utilidad_1":    140,
        "utilidad_2":    124,
        "utilidad_3":    60,
        "utilidad_4":    45,
        "formula":       1,
        "descuento_1":   0,
        "descuento_2":   0,
    },
    # ── AMPHORA ──
    44: {
        "nombre":        "AMPHORA",
        "cuit":          "30708994002",
        "condicion_iva": "I",
        "zona":          6,
        "marca":         44,
        "empresa":       "H4",
        "descuento":     0,
        "utilidad_1":    100,
        "utilidad_2":    124,
        "utilidad_3":    60,
        "utilidad_4":    45,
        "formula":       1,
        "descuento_1":   0,
        "descuento_2":   0,
    },
    # ── LESEDIFE S.A. ──
    42: {
        "nombre":        "LESEDIFE S.A.",
        "cuit":          "30661041486",
        "condicion_iva": "I",
        "zona":          3,
        "marca":         42,            # LESEDIFE (también usa 348)
        "empresa":       "H4",          # factura a H4, el 50% "bon volumen" es split ABI/H4
        "descuento":     19,            # descuento real sobre precio lista
        "utilidad_1":    120,           # → precio_1 (Contado)
        "utilidad_2":    144,           # → precio_2 (Lista)
        "utilidad_3":    60,            # → precio_3 (Intermedio)
        "utilidad_4":    45,            # → precio_4 (Mayorista)
        "formula":       1,
        "descuento_1":   0,
        "descuento_2":   0,
    },
    # ── DIADORA (Calzados Blanco S.A.) ──
    614: {
        "nombre":        "CALZADOS BLANCO S.A.",
        "cuit":          "30707450394",
        "condicion_iva": "I",
        "zona":          1,
        "marca":         675,          # DIADORA (codigo en tabla marcas)
        "empresa":       "H4",
        "descuento":     10,           # 10% desc comercial (obs_factura: "10%+5% en Fact")
        "utilidad_1":    100,          # → precio_1 (Contado) — copiado de arts existentes prov 614
        "utilidad_2":    124,          # → precio_2 (Lista)
        "utilidad_3":    60,           # → precio_3 (Intermedio)
        "utilidad_4":    45,           # → precio_4 (Mayorista)
        "formula":       1,
        "descuento_1":   0,
        "descuento_2":   0,
    },
    # ── Ejemplo para otro proveedor ──
    # 794: {
    #     "nombre":      "LUCIA",
    #     "cuit":        "...",
    #     "condicion_iva": "I",
    #     "zona":        1,
    #     "marca":       ...,
    #     "descuento":   0,
    #     "utilidad_1":  80,
    #     "utilidad_2":  100,
    #     "utilidad_3":  50,
    #     "utilidad_4":  35,
    #     "formula":     1,
    #     "descuento_1": 0,
    #     "descuento_2": 0,
    # },
}


def calcular_precios(precio_fabrica: float, proveedor_id: int) -> dict:
    """
    Calcula toda la cadena de precios a partir del precio de fábrica
    y la configuración del proveedor.

    Retorna dict con: precio_fabrica, descuento, precio_costo,
    utilidad_1..4, precio_1..4, precio_sugerido, formula, descuento_1, descuento_2
    """
    prov = PROVEEDORES.get(proveedor_id)
    if not prov:
        # Fallback: buscar dinámicamente en la BD
        try:
            from proveedores_db import obtener_pricing_proveedor
            prov = obtener_pricing_proveedor(proveedor_id)
        except Exception:
            pass
    if not prov:
        raise ValueError(f"Proveedor {proveedor_id} no encontrado ni en config.py ni en BD")

    desc = prov["descuento"]
    precio_costo = round(precio_fabrica * (1 - desc / 100), 4)

    return {
        "precio_fabrica": precio_fabrica,
        "descuento":      desc,
        "precio_costo":   precio_costo,
        "precio_sugerido": round(precio_costo, 2),
        "utilidad_1":     prov["utilidad_1"],
        "utilidad_2":     prov["utilidad_2"],
        "utilidad_3":     prov["utilidad_3"],
        "utilidad_4":     prov["utilidad_4"],
        "precio_1":       round(precio_costo * (1 + prov["utilidad_1"] / 100), 2),
        "precio_2":       round(precio_costo * (1 + prov["utilidad_2"] / 100), 2),
        "precio_3":       round(precio_costo * (1 + prov["utilidad_3"] / 100), 2),
        "precio_4":       round(precio_costo * (1 + prov["utilidad_4"] / 100), 2),
        "formula":        prov["formula"],
        "descuento_1":    prov["descuento_1"],
        "descuento_2":    prov["descuento_2"],
    }


# Subrubros por industria (para calcular período)
SUBRUBROS_ZAPATERIA    = list(range(1,10)) + list(range(11,18)) + [20,21,34,35,37,38] + list(range(40,45))
SUBRUBROS_DEPORTES     = [10,19,22,33,45] + list(range(47,52)) + [53,54,59]
SUBRUBROS_MIXTO        = [52, 55]
SUBRUBROS_MARROQUINERIA= [18,24,25,26,30,31,39,58]
SUBRUBROS_INDUMENTARIA = [23,46,57,61,62,63]
SUBRUBROS_COSMETICA    = [27,28,29,32]
