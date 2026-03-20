# FIX CFO GAPS — 20 marzo 2026

## Problema raíz

El calce financiero (`calce_financiero.py`) calculaba tiempos de recupero de inversión usando **velocidad aparente** (ventas brutas / meses totales). Esto subestima la demanda real cuando hay quiebre de stock.

Ejemplo CARMEL CANELA T42:
- vel_aparente: 2 pares/mes (incluye 34 meses con stock=0)
- vel_real: 10.8 pares/mes (solo meses con stock)
- Factor: 5.4x
- **Impacto**: el presupuesto dice que se necesitan $100K cuando la demanda real es $540K

## Solución: 3 fases

### FASE 1: Tabla compartida vel_real_articulo

**Archivo**: `_scripts_oneshot/crear_tabla_vel_real.py`
**Commit**: `feat: script para generar tabla vel_real_articulo`

- Conecta a réplica 112 (solo SELECT)
- Para cada artículo activo con ventas últimos 12 meses:
  - Reconstruye stock mes a mes hacia atrás (mismo algoritmo que `analizar_quiebre_batch()`)
  - Cuenta meses quebrados vs OK
  - Calcula vel_aparente, vel_real, factor_quiebre
- Genera script SQL para `omicronvt.dbo.vel_real_articulo`
- **NO ejecuta el INSERT**, solo genera el .sql

**Ejecución**:
```bash
cd ~/Desktop/cowork_pedidos
python _scripts_oneshot/crear_tabla_vel_real.py
# Genera: _scripts_oneshot/vel_real_articulo_YYYYMMDD.sql
# Copiar al 111 y ejecutar con sqlcmd
```

**Tabla generada**:
| Columna | Tipo | Descripción |
|---------|------|-------------|
| codigo | VARCHAR(20) PK | codigo_sinonimo del artículo |
| vel_aparente | DECIMAL(10,2) | ventas_total / 12 meses |
| vel_real | DECIMAL(10,2) | ventas_ok / meses_ok |
| meses_con_stock | INT | meses sin quiebre |
| meses_quebrado | INT | meses con stock_inicio <= 0 |
| factor_quiebre | DECIMAL(8,3) | vel_real / vel_aparente |
| fecha_calculo | DATE | cuándo se calculó |

### FASE 2: Fix presupuesto

**Archivo**: `_informes/calzalindo_informes_DEPLOY/sql/crear_presupuesto_industria.sql`
**Commit**: `feat: presupuesto ajustado por quiebre`

Columnas nuevas en `t_presupuesto_industria`:
| Columna | Descripción |
|---------|-------------|
| vel_aparente_industria | Promedio vel_aparente de la industria |
| vel_real_industria | Promedio vel_real de la industria |
| factor_quiebre_industria | vel_real / vel_aparente (promedio industria) |
| presupuesto_ajustado | presupuesto_costo * factor_quiebre |
| disponible_ajustado | presupuesto_ajustado - comprometido |
| pct_ejecutado_ajustado | comprometido / presupuesto_ajustado * 100 |

**Cuándo usar cada uno**:
- `presupuesto_costo` → planificación financiera conservadora
- `presupuesto_ajustado` → planificación de compras, objetivo de venta real
- `pct_ejecutado` → ejecución vs ventas del año pasado
- `pct_ejecutado_ajustado` → ejecución vs demanda real estimada

**Backwards compatible**: si `vel_real_articulo` no existe, `factor_quiebre = 1.0` (sin ajuste).

### FASE 3: Fix calce financiero

**Archivo**: `_informes/calzalindo_informes_DEPLOY/controllers/calce_financiero.py`
**Commit**: `feat: t_recupero_real con vel_real en calce financiero`

Campos nuevos en la matriz integrada del dashboard:
| Campo | Descripción |
|-------|-------------|
| dias_50_real | Días para recuperar 50% corregido por quiebre |
| dias_75_real | Días para recuperar 75% corregido por quiebre |
| pct_vendido_al_pago_real | % vendido al momento del pago (corregido) |
| factor_quiebre | Factor promedio de la industria |
| alerta_quiebre | Texto de alerta si diferencia > 50% |

**Lógica**:
- `dias_50_real = dias_50_aparente / factor_quiebre`
- Si factor=2x → recuperás en la mitad de tiempo (porque vendés el doble cuando hay stock)
- Alerta automática cuando la diferencia aparente vs real supera 50%

**Backwards compatible**: si `vel_real_articulo` no existe, el bloque falla silenciosamente y usa valores aparentes.

## Orden de ejecución

1. Ejecutar `crear_tabla_vel_real.py` en Mac (genera .sql)
2. Copiar .sql al 111 y ejecutar (`sqlcmd` o SSMS)
3. Ejecutar `crear_presupuesto_industria.sql` en 111 (recrea tabla con columnas nuevas)
4. Deploy `calce_financiero.py` al 111 (web2py controller)
5. Ejecutar `EXEC sp_calcular_presupuesto` para recalcular con datos de vel_real

## Dependencias

```
vel_real_articulo (FASE 1)
    ↓
t_presupuesto_industria (FASE 2) ← JOIN vel_real_articulo por industria
    ↓
calce_financiero.py (FASE 3) ← JOIN vel_real_articulo por industria
```

Ambos (FASE 2 y 3) dependen de FASE 1. Si FASE 1 no se ejecutó, ambos degradan gracefully a factor=1.0.
