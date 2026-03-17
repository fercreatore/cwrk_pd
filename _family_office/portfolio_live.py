"""
Portfolio unificado — combina IOL + Cocos + (futuro IBKR)
Reemplaza mock_data.py cuando las credenciales están configuradas.
"""
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from broker_iol import IOLClient, normalize_positions as normalize_iol
from broker_cocos import CocosClient, normalize_positions as normalize_cocos, PYCOCOS_AVAILABLE


def get_all_positions():
    """
    Conecta a todos los brokers configurados y retorna posiciones unificadas.
    Si un broker falla, loguea el error y sigue con los demás.
    """
    all_positions = []
    errors = []

    # --- IOL ---
    if os.getenv("IOL_USER") and os.getenv("IOL_PASSWORD"):
        try:
            iol = IOLClient()
            raw = iol.get_portfolio()
            positions = normalize_iol(raw)
            all_positions.extend(positions)
        except Exception as e:
            errors.append(f"IOL: {e}")
    else:
        errors.append("IOL: credenciales no configuradas (IOL_USER/IOL_PASSWORD en .env)")

    # --- COCOS ---
    if PYCOCOS_AVAILABLE and os.getenv("COCOS_EMAIL") and os.getenv("COCOS_PASSWORD"):
        try:
            cocos = CocosClient()
            raw = cocos.get_portfolio()
            positions = normalize_cocos(raw)
            all_positions.extend(positions)
        except Exception as e:
            errors.append(f"COCOS: {e}")
    elif not PYCOCOS_AVAILABLE:
        errors.append("COCOS: pycocos no instalado (pip install pycocos)")
    else:
        errors.append("COCOS: credenciales no configuradas (COCOS_EMAIL/COCOS_PASSWORD/COCOS_TOTP_SECRET en .env)")

    return all_positions, errors


def get_all_balances():
    """Retorna saldos de todos los brokers."""
    balances = []
    errors = []

    if os.getenv("IOL_USER") and os.getenv("IOL_PASSWORD"):
        try:
            iol = IOLClient()
            state = iol.get_account_state()
            balances.append({"source": "IOL", "data": state})
        except Exception as e:
            errors.append(f"IOL balances: {e}")

    if PYCOCOS_AVAILABLE and os.getenv("COCOS_EMAIL"):
        try:
            cocos = CocosClient()
            funds = cocos.get_funds()
            balances.append({"source": "COCOS", "data": funds})
        except Exception as e:
            errors.append(f"COCOS balances: {e}")

    return balances, errors


def get_dolar_mep():
    """Obtiene cotización MEP desde Cocos (tiene endpoint dedicado)."""
    if PYCOCOS_AVAILABLE and os.getenv("COCOS_EMAIL"):
        try:
            cocos = CocosClient()
            return cocos.get_dolar_mep()
        except Exception:
            pass
    return None


if __name__ == "__main__":
    # Test rápido
    positions, errors = get_all_positions()
    print(f"Posiciones: {len(positions)}")
    for p in positions:
        print(f"  {p['source']} | {p['ticker']} | {p['qty']} @ ${p['current_price']}")
    if errors:
        print(f"\nErrores: {errors}")
