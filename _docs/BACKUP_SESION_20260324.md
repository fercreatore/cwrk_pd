# Backup Sesión 24-mar-2026 — Reposición Inteligente v2

## RESUMEN DE LO APRENDIDO EN ESTA SESIÓN

### 1. Presupuesto basado en pares vendidos (no en dinero)
- El presupuesto de un proveedor = pares vendidos del mismo período año anterior
- Ejemplo: OLK (prov 722, Global Brands) vendió 475 pares mar-jun 2025 → presupuesto 475 pares
- Condición de pago 60/90/120/150 días afecta ROI efectivo

### 2. Distribución NO pareja
- Error v1: comprar 12 pares por línea parejo
- Corrección: distribuir según ventas reales por género y color
- OLK hombres: NEGRO 56%, AZUL 21%, GRIS 11%
- OLK damas: NEGRO 52%, BEIGE 13%, AZUL 6%

### 3. Precio techo por historial
- No comprar modelos caros que no se venden en el negocio
- Usar percentil 90 del precio de venta como techo
- GRAFENO 3 ($108k) → descartado

### 4. Talles individuales, NO por rango
- Stock por talle individual con cobertura en días
- 46/47/48 = siempre tratar como stock cero (escasez crónica)
- Curva de talles REAL (de ventas) vs curva del proveedor

### 5. Estacionalidad mensual
- Mar: 74%, Abr: 73% (valle) → Jun: 105%, Jul: 98% (destino)
- Factor ajuste: si compro en marzo para vender en junio = 1.42x

### 6. Ratio C/V = 75% (modelo nuevo)
- Se compra 25% menos de lo que se vende → drenaje de stock
- Cobertura global 593 días es ENGAÑOSA por quiebre a nivel SKU

### 7. Quiebre obligatorio
- Reconstruir stock mes a mes hacia atrás
- Meses con stock_inicio ≤ 0 = QUEBRADO → no contar en velocidad
- Velocidad aparente SUBESTIMA demanda real

## FUNCIONES NUEVAS AGREGADAS A app_reposicion.py

| Función | Qué hace |
|---------|----------|
| `presupuesto_pares()` | Presupuesto en pares basado en ventas mismo período año anterior + ajuste estacional |
| `distribucion_genero()` | Split de pares por género según ventas históricas |
| `distribucion_color()` | Split por color usando keywords ESP/ENG/POR |
| `precio_techo()` | P50/P75/P90/Max de precio fábrica por proveedor×género |
| `curva_talles_real()` | Curva de demanda por talle con corrección quiebre |
| `talles_escasez_cronica()` | Talles con >70% meses quebrados |
| `cargar_talles_categoria()` | Stock/ventas/cobertura por talle individual |
| `detectar_tendencias_emergentes()` | Productos acelerando (tiene bug clip) |

## TABS ACTUALES
1. 🗺️ Mapa Surtido (categoría × género con drill-down)
2. 📊 Dashboard (con alerta C/V 75%)
3. 🐋 Waterfall
4. 💰 Optimizar Compra (presupuesto pares + curva comparador)
5. 🐾 Curva Talle
6. 🐕 Canibalización
7. 🚀 Emergentes (CRASH - fix pending)
8. 🛒 Armar Pedido
9. 📁 Historial

## PROVEEDORES EN SISTEMA
- 668: ALPARGATAS (Topper) - viajante 98
- 722: GLOBAL BRANDS (Olympikus) - viajante 98
- 876: INTERNATIONAL BRANDS (OLK Agua) - viajante 98
- 104: EL GITANO (GTN) - CALZALINDO
- 594: VICBOR (multi-marca)
- 656: DISTRINANDO (Reebok)
- 561: Souter (Ringo/Carmel)
- 614: Calzados Blanco (Diadora)

## PROVEEDORES NUEVOS (catálogos recibidos hoy)
- John Foos
- Pira Gowell
- PSV Passoti
- (posiblemente más)

## BUGS PENDIENTES
- `detectar_tendencias_emergentes()` línea 2520: `.clip(lower=1)` → usar `max(..., 1)`
- Cuadros blancos en métricas (CSS fix aplicado pero verificar)

## BASE DE DATOS KEY FACTS
- OLK = proveedor 722 (GLOBAL BRANDS S.A.)
- Artículos OLK: 2,892 en msgestion01art
- Talle en `descripcion_5` de articulo
- Tablas talles: aliases_talles, equivalencias_talles_calzado, regla_talle_subrubro (en msgestion01)
- PostgreSQL embeddings: postgresql://guille:Martes13%23@200.58.109.125:5432/clz_productos
