# Auditoría de Fórmulas — app_reposicion.py
> Fecha: 2026-03-20

---

## 1. MESES DE STOCK / COBERTURA SIMPLE

**Ubicación**: Líneas 837-842 (`cargar_mapa_surtido`) y 2150-2156 (Dashboard)

```python
df['vel_diaria'] = df['ventas_12m'] / 365
df['cobertura_dias'] = stock_total / vel_diaria
```

**Fórmula**: `cobertura = stock / (ventas_12m / 365)`

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Excluye código 7,36 | ✅ OK | Via EXCL_VENTAS constante |
| Excluye marcas gastos | ✅ OK | Via EXCL_MARCAS_GASTOS |
| Corrige por quiebre | ❌ NO | Usa velocidad aparente, no real |
| Neto ventas-devol | ✅ OK | operacion '+' suma, '-' resta |

**Impacto**: Sobreestima cobertura en artículos con quiebre alto.
Ejemplo: artículo con 87% quiebre → vel_aparente ≈ 2/mes, vel_real ≈ 10.8/mes → cobertura real es 5x menor.

**Veredicto**: ⚠️ MÁS O MENOS — correcto como primera vista rápida del mapa, pero NO debería usarse para decisiones de compra.

**Fix propuesto**: En Mapa Surtido, si el quiebre > 30%, mostrar cobertura con vel_real en vez de vel_aparente. Alternativa: indicar "⚠️ quiebre X%" al lado.

---

## 2. VELOCIDAD DE VENTA (analizar_quiebre_batch)

**Ubicación**: Líneas 138-259

```python
vel_ap = ventas_total / max(meses, 1)
vel_real = ventas_ok / max(meses_ok, 1) if meses_ok > 0 else vel_ap
```

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Ventas netas (+-) | ✅ OK | SUM(CASE '+' THEN cant, '-' THEN -cant) |
| Excluye código 7,36 | ✅ OK | WHERE v.codigo NOT IN (7,36) |
| Divide por meses con stock | ✅ OK | ventas_ok / meses_ok |
| Reconstruye stock hacia atrás | ✅ OK | stock_inicio = stock_fin + v - c |
| Usa compras operacion='+' | ✅ OK | Solo ingresos reales |

**Veredicto**: ✅ CORRECTO — Implementación gold-standard de velocidad real con corrección de quiebre.

---

## 3. COBERTURA EN DÍAS (Advanced)

**Ubicación**: Líneas 578-593 (`calcular_dias_cobertura`)

```python
for d in range(1, max_dias + 1):
    factor = factores_est.get(fecha.month, 1.0)
    stock_restante -= vel_diaria * factor
    if stock_restante <= 0:
        return d
```

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Usa vel_real (quiebre) | ✅ OK | Input ya viene de analizar_quiebre_batch |
| Estacionalidad mensual | ✅ OK | Factores de 3 años de historia |
| Día a día iterativo | ✅ OK | Más preciso que dividir |

**Veredicto**: ✅ CORRECTO — Usado en Waterfall y ROI. La cadena es: quiebre → vel_real → /30 → estacionalidad → proyección.

---

## 4. GMROI

**Ubicación**: NO IMPLEMENTADO

Lo que existe es **ROI de inversión** (líneas 596-656):
```python
inversion = precio_costo × cantidad_pedir
dias_recupero = día en que margen_acumulado >= inversion
roi_60d = (ingresos_60d - inversion) / inversion × 100
```

**Veredicto**: ❌ GMROI no existe como tal. El ROI implementado es una métrica distinta pero útil (cuántos días tarda en recuperar la inversión de una compra específica). Para agregar GMROI real: `margen_bruto_anual / stock_promedio_a_costo`.

---

## 5. ÍNDICE DE ROTACIÓN

**Ubicación**: NO CALCULADO EXPLÍCITAMENTE

Solo existe velocidad mensual:
```python
vel_mes = ventas_12m / 12
vel_dia = vel_mes / 30
```

**Veredicto**: ❌ No se calcula. Para agregar: `rotacion = costo_ventas_12m / stock_promedio_costo`. Requiere campo `costo_v` de ventas1 y stock promedio.

---

## 6. CURVA DE TALLES IDEAL

**Ubicación**: Líneas 1365-1406 (`calcular_curva_talle_ideal`)

```python
pct_demanda = vtas_per_talle / total_vtas_per_categoria × 100
```

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Ventas netas | ✅ OK | operacion +/- correcta |
| Excluye 7,36 | ✅ OK | EXCL_VENTAS |
| 3 años historia | ✅ OK | Buen volumen estadístico |
| Corrige quiebre por talle | ❌ NO | Un talle siempre quebrado aparece como "baja demanda" |

**Impacto**: Si T42 de una categoría estuvo sin stock 80% del tiempo, la curva ideal la subestima.
La demanda real de ese talle es mayor que lo que muestran las ventas históricas.

**Veredicto**: ⚠️ MÁS O MENOS — buena para categorías con buen stock general, engañosa para categorías con quiebre concentrado en talles pico.

**Fix propuesto**: Para la curva ideal por subrubro (nueva función de omicron), ponderar por (1 + pct_quiebre_talle) para compensar demanda no atendida. O al menos mostrar un disclaimer.

---

## RESUMEN

| Fórmula | Estado | Quiebre? | Excl 7,36? |
|---------|--------|----------|------------|
| Meses Stock (simple) | ⚠️ | ❌ | ✅ |
| Velocidad Real | ✅ | ✅ | ✅ |
| Velocidad Aparente | ⚠️ | ❌ | ✅ |
| Cobertura Advanced | ✅ | ✅ | ✅ |
| GMROI | ❌ No existe | — | — |
| Rotación | ❌ No existe | — | — |
| Curva Talles | ⚠️ | ❌ por talle | ✅ |
| Waterfall | ✅ | ✅ (input) | ✅ |
| ROI | ✅ | ✅ (input) | ✅ |

### Lo que funciona bien:
1. `analizar_quiebre_batch` es sofisticado y correcto
2. Cadena Waterfall→ROI usa velocidad real + estacionalidad
3. Exclusiones (7,36 + marcas gastos) son consistentes

### Lo que necesita mejora:
1. Dashboard overview usa vel_aparente (OK para vista rápida, no para decisiones)
2. Curva de talles no corrige por quiebre a nivel talle
3. GMROI y Rotación no están implementados
4. Cobertura simple en Mapa Surtido puede engañar en categorías con quiebre alto
