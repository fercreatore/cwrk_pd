
---
## SESIÓN 25-26 MAR — RESUMEN COMPLETO

### Pedido Timmis Folclore insertado
- #1134086 (Ent1 Abr): 143p, $3.47M — CONTADO
- #1134087 (Ent2 May): 132p, $3.20M
- #1134088 (Ent3 Jun): 133p, $3.23M
- TOTAL: 408 pares, $9.89M

### Funciones nuevas en app_reposicion.py
- calcular_curva_ideal() — curva por talle con CTEs
- calcular_pedido_modelo() — vista zapatero (modelos×talles)
- calcular_safety_stock() — Poisson + nivel servicio
- clasificar_abc_xyz() — revenue + regularidad
- presupuesto auto desde ventas + quiebre
- WhatsApp botón proveedor
- Performance: session_state + progress bars + TTL 2h
- Horizonte configurable 30-365 días
- proyectar_entregas_mensuales()
- Lost sales en quiebre
- Multi-proveedor unification

### vel_real_articulo en producción
- 31,600 registros en omicronvt.dbo.vel_real_articulo
- 51% artículos con >50% quiebre
- 17,912 con vel_real > 2x vel_aparente

### Backtesting
- 36 reportes completos en _informes/backtesting/
- Modelo subestima verano (-41% a -80%)
- Sobrecompra perennes (+90% a +200%)
- Acierta bien invierno clásico (+2.7%)

### Pedidos Invierno 2026 parseados
- 10 proveedores, ~10,500 pares total
- Catálogos vacíos: FOOTY, Athix, HEAD, ADDNICE, Nike/Adidas

### Próximos pasos
- Variables exógenas (tasa, M2, M3, inflación)
- Más backtesting para calibrar
- Imputar pedidos restantes (Atomik, Floyd, etc)
- Sincronizar las 4 copias de vel_real
