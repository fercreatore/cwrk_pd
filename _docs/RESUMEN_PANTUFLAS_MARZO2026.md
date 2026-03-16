# Análisis Pantuflas — Resumen para Continuación
## Fecha: 14 marzo 2026

---

## 1. COMODITAS (Proveedor 98, Marca 776, Subrubro 60)

### Stock actual adulto T35-46: 325 pares (190 dama + 135 hombre)

### Estacionalidad mensual (ventas totales):
| Mes | 2023 | 2024 | 2025 |
|-----|------|------|------|
| Ene | — | 23 | 16 |
| Feb | — | 20 | 27 |
| Mar | 39 | 44 | 75 |
| Abr | 169 | 194 | 160 |
| May | 184 | 254 | 216 |
| Jun | 342 | 264 | 303 |
| Jul | 140 | 159 | 226 |
| Ago | 62 | 67 | 90 |
| Sep | 40 | 20 | 33 |
| Oct | 56 | 52 | 22 |
| Nov | 19 | 22 | 11 |
| Dic | 31 | 28 | 8 |

Factor pico invierno (may-jul): **2.7x** sobre promedio anual.

### Propuesta de reposición: 403 pares (cobertura 3 meses mid-May a mid-Aug)

**DAMA (T35-40): 235 pares**

| Talle | Stock | Quiebre% | Vel suavizada/mes | Pedido |
|-------|-------|----------|-------------------|--------|
| T35 | 5 | bajo | baja | 0 |
| T36 | 51 | 59% | moderada | 7 |
| T37 | 30 | 51% | media | 65 |
| T38 | 55 | 95% | 13.6 | 56 |
| T39 | 0 | 92% | 7.7 | 62 |
| T40 | 49 | 95% | 11.7 | 45 |

**HOMBRE (T41-46): 168 pares**

| Talle | Stock | Quiebre% | Vel suavizada/mes | Pedido |
|-------|-------|----------|-------------------|--------|
| T41 | 7 | 73% | 6.7 | 48 |
| T42 | 85 | 89% | 16.4 | 48 |
| T43 | 3 | 70% | 5.2 | 39 |
| T44 | 40 | 92% | 6.9 | 16 |
| T45 | 0 | 100% | 2.1 | 17 |
| T46 | 0 | — | — | 0 |

### Metodología velocidad suavizada
- Quiebre >80%: media geométrica de vel aparente y vel real (suaviza outliers)
- Quiebre 50-80%: media aritmética de vel aparente y vel real
- Quiebre <50%: vel real directa
- Fórmula pedido: (vel_suavizada × factor_pico × 3_meses) - stock_actual

---

## 2. MARYSABEL (Proveedor 28, Marca 28, Subrubro 60)

### Stock actual consolidado: 443 pares
⚠️ **Tiene el mismo problema base01/base03**: T38 tiene base01=-135, base03=+160 → consolidado=25. Pendiente fix similar al de Tivory.

### Stock por talle (consolidado actual):
T35:19, T36:116, T37:111, T38:25, T39:35, T40:49, T41:56, T42:24, T43:5, T44:10, T45:-3, T46:-4

### Proyección quiebre invierno 2026:

| Talle | Stock | Vel inv/mes | Quiebre inv hist% | Quiebra en... |
|-------|-------|-------------|-------------------|---------------|
| T35 | 19 | baja | — | OK |
| T36 | 116 | media | bajo | OK |
| T37 | 111 | media | bajo | OK |
| **T38** | **25** | **19.0** | **67%** | **MAYO** |
| T39 | 35 | 13.5 | 47% | JUNIO |
| T40 | 49 | 16.9 | 47% | JUNIO |
| T41 | 56 | 11.3 | 33% | AGOSTO |
| T42 | 24 | 8.9 | 0% | JUNIO |
| **T43** | **5** | **14.3** | **60%** | **ABRIL** |
| **T44** | **10** | **10.8** | **60%** | **MAYO** |
| T45 | -3 | 0 | 100% | YA QUEBRADO |
| T46 | -4 | 0 | 100% | YA QUEBRADO |

**Críticos**: T43 quiebra en ABRIL (5 pares, vel 14.3/mes). T38 y T44 quiebran en MAYO.

---

## 3. COMODITAS vs MARYSABEL — Comparación

| Métrica | Comoditas | Marysabel |
|---------|-----------|-----------|
| Ventas 3 años | 3342 pares | 2546 pares |
| Meses sin venta (proxy) | 24% | 16% |
| Quiebre real reconstruido | 74% | (pendiente global) |
| Estacionalidad | Muy marcada (pico may-jul) | Más pareja todo el año |
| Share temporada alta (abr-may) | 75-81% | 19-25% |
| Ventas verano (dic) | Muy bajo (8-31/mes) | Moderado (75 dic-2025) |

Comoditas domina la temporada fría. Marysabel vende más estable todo el año.

---

## 4. METODOLOGÍA DE QUIEBRE (referencia)

1. Obtener `stock_actual` de `msgestionC.dbo.stock` (consolidado base01+base03)
2. Obtener ventas mensuales de `ventas1` (excluir codigo 7,36) — 3 años
3. Obtener compras mensuales de `compras1` (operacion='+') — 3 años
4. Reconstruir stock mes a mes HACIA ATRÁS:
   - `stock_mes_anterior = stock_mes + ventas_mes - compras_mes`
5. Mes con `stock_inicio ≤ 0` → QUEBRADO
6. Vel real = ventas solo de meses NO quebrados / cantidad meses NO quebrados
7. Vel aparente = total ventas / total meses (SUBESTIMA demanda real)
8. Ejemplo clásico: CARMEL CANELA T42 — vel aparente 2/mes, vel real 10.8/mes, quiebre 87%

### Cuidado con base01/base03
- `msgestionC.dbo.stock` = UNION ALL de msgestion01 + msgestion03
- Cuando hay stock en ambas bases con signos opuestos → consolidado erróneo
- Verificar siempre consultando cada base por separado si los números no cierran

---

## 5. PENDIENTES PARA CONTINUAR

- [ ] **Comparar con propuesta del humano** — fer dijo que pasaría su propuesta manual para contrastar
- [ ] **Armar propuesta Marysabel** — ya tenemos el quiebre, falta calcular cantidades por talle
- [ ] **Fix stock base01/base03 de Marysabel** — mismo problema que Tivory (negativos en base01)
- [ ] **Cargar pedido Confortables** — confirmado pendiente
- [ ] **Ejecutar fix_stock_tivory_dep0.py** — limpia dep 0/6/8, script creado pero no ejecutado aún

---

## 6. QUERIES ÚTILES

### Stock consolidado pantuflas por marca y talle:
```sql
SELECT a.descripcion, a.grupo,
       CAST(a.talle AS VARCHAR) AS talle,
       SUM(s.stock_actual) AS stock
FROM msgestionC.dbo.stock s
JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
WHERE a.subrubro = 60
  AND s.deposito = 11
  AND s.serie = ' '
  AND a.marca IN (776, 28)  -- 776=Comoditas, 28=Marysabel
GROUP BY a.descripcion, a.grupo, a.talle
ORDER BY a.descripcion, a.talle
```

### Ventas mensuales por talle (ajustar marca):
```sql
SELECT YEAR(v.fecha) AS anio, MONTH(v.fecha) AS mes,
       a.talle, SUM(v.cantidad) AS pares
FROM msgestionC.dbo.ventas1 v
JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
WHERE a.marca = 776  -- o 28 para Marysabel
  AND a.subrubro = 60
  AND v.codigo NOT IN (7, 36)
  AND v.fecha >= '2023-01-01'
GROUP BY YEAR(v.fecha), MONTH(v.fecha), a.talle
ORDER BY 1, 2, 3
```
