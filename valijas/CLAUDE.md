# CLAUDE.md — valijas/

## QUÉ HACE
Campaña de marketing y ventas del set de valijas GO (3 piezas: 17"+19"+21"). Dos canales: afiliados (agencias de viaje, comisión $20K/set) y venta mayorista directa. Incluye automatización WhatsApp, estrategia redes sociales, y material gráfico.

---

## ARCHIVOS CLAVE

### Estrategia y campañas
| Archivo | Función |
|---------|---------|
| `ESTRATEGIA_VALIJAS_GO.md` | Estrategia de negocio: unit economics, segmentos, pricing |
| `CAMPANA_WHATSAPP_AGENCIAS.md` | Roadmap campaña WA para 36 agencias. Secuencia follow-up día 1→2→4→7 |
| `CAMPANA_INSTAGRAM_FACEBOOK.md` | Calendario social: posts, stories, reels, Meta Ads |
| `GUION_VIDEO_VALIJAS.md` | Script video 30s vertical para Reels/Stories |

### Scripts de automatización
| Archivo | Función |
|---------|---------|
| `enviar_whatsapp.py` | Envío WA manual (wa.me links). Lee Excel, personaliza por tipo agencia, rate limit 45s |
| `enviar_whatsapp_agencias.py` | Envío WA via Meta Cloud API oficial. Template aprobado, normaliza teléfonos AR |
| `api_contactos_whatsapp.py` | API HTTP local (port 5050) para n8n. GET /contactos, POST /marcar_enviado |
| `n8n_workflow_whatsapp_valijas.json` | Workflow n8n: fetch contactos → enviar WA → marcar enviado → wait 45s → loop |

### Datos y assets
| Archivo | Función |
|---------|---------|
| `LISTA_AGENCIAS_WHATSAPP.xlsx` | Contactos agencias (nombre, ciudad, tipo, teléfono, estado) |
| `LISTA_AGENCIAS_PROSPECCION.xlsx` | 36 agencias con prioridad (8 ALTA, 18 MEDIA, 10 NORMAL) |
| `imagenes/` | Fotos producto: 4 colores (Negro, Rosa, Rojo, Rosa Gold) + interiores |
| `FLYER_*.html`, `VIDEO_*.html` | Material gráfico HTML (convertible a PNG) |
| `log_envios_agencias.json` | Log de envíos con message IDs y timestamps |

---

## PRICING

- **Retail**: $199,999 (6 cuotas sin interés)
- **Transferencia**: $159,999 (20% off)
- **Costo**: ~$45,000/set
- **Margen**: $58K–$117K según canal/pago

---

## CÓMO SE USA

```bash
# API local para n8n
python valijas/api_contactos_whatsapp.py  # → http://localhost:5050

# Envío manual WA
python valijas/enviar_whatsapp.py

# Envío via Meta Cloud API
python valijas/enviar_whatsapp_agencias.py test     # test a un número
python valijas/enviar_whatsapp_agencias.py alta      # solo prioridad alta
python valijas/enviar_whatsapp_agencias.py todas     # todas las agencias
```

---

## CONEXIÓN CON PROYECTO PRINCIPAL

**Loosely coupled.** No usa SQL Server ni ERP. Comparte marca Calzalindo, WhatsApp (3462-676300), y posiblemente tienda TiendaNube. Es una línea de producto separada (valijas vs calzado).

## QUÉ NO TOCAR

- `log_envios_agencias.json` — historial de envíos, no borrar
- `LISTA_AGENCIAS_*.xlsx` — datos de contacto con estado de seguimiento
- Rate limits en scripts WA (45s entre mensajes, max 15/sesión) — evita ban

## DEPENDENCIAS

openpyxl, pandas, requests, http.server (stdlib)
Servicios externos: Meta WhatsApp Cloud API, TiendaNube, n8n
