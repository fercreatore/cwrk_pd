# -*- coding: utf-8 -*-
"""
Renovación automática del access_token de MercadoLibre (OAuth2).
Soporta múltiples cuentas ML.

El token de ML vence cada 6 horas. Este script lee mercadolibre_config_{cuenta}.json,
hace el refresh via OAuth2 y guarda el nuevo token en el mismo archivo.

USO:
    # Renovar token de cuenta default (calzalindo_h)
    python -m multicanal.refresh_token_ml

    # Renovar cuenta específica
    python -m multicanal.refresh_token_ml --account calzalindo_tama

    # Renovar TODAS las cuentas
    python -m multicanal.refresh_token_ml --all

    # Verificar sin renovar
    python -m multicanal.refresh_token_ml --check
    python -m multicanal.refresh_token_ml --check --account calzalindo_lu

    # Cron cada 4 horas (antes del vencimiento de 6hs):
    # 0 */4 * * * cd /path/to/cowork_pedidos && python -m multicanal.refresh_token_ml --all >> /var/log/ml_token.log 2>&1
"""

import glob
import json
import os
import sys
from datetime import datetime

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ML_AUTH_URL = 'https://api.mercadolibre.com/oauth/token'

# Tiempo de vida del token en segundos (6 horas = 21600s)
TOKEN_TTL_SECONDS = 21600
# Margen de seguridad: renovar si faltan menos de 90 minutos
REFRESH_MARGIN_SECONDS = 5400

# Directorio de configs
_CONFIG_DIR = os.path.dirname(__file__)


# ── Multi-cuenta ──

def _config_path(account: str = None) -> str:
    """Retorna el path al config file de una cuenta."""
    if account:
        return os.path.join(_CONFIG_DIR, f'mercadolibre_config_{account}.json')
    return os.path.join(_CONFIG_DIR, 'mercadolibre_config.json')


def listar_cuentas() -> list:
    """Lista todas las cuentas ML configuradas."""
    cuentas = []
    # Default
    default = _config_path()
    if os.path.exists(default):
        cuentas.append(None)  # None = default
    # Named
    for f in sorted(glob.glob(os.path.join(_CONFIG_DIR, 'mercadolibre_config_*.json'))):
        nombre = os.path.basename(f).replace('mercadolibre_config_', '').replace('.json', '')
        cuentas.append(nombre)
    return cuentas


def cargar_config(account: str = None) -> dict:
    """Lee config de una cuenta ML. None = default."""
    path = _config_path(account)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def guardar_config(config: dict, account: str = None):
    """Escribe config preservando campos existentes."""
    config['updated_at'] = datetime.now().isoformat()
    path = _config_path(account)
    with open(path, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def token_vigente(config: dict) -> bool:
    """
    Verifica si el token actual todavía es válido según updated_at + TTL.
    Retorna True si falta más de REFRESH_MARGIN_SECONDS para el vencimiento.
    """
    updated_at = config.get('updated_at', '')
    if not updated_at:
        return False

    try:
        fecha_update = datetime.fromisoformat(updated_at)
    except (ValueError, TypeError):
        return False

    segundos_desde_update = (datetime.now() - fecha_update).total_seconds()
    segundos_restantes = TOKEN_TTL_SECONDS - segundos_desde_update

    if segundos_restantes > REFRESH_MARGIN_SECONDS:
        horas_restantes = segundos_restantes / 3600
        print(f"  Token vigente — vence en {horas_restantes:.1f}h")
        return True

    if segundos_restantes > 0:
        print(f"  Token por vencer en {segundos_restantes / 60:.0f} min — renovando...")
    else:
        print(f"  Token vencido hace {abs(segundos_restantes) / 60:.0f} min — renovando...")

    return False


def refresh_token(account: str = None, force: bool = False) -> dict:
    """
    Renueva el access_token de ML usando el refresh_token via OAuth2.

    Args:
        account: Nombre de cuenta ('calzalindo_tama', 'calzalindo_lu', None=default)
        force: Si True, renueva aunque no haya vencido.

    Returns:
        dict con resultado: {'ok': True, 'access_token': '...', 'expires_in': ...}
        o {'ok': False, 'error': '...'}
    """
    nombre = account or 'default'
    config = cargar_config(account)

    if not config:
        return {'ok': False, 'error': f'No existe config para cuenta {nombre}. Crear archivo primero.'}

    # Campos requeridos para refresh OAuth2
    refresh_tok = config.get('refresh_token', '')
    client_id = config.get('client_id', '')
    client_secret = config.get('client_secret', '')

    if not refresh_tok:
        # Sin refresh_token, no podemos renovar — pero el token puede ser válido
        # si viene de n8n (que lo refresca por su cuenta)
        if config.get('access_token'):
            return {'ok': True, 'access_token': config['access_token'],
                    'skipped': True, 'reason': 'Sin refresh_token — usando token existente'}
        return {'ok': False, 'error': f'Cuenta {nombre}: no hay refresh_token ni access_token.'}

    if not client_id or not client_secret:
        return {'ok': False, 'error': f'Cuenta {nombre}: faltan client_id y/o client_secret.'}

    # Verificar si hace falta renovar
    if not force and token_vigente(config):
        return {'ok': True, 'access_token': config.get('access_token', ''), 'skipped': True}

    # POST OAuth2 refresh
    payload = {
        'grant_type': 'refresh_token',
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_tok,
    }

    try:
        resp = requests.post(ML_AUTH_URL, data=payload, timeout=30)
    except requests.RequestException as e:
        return {'ok': False, 'error': f'Cuenta {nombre}: error de conexión: {e}'}

    if resp.status_code != 200:
        return {
            'ok': False,
            'error': f'Cuenta {nombre}: HTTP {resp.status_code}: {resp.text[:300]}',
            'status_code': resp.status_code,
        }

    data = resp.json()

    nuevo_access = data.get('access_token', '')
    nuevo_refresh = data.get('refresh_token', '')
    expires_in = data.get('expires_in', TOKEN_TTL_SECONDS)

    if not nuevo_access:
        return {'ok': False, 'error': f'Cuenta {nombre}: respuesta sin access_token', 'response': data}

    # Guardar tokens actualizados
    config['access_token'] = nuevo_access
    if nuevo_refresh:
        config['refresh_token'] = nuevo_refresh
    config['expires_in'] = expires_in
    config['user_id'] = str(data.get('user_id', config.get('user_id', '')))
    guardar_config(config, account)

    print(f"  [{nombre}] Token renovado OK — expira en {expires_in / 3600:.1f}h")

    return {
        'ok': True,
        'access_token': nuevo_access,
        'expires_in': expires_in,
        'user_id': config['user_id'],
        'account': nombre,
    }


def refresh_all(force: bool = False) -> list:
    """Renueva tokens de TODAS las cuentas configuradas."""
    resultados = []
    cuentas = listar_cuentas()

    if not cuentas:
        print("No hay cuentas ML configuradas.")
        return resultados

    for cuenta in cuentas:
        nombre = cuenta or 'default'
        print(f"\n  --- Cuenta: {nombre} ---")
        r = refresh_token(account=cuenta, force=force)
        r['account'] = nombre
        resultados.append(r)

    return resultados


def check_token(account: str = None) -> dict:
    """Verifica el estado del token sin renovar."""
    nombre = account or 'default'
    config = cargar_config(account)
    if not config:
        return {'ok': False, 'error': f'No existe config para cuenta {nombre}'}

    access = config.get('access_token', '')
    updated = config.get('updated_at', '')
    has_refresh = bool(config.get('refresh_token'))
    has_credentials = bool(config.get('client_id') and config.get('client_secret'))

    resultado = {
        'cuenta': nombre,
        'user_id': config.get('user_id', ''),
        'empresa': config.get('empresa', ''),
        'tiene_access_token': bool(access),
        'tiene_refresh_token': has_refresh,
        'tiene_credenciales': has_credentials,
        'updated_at': updated,
        'vigente': token_vigente(config),
    }

    if updated:
        try:
            fecha = datetime.fromisoformat(updated)
            segs = (datetime.now() - fecha).total_seconds()
            resultado['edad_minutos'] = round(segs / 60, 1)
            resultado['restante_minutos'] = round((TOKEN_TTL_SECONDS - segs) / 60, 1)
        except (ValueError, TypeError):
            pass

    return resultado


# ── Actualización desde n8n ──

def actualizar_desde_n8n(tokens_dict: dict):
    """
    Recibe un dict con tokens frescos de n8n y actualiza los config files.

    Args:
        tokens_dict: {
            'calzalindo_h': 'Bearer APP_USR-...',
            'calzalindo_tama': 'Bearer APP_USR-...',
            'calzalindo_lu': 'Bearer APP_USR-...',
            'tiendanube': 'bearer ...',
            'id_tiendanube': '7018867',
            'tiendanube2': 'bearer ...',
            'id_tiendanube2': '6466615',
        }
    """
    # ML accounts
    ml_mapping = {
        'calzalindo_h': (None, '196198035', 'H4'),       # default
        'calzalindo_tama': ('tama', '159354061', 'ABI'),
        'calzalindo_lu': ('lu', '529435195', 'ABI'),
    }

    for key, (account, user_id, empresa) in ml_mapping.items():
        token_raw = tokens_dict.get(key, '')
        if not token_raw:
            continue
        # Quitar "Bearer " prefix si existe
        access_token = token_raw.replace('Bearer ', '').replace('bearer ', '').strip()

        config = cargar_config(account)
        config['access_token'] = access_token
        config['user_id'] = user_id
        config['empresa'] = empresa
        config['account_name'] = key
        guardar_config(config, account)
        print(f"  [{key}] Token ML actualizado desde n8n")

    # TN accounts
    tn_mapping = {
        ('tiendanube', 'id_tiendanube'): None,       # default (Calzalindo)
        ('tiendanube2', 'id_tiendanube2'): 'godance',
    }

    for (token_key, id_key), nombre in tn_mapping.items():
        token_raw = tokens_dict.get(token_key, '')
        store_id = str(tokens_dict.get(id_key, ''))
        if not token_raw:
            continue
        access_token = token_raw.replace('Bearer ', '').replace('bearer ', '').strip()

        from multicanal.facturador_tn import cargar_config_tienda, guardar_config_tienda
        guardar_config_tienda(store_id=store_id, access_token=access_token,
                              nombre_tienda=nombre, empresa='H4')
        print(f"  [TN-{nombre or 'default'}] Token TN actualizado desde n8n")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Renovar access_token de MercadoLibre (OAuth2)')
    parser.add_argument('--check', action='store_true', help='Solo verificar estado del token')
    parser.add_argument('--force', action='store_true', help='Forzar renovación aunque no haya vencido')
    parser.add_argument('--account', type=str, default=None,
                        help='Cuenta específica (calzalindo_h, calzalindo_tama, calzalindo_lu)')
    parser.add_argument('--all', action='store_true', help='Renovar TODAS las cuentas')
    parser.add_argument('--from-n8n', type=str, default=None,
                        help='Path a CSV exportado de n8n para actualizar tokens')
    args = parser.parse_args()

    print(f"\n{'='*50}")
    print(f"  ML Token Refresh — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    # Actualizar desde CSV de n8n
    if args.from_n8n:
        import csv
        with open(args.from_n8n) as f:
            reader = csv.DictReader(f)
            for row in reader:
                actualizar_desde_n8n(row)
        print("\nTokens actualizados desde n8n CSV.")
        sys.exit(0)

    if args.check:
        if args.all:
            for cuenta in listar_cuentas():
                info = check_token(cuenta)
                print(f"\n  --- {info.get('cuenta', 'default')} ---")
                for k, v in info.items():
                    print(f"  {k}: {v}")
        else:
            info = check_token(args.account)
            for k, v in info.items():
                print(f"  {k}: {v}")
        sys.exit(0)

    if args.all:
        resultados = refresh_all(force=args.force)
        ok = sum(1 for r in resultados if r.get('ok'))
        fail = sum(1 for r in resultados if not r.get('ok'))
        print(f"\n  Resultado: {ok} OK, {fail} errores de {len(resultados)} cuentas")
        sys.exit(0 if fail == 0 else 1)

    resultado = refresh_token(account=args.account, force=args.force)

    if resultado.get('ok'):
        if resultado.get('skipped'):
            reason = resultado.get('reason', 'No fue necesario renovar')
            print(f"\n  {reason}")
        else:
            print("\n  Renovación exitosa.")
        sys.exit(0)
    else:
        print(f"\n  ERROR: {resultado['error']}")
        sys.exit(1)
