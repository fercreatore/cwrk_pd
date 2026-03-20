# -*- coding: utf-8 -*-
"""
Renovación automática del access_token de MercadoLibre (OAuth2).

El token de ML vence cada 6 horas. Este script lee mercadolibre_config.json,
hace el refresh via OAuth2 y guarda el nuevo token en el mismo archivo.

USO:
    # Renovar token
    python -m multicanal.refresh_token_ml

    # Verificar sin renovar
    python -m multicanal.refresh_token_ml --check

    # Desde código
    from multicanal.refresh_token_ml import refresh_token
    resultado = refresh_token()

    # Cron cada 5 horas (antes del vencimiento de 6hs):
    # 0 */5 * * * cd /path/to/cowork_pedidos && python -m multicanal.refresh_token_ml >> /var/log/ml_token.log 2>&1
"""

import json
import os
import sys
from datetime import datetime

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'mercadolibre_config.json')
ML_AUTH_URL = 'https://api.mercadolibre.com/oauth/token'

# Tiempo de vida del token en segundos (6 horas = 21600s)
TOKEN_TTL_SECONDS = 21600
# Margen de seguridad: renovar si faltan menos de 90 minutos
REFRESH_MARGIN_SECONDS = 5400


def cargar_config() -> dict:
    """Lee mercadolibre_config.json. Retorna dict vacío si no existe."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def guardar_config(config: dict):
    """Escribe mercadolibre_config.json preservando campos existentes."""
    config['updated_at'] = datetime.now().isoformat()
    with open(CONFIG_FILE, 'w') as f:
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


def refresh_token(force: bool = False) -> dict:
    """
    Renueva el access_token de ML usando el refresh_token via OAuth2.

    Args:
        force: Si True, renueva aunque no haya vencido.

    Returns:
        dict con resultado: {'ok': True, 'access_token': '...', 'expires_in': ...}
        o {'ok': False, 'error': '...'}
    """
    config = cargar_config()

    if not config:
        return {'ok': False, 'error': f'No existe {CONFIG_FILE}. Ejecutar guardar_config() primero.'}

    # Campos requeridos
    refresh_tok = config.get('refresh_token', '')
    client_id = config.get('client_id', '')
    client_secret = config.get('client_secret', '')

    if not refresh_tok:
        return {'ok': False, 'error': 'No hay refresh_token en config. Obtener token inicial manualmente.'}
    if not client_id or not client_secret:
        return {'ok': False, 'error': 'Faltan client_id y/o client_secret en config.'}

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
        return {'ok': False, 'error': f'Error de conexión: {e}'}

    if resp.status_code != 200:
        return {
            'ok': False,
            'error': f'HTTP {resp.status_code}: {resp.text[:300]}',
            'status_code': resp.status_code,
        }

    data = resp.json()

    nuevo_access = data.get('access_token', '')
    nuevo_refresh = data.get('refresh_token', '')
    expires_in = data.get('expires_in', TOKEN_TTL_SECONDS)

    if not nuevo_access:
        return {'ok': False, 'error': 'Respuesta sin access_token', 'response': data}

    # Guardar tokens actualizados
    config['access_token'] = nuevo_access
    if nuevo_refresh:
        config['refresh_token'] = nuevo_refresh
    config['expires_in'] = expires_in
    config['user_id'] = data.get('user_id', config.get('user_id', ''))
    guardar_config(config)

    print(f"  Token renovado OK — expira en {expires_in / 3600:.1f}h")
    print(f"  user_id: {config['user_id']}")

    return {
        'ok': True,
        'access_token': nuevo_access,
        'expires_in': expires_in,
        'user_id': config['user_id'],
    }


def check_token() -> dict:
    """Verifica el estado del token sin renovar."""
    config = cargar_config()
    if not config:
        return {'ok': False, 'error': 'No existe mercadolibre_config.json'}

    access = config.get('access_token', '')
    updated = config.get('updated_at', '')
    has_refresh = bool(config.get('refresh_token'))
    has_credentials = bool(config.get('client_id') and config.get('client_secret'))

    resultado = {
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


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Renovar access_token de MercadoLibre (OAuth2)')
    parser.add_argument('--check', action='store_true', help='Solo verificar estado del token')
    parser.add_argument('--force', action='store_true', help='Forzar renovación aunque no haya vencido')
    args = parser.parse_args()

    print(f"\n{'='*50}")
    print(f"  ML Token Refresh — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    if args.check:
        info = check_token()
        for k, v in info.items():
            print(f"  {k}: {v}")
        sys.exit(0)

    resultado = refresh_token(force=args.force)

    if resultado.get('ok'):
        if resultado.get('skipped'):
            print("\n  No fue necesario renovar.")
        else:
            print("\n  Renovación exitosa.")
        sys.exit(0)
    else:
        print(f"\n  ERROR: {resultado['error']}")
        sys.exit(1)
