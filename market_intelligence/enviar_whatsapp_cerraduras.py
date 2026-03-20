"""
Script para enviar WhatsApp masivo — Cerraduras Inteligentes GO.

Envía via Chatwoot (chat.calzalindo.com.ar) usando WhatsApp Cloud API (Meta).
Usa template aprobado 'promo_mejores_clientes' para contactos nuevos (sin ventana 24hs).

Targets:
  - Cerrajeros y ferreterías
  - Administradores de edificios / consorcios
  - Inmobiliarias (Airbnb / alquiler temporario)
  - Constructoras / arquitectos

Uso:
    python3 market_intelligence/enviar_whatsapp_cerraduras.py              # Ver contactos
    python3 market_intelligence/enviar_whatsapp_cerraduras.py --demo       # Ver todos los mensajes
    python3 market_intelligence/enviar_whatsapp_cerraduras.py --test       # Enviar 5 tipos a Fernando
    python3 market_intelligence/enviar_whatsapp_cerraduras.py --enviar     # Enviar a contactos reales
    python3 market_intelligence/enviar_whatsapp_cerraduras.py --tipo cerrajero
"""

import re
import os
import sys
import ssl
import time
import json
import urllib.request
import urllib.error
from datetime import datetime

# Fix SSL certs en macOS (Python no usa el keychain del sistema)
try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()
    SSL_CTX.check_hostname = False
    SSL_CTX.verify_mode = ssl.CERT_NONE

# Rutas
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONTACTOS_JSON = os.path.join(SCRIPT_DIR, "data", "contactos_cerraduras.json")

# Números
WHATSAPP_PROPIO = "5493462507436"  # Calzalindo WhatsApp Business
WHATSAPP_FERNANDO = "5493462672330"

# Chatwoot config
CHATWOOT_URL = "https://chat.calzalindo.com.ar"
CHATWOOT_TOKEN = "zvQpseDYDoeqJpwM41GCb1LP"
CHATWOOT_ACCOUNT = 3
CHATWOOT_INBOX_ID = 9  # CALZLINDO 7436 (WhatsApp Cloud)

# Meta WhatsApp Cloud API
META_PHONE_NUMBER_ID = "1046697335188691"
META_ACCESS_TOKEN = "EAAT9fQyZAdWYBQ4qolDqcaRYaTT8tZAZBAMxHm2bwfhZAFLCDqkKEWNCXgQjlLGdUGJae0T1LY5rvVKh40uQLqQEgPXta1ssn1fWosn0BRynxrgf4k8BBwLH3D1Pk3klIlGbsILmPquDWCKUeCIkS6ra3rlhhEred73rbDb2TwrMm5z9x9U3hfUPxFG3KVPRdgZDZD"

# Template aprobado: promo_mejores_clientes (es_AR, MARKETING)
# Header: "www.calzalindo.com.ar"
# Body: "Hola {{1}}. Tenemos una promoción especial pensada para vos. {{2}}
#        Si te interesa, podés responder a este numero {{3}} y una asesora te va a asistir."
TEMPLATE_NAME = "promo_mejores_clientes"
TEMPLATE_LANG = "es_AR"
NUMERO_RESPUESTA = "3462507436"

# Rate limiting
DELAY_ENTRE_MENSAJES = 45
MAX_POR_SESION = 15

# Precios
PRECIO_LISTA = 249999
PRECIO_MAYORISTA_5 = 189999    # 5+ unidades
PRECIO_MAYORISTA_10 = 169999   # 10+ unidades


def normalizar_telefono(telefono):
    """Normalizar número a formato internacional sin +."""
    if not telefono:
        return None
    limpio = re.sub(r'[^\d]', '', str(telefono))
    if limpio.startswith("0"):
        limpio = "54" + limpio[1:]
    if limpio.startswith("08"):
        return None
    if len(limpio) < 10:
        return None
    return limpio


def get_promo_text(tipo="general"):
    """Texto promocional por tipo (va en parámetro {{2}} del template)."""

    if tipo == "cerrajero":
        return (
            "CERRADURA INTELIGENTE GO — Biométrica con huella por ambos lados, "
            "teclado táctil, NFC, App WiFi, IP65 exterior. "
            "El 51% de los robos en AR son en domicilios (Verisure 2025), "
            "la demanda de smart locks está explotando. "
            "Precio cerrajerías: 5+ a $189.999 c/u, 10+ a $169.999 c/u. "
            "Margen de $60.000 a $80.000 por unidad. Envío gratis, Factura A."
        )

    elif tipo == "inmobiliaria":
        return (
            "CERRADURA INTELIGENTE GO para Airbnb/temporario. "
            "Rosario tiene +1.800 propiedades temporarias, creciendo 24% anual. "
            "68% de hosts ya usa smart lock, +0.2 estrellas en rating. "
            "Creás códigos temporales, el huésped entra solo, sin coordinar llaves. "
            "Se paga sola en 60 días (un lockout = $150.000+ en cerrajero). "
            "$249.999, 3+ unidades a $209.999. Envío gratis."
        )

    elif tipo == "consorcio":
        return (
            "CERRADURA GO — Acceso biométrico para edificios. "
            "Hasta 100 huellas, código + NFC + App WiFi, historial de accesos, IP65 exterior. "
            "El 51% de los robos en AR son en domicilios. "
            "Chau llaves perdidas y copias no autorizadas. "
            "$249.999, 3+ a $209.999, 5+ a $189.999. Factura A, envío gratis."
        )

    elif tipo == "constructora":
        return (
            "CERRADURA GO — Smart Lock biométrica ideal para obra nueva. "
            "5 métodos de acceso (huella, código, NFC, app, llave), "
            "WiFi + Bluetooth, IP65, acero inoxidable. "
            "Agrega valor real a cualquier propiedad. Se instala en 30 min. "
            "5+ unidades: $189.999 c/u, 10+: $169.999 c/u. Envío gratis."
        )

    else:  # general
        return (
            "CERRADURA INTELIGENTE GO — Tu puerta se abre con tu dedo. "
            "Huella dactilar por ambos lados, teclado + NFC + App WiFi, "
            "acero inoxidable, IP65 lluvia, timbre integrado. "
            "$249.999 con envío gratis. Factura A y B."
        )


def get_mensaje_completo(nombre, tipo="general"):
    """Mensaje completo (para --demo en consola)."""

    if tipo == "cerrajero":
        return f"""Hola! Buenas tardes 👋

Soy Fernando de Calzalindo/GO. Te escribo porque tenemos una cerradura inteligente importada que puede ser un producto estrella para tu negocio.

El 51% de los robos en Argentina son en domicilios (Observatorio Verisure 2025). La demanda de cerraduras inteligentes está explotando.

CERRADURA GO — Biométrica con Huella Digital
✦ Huella por DENTRO y por FUERA
✦ Teclado numérico táctil
✦ Tarjeta NFC
✦ App Tuya Smart (WiFi)
✦ Acero inoxidable, IP65 (exterior)
✦ Timbre integrado con notificación al celular

La vendemos en MercadoLibre a $249.999.

Para cerrajerías tenemos precio especial:
• 5+ unidades: $189.999 c/u
• 10+ unidades: $169.999 c/u

Margen de $60.000 a $80.000 por unidad instalada.
Envío gratis. Factura A y B.

Te mando un video de cómo funciona?"""

    elif tipo == "inmobiliaria":
        return f"""Hola! Buenas tardes 👋

Soy Fernando de GO. Te escribo porque tenemos algo ideal para propiedades en alquiler temporario y Airbnb.

Algunos datos que me parecen clave:
📊 Rosario tiene +1.800 propiedades temporarias, creciendo 24% anual
📊 El 68% de los hosts de Airbnb ya usa smart lock
📊 Los huéspedes dan +0.2 estrellas en rating a deptos con acceso sin llave
📊 Un lockout de huésped = $150.000+ en cerrajero de urgencia

CERRADURA INTELIGENTE GO — Se abre con el dedo
✦ Creás CÓDIGOS TEMPORALES desde el celular
✦ El huésped entra solo, sin coordinar llaves
✦ Cuando termina, el código se desactiva
✦ Historial: sabés quién entró y a qué hora
✦ Resistente a lluvia (IP65)

Ya no más:
❌ Coordinar entrega de llaves
❌ Hacer copias
❌ Preocuparte si devolvieron la llave

Se paga sola en 60 días con lo que ahorrás en cerrajero y tiempo.

Precio: $249.999 c/u
Para 3+ unidades: $209.999 c/u

Te mando un video? Se instala en 30 minutos."""

    elif tipo == "consorcio":
        return f"""Hola! Buenas tardes 👋

Soy Fernando de GO. Te escribo porque tenemos una solución de acceso inteligente para edificios y consorcios.

El 51% de los robos en Argentina son en domicilios. El control de acceso es la primera línea de defensa.

CERRADURA GO — Acceso Biométrico Profesional
✦ Hasta 100 huellas registradas (ideal para muchos usuarios)
✦ Código numérico + tarjeta NFC + App WiFi
✦ Historial completo de accesos (sabés quién entró y cuándo)
✦ IP65 — funciona en exterior (portón, puerta de calle)
✦ Timbre con notificación al celular
✦ Acero inoxidable, antivandalismo

Chau llaves perdidas, copias no autorizadas y reclamos de propietarios.

Para edificios y consorcios:
• Precio unitario: $249.999
• 3+ unidades: $209.999
• 5+ unidades: $189.999

Factura A. Garantía 6 meses. Envío gratis.

Te interesa ver cómo funciona? Te mando un video."""

    elif tipo == "constructora":
        return f"""Hola! Buenas tardes 👋

Soy Fernando de GO. Tenemos cerraduras inteligentes importadas ideales para obra nueva y remodelaciones.

CERRADURA GO — Smart Lock Biométrica
✦ Huella digital por ambos lados
✦ 5 métodos de acceso (huella, código, NFC, app, llave)
✦ WiFi + Bluetooth — control desde la app Tuya
✦ IP65 para exterior
✦ Acero inoxidable

Para constructoras y arquitectos:
• 5+ unidades: $189.999 c/u
• 10+ unidades: $169.999 c/u

Es un upgrade real que le agrega valor a cualquier propiedad.
Se instala en puerta estándar de 35-55mm.

Les mando la ficha técnica?"""

    else:  # general
        return f"""Hola! Buenas tardes 👋

Soy Fernando de GO. Tenemos cerraduras inteligentes importadas con acceso biométrico.

CERRADURA GO — Tu puerta se abre con tu dedo
✦ Huella dactilar por dentro y por fuera
✦ Teclado numérico + tarjeta NFC
✦ Control WiFi desde el celular (App Tuya)
✦ Acero inoxidable, resistente a lluvia (IP65)
✦ Timbre integrado

Precio: $249.999
Envío gratis a todo el país.
Factura A y B.

Te mando fotos y un video de cómo funciona?"""


def enviar_template_meta(telefono, nombre, tipo="general"):
    """Enviar template 'promo_mejores_clientes' via Meta WhatsApp Cloud API."""
    url = f"https://graph.facebook.com/v21.0/{META_PHONE_NUMBER_ID}/messages"

    promo = get_promo_text(tipo)

    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "template",
        "template": {
            "name": TEMPLATE_NAME,
            "language": {"code": TEMPLATE_LANG},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": nombre},
                        {"type": "text", "text": promo},
                        {"type": "text", "text": NUMERO_RESPUESTA},
                    ]
                }
            ]
        }
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {META_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            msg_id = result.get("messages", [{}])[0].get("id", "?")
            status = result.get("messages", [{}])[0].get("message_status", "?")
            return True, f"OK ({status}) id={msg_id[:30]}..."
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return False, f"HTTP {e.code}: {body[:200]}"
    except Exception as e:
        return False, str(e)


def registrar_en_chatwoot(telefono, nombre, tipo="general"):
    """Crear/buscar contacto en Chatwoot para tener registro de la conversación."""
    # Buscar contacto existente
    url = f"{CHATWOOT_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT}/contacts/search?q={telefono}"
    req = urllib.request.Request(url, headers={"api_access_token": CHATWOOT_TOKEN})

    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("meta", {}).get("count", 0) > 0:
                contact_id = data["payload"][0]["id"]
                return contact_id

        # Crear contacto nuevo
        url = f"{CHATWOOT_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT}/contacts"
        payload = {
            "name": nombre,
            "phone_number": f"+{telefono}",
            "inbox_id": CHATWOOT_INBOX_ID,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "api_access_token": CHATWOOT_TOKEN,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, context=SSL_CTX) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("payload", {}).get("contact", {}).get("id")
    except Exception as e:
        print(f"    (Chatwoot registro: {e})")
        return None


def cargar_contactos(filtro_tipo=None, solo_pendientes=True):
    """Cargar contactos del JSON."""
    if not os.path.exists(CONTACTOS_JSON):
        print(f"No existe {CONTACTOS_JSON}")
        print("Creando archivo de ejemplo...")
        crear_contactos_ejemplo()

    with open(CONTACTOS_JSON, "r", encoding="utf-8") as f:
        contactos = json.load(f)

    result = []
    for c in contactos:
        if solo_pendientes and c.get("estado") not in ("pendiente", None, ""):
            continue
        if filtro_tipo and c.get("tipo", "").lower() != filtro_tipo.lower():
            continue
        result.append(c)

    return result


def crear_contactos_ejemplo():
    """Crear archivo JSON de ejemplo con contactos."""
    ejemplo = [
        {
            "nombre": "Cerrajería Ejemplo",
            "telefono": "5493462000000",
            "tipo": "cerrajero",
            "ciudad": "Venado Tuerto",
            "estado": "pendiente",
            "notas": ""
        },
    ]

    os.makedirs(os.path.dirname(CONTACTOS_JSON), exist_ok=True)
    with open(CONTACTOS_JSON, "w", encoding="utf-8") as f:
        json.dump(ejemplo, f, ensure_ascii=False, indent=2)

    print(f"Archivo creado: {CONTACTOS_JSON}")
    print("Editalo con tus contactos reales antes de enviar.")


def marcar_enviado(contactos, index):
    """Marcar contacto como enviado."""
    with open(CONTACTOS_JSON, "r", encoding="utf-8") as f:
        todos = json.load(f)

    nombre = contactos[index]["nombre"]
    for c in todos:
        if c["nombre"] == nombre:
            c["estado"] = "enviado"
            c["fecha_envio"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            break

    with open(CONTACTOS_JSON, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)


def mostrar_contactos(contactos):
    """Mostrar tabla de contactos."""
    con_wa = [c for c in contactos if normalizar_telefono(c.get("telefono"))]

    print(f"\n{'='*80}")
    print(f"CERRADURAS GO — {len(contactos)} contactos, {len(con_wa)} con WhatsApp")
    print(f"{'='*80}")

    print(f"\n{'#':>3}  {'Nombre':<30} {'Ciudad':<15} {'Tipo':<15} {'Estado'}")
    print("-" * 80)

    for i, c in enumerate(contactos, 1):
        print(f"{i:>3}  {c['nombre']:<30} {c.get('ciudad',''):<15} {c.get('tipo',''):<15} {c.get('estado','pendiente')}")


def ejecutar_envio(contactos):
    """Enviar templates via Meta WhatsApp Cloud API."""
    con_wa = [c for c in contactos if normalizar_telefono(c.get("telefono"))]

    if not con_wa:
        print("\nNo hay contactos con WhatsApp para enviar.")
        return

    print(f"\n{'='*80}")
    print(f"ENVÍO WHATSAPP CERRADURAS GO — {len(con_wa)} contactos")
    print(f"Via: Meta WhatsApp Cloud API → chat.calzalindo.com.ar")
    print(f"Template: {TEMPLATE_NAME}")
    print(f"Delay: {DELAY_ENTRE_MENSAJES}s | Max: {MAX_POR_SESION}/sesión")
    print(f"{'='*80}")

    enviados = 0
    fallidos = 0

    for i, c in enumerate(con_wa):
        if enviados >= MAX_POR_SESION:
            print(f"\n  Límite alcanzado ({MAX_POR_SESION}). Esperá 1 hora.")
            break

        tel = normalizar_telefono(c["telefono"])
        tipo = c.get("tipo", "general")

        print(f"\n[{i+1}/{len(con_wa)}] {c['nombre']} ({tipo}) → {tel}")

        # Registrar en Chatwoot
        registrar_en_chatwoot(tel, c["nombre"], tipo)

        # Enviar template
        ok, msg = enviar_template_meta(tel, c["nombre"], tipo)

        if ok:
            print(f"  ✅ {msg}")
            marcar_enviado(con_wa, i)
            enviados += 1
        else:
            print(f"  ❌ {msg}")
            fallidos += 1

        if i < len(con_wa) - 1 and enviados < MAX_POR_SESION:
            print(f"  Esperando {DELAY_ENTRE_MENSAJES}s...")
            time.sleep(DELAY_ENTRE_MENSAJES)

    print(f"\n{'='*80}")
    print(f"ENVIADOS: {enviados} | FALLIDOS: {fallidos}")
    print(f"Las conversaciones quedan en chat.calzalindo.com.ar")
    print(f"{'='*80}")


def ejecutar_test():
    """Enviar los 5 tipos de template al WhatsApp de Fernando para revisión."""
    tipos = ["cerrajero", "inmobiliaria", "consorcio", "constructora", "general"]
    tel = WHATSAPP_FERNANDO
    delay = 10

    print(f"\n{'='*80}")
    print(f"MODO TEST — Enviando 5 templates a Fernando ({tel})")
    print(f"Via: Meta WhatsApp Cloud API")
    print(f"Template: {TEMPLATE_NAME}")
    print(f"Delay: {delay}s entre mensajes")
    print(f"{'='*80}")

    enviados = 0
    for i, tipo in enumerate(tipos):
        print(f"\n[{i+1}/5] Tipo: {tipo.upper()}")

        promo = get_promo_text(tipo)
        print(f"  Promo: {promo[:80]}...")

        ok, msg = enviar_template_meta(tel, f"Fernando (TEST {tipo.upper()})", tipo)

        if ok:
            print(f"  ✅ {msg}")
            enviados += 1
        else:
            print(f"  ❌ {msg}")

        if i < len(tipos) - 1:
            print(f"  Esperando {delay}s...")
            time.sleep(delay)

    print(f"\n{'='*80}")
    print(f"LISTO — {enviados}/5 enviados. Revisá tu celular.")
    print(f"Si están OK, corré con --enviar para mandar a contactos reales.")
    print(f"{'='*80}")


def demo_mensajes():
    """Mostrar todos los tipos de mensaje para revisar."""
    tipos = ["cerrajero", "inmobiliaria", "consorcio", "constructora", "general"]

    print(f"\n{'='*60}")
    print("TEMPLATE QUE SE ENVÍA (promo_mejores_clientes)")
    print(f"{'='*60}")
    print('Header: "www.calzalindo.com.ar"')
    print('Body: "Hola {{nombre}}. Tenemos una promoción especial')
    print('       pensada para vos. {{PROMO}} Si te interesa, podés')
    print(f'       responder a este numero {NUMERO_RESPUESTA}"')

    for tipo in tipos:
        print(f"\n{'-'*60}")
        print(f"PROMO TIPO: {tipo.upper()}")
        print(f"{'-'*60}")
        promo = get_promo_text(tipo)
        print(promo)
        print(f"  [{len(promo)} chars]")

    print(f"\n{'='*60}")
    print("MENSAJES COMPLETOS (para referencia / follow-up)")
    print(f"{'='*60}")

    for tipo in tipos:
        print(f"\n{'='*60}")
        print(f"MENSAJE TIPO: {tipo.upper()}")
        print(f"{'='*60}")
        msg = get_mensaje_completo("NOMBRE_EJEMPLO", tipo)
        print(msg)

    print(f"\n{'='*60}")
    print("PRECIOS:")
    print(f"  Lista:        ${PRECIO_LISTA:,}")
    print(f"  Mayor 5+:     ${PRECIO_MAYORISTA_5:,}")
    print(f"  Mayor 10+:    ${PRECIO_MAYORISTA_10:,}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="WhatsApp masivo — Cerraduras GO (via Chatwoot/Meta API)")
    parser.add_argument("--enviar", action="store_true", help="Enviar templates a contactos reales")
    parser.add_argument("--tipo", type=str, help="Filtrar: cerrajero, inmobiliaria, consorcio, constructora")
    parser.add_argument("--todos", action="store_true", help="Incluir ya enviados")
    parser.add_argument("--demo", action="store_true", help="Ver todos los mensajes")
    parser.add_argument("--test", action="store_true", help="Enviar 5 tipos al WhatsApp de Fernando para revisar")
    args = parser.parse_args()

    if args.demo:
        demo_mensajes()
        return

    if args.test:
        ejecutar_test()
        return

    contactos = cargar_contactos(
        filtro_tipo=args.tipo,
        solo_pendientes=not args.todos,
    )

    if args.enviar:
        ejecutar_envio(contactos)
    else:
        mostrar_contactos(contactos)
        print(f"\nPara ver mensajes: python3 market_intelligence/enviar_whatsapp_cerraduras.py --demo")
        print(f"Para testear:      python3 market_intelligence/enviar_whatsapp_cerraduras.py --test")
        print(f"Para enviar:       python3 market_intelligence/enviar_whatsapp_cerraduras.py --enviar")
        print(f"Filtrar:           python3 market_intelligence/enviar_whatsapp_cerraduras.py --tipo cerrajero")


if __name__ == "__main__":
    main()
