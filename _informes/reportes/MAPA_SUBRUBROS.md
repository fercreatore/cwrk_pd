# MAPA_SUBRUBROS.md — Mapa Subrubro → Industria / Categoría Comercial

> Última actualización: 2026-04-04
> Fuentes: `fix_sp_recupero_inversion.sql`, `agregar_industrias.sql`,
>           `crear_equivalencias_calzado_iram.sql`, `app_carga.py`

---

## Tabla maestra: `omicronvt.dbo.map_subrubro_industria`

La tabla vive en la base **omicronvt** del servidor 111.
- PK: `subrubro` (INT)
- Columna: `industria` (VARCHAR)

### JOIN estándar para agregar industria a una query de artículos

```sql
LEFT JOIN omicronvt.dbo.map_subrubro_industria ind ON a.subrubro = ind.subrubro
```

Donde `a` es `msgestion01art.dbo.articulo` (o alias de `msgestionC.dbo.articulo`).

---

## Mapa completo subrubro → industria

### Industria: Zapatería (calzado clásico y de moda)

| subrubro | descripción           | tipo_talle  | acepta_MP | notas               |
|----------|-----------------------|-------------|-----------|---------------------|
| 1        | ALPARGATAS            | CALZADO     | No        |                     |
| 2        | BORCEGOS              | CALZADO     | No        |                     |
| 3        | MAQUILLAJE            | ACCESORIO   | No        | históricamente acá  |
| 4        | (sin nombre en SUBRUBROS) | CALZADO | No        | incluido en script  |
| 5        | CHATA                 | CALZADO     | No        |                     |
| 6        | CHINELA               | OJOTA       | No        |                     |
| 7        | MOCASINES             | CALZADO     | No        |                     |
| 8        | (incluido en script)  | —           | —         |                     |
| 9        | (incluido en script)  | —           | —         |                     |
| 11       | OJOTAS                | OJOTA       | No        |                     |
| 12       | SANDALIAS             | CALZADO     | No        |                     |
| 13       | ZUECOS                | OJOTA       | No        |                     |
| 14       | BORCEGOS              | CALZADO     | No        | (subrubro 14 = borcego, 2 = similar) |
| 15       | BOTAS                 | CALZADO     | No        |                     |
| 16       | (incluido en script)  | —           | —         |                     |
| 17       | GUILLERMINA           | CALZADO     | No        | Comunión / zapato de fiesta niñas |
| 20       | ZAPATO DE VESTIR      | CALZADO     | No        | Hombre oficina + damas |
| 21       | CASUAL                | CALZADO     | No        |                     |
| 34       | (incluido en script)  | —           | —         |                     |
| 35       | PANCHA                | CALZADO     | No        |                     |
| 37       | FRANCISCANA           | CALZADO     | No        |                     |
| 38       | MERREL (outdoor clásico) | CALZADO  | No        |                     |
| 40       | NAUTICO               | CALZADO     | No        | Colegial / escuela  |
| 41-44    | (incluidos en script) | —           | —         |                     |
| 56       | FIESTA                | CALZADO     | No        |                     |
| 60       | PANTUFLA              | CALZADO     | No        | Agregado en `agregar_industrias.sql` |

### Industria: Deportes (calzado deportivo especializado)

| subrubro | descripción           | tipo_talle  | acepta_MP | notas               |
|----------|-----------------------|-------------|-----------|---------------------|
| 10       | ACC. DEPORTIVOS       | ACCESORIO   | No        |                     |
| 19       | BOTINES TAPON         | CALZADO     | Sí        | Fútbol campo        |
| 22       | CANILLERA             | ACCESORIO   | No        |                     |
| 33       | PELOTAS               | ACCESORIO   | No        |                     |
| 45       | BOTINES PISTA         | CALZADO     | Sí        | Fútbol sala / futsal |
| 47       | ZAPATILLA RUNNING     | CALZADO     | Sí        | **temporada todo el año** |
| 48       | ZAPATILLA TENNIS      | CALZADO     | Sí        | Escolar + adulto    |
| 49       | ZAPATILLA TRAINING    | CALZADO     | Sí        | **temporada todo el año** |
| 50       | ZAPATILLA BASKET      | CALZADO     | Sí        |                     |
| 51       | ZAPATILLA OUTDOOR     | CALZADO     | Sí        |                     |
| 53       | ZAPATILLA SKATER      | CALZADO     | Sí        |                     |
| 54       | BOTIN INDOOR          | CALZADO     | Sí        | Fútbol indoor / arco |
| 59       | ROLLER / PATÍN        | CALZADO     | No        |                     |

**Períodos Deportes**: H1 (ene-jun) / H2 (jul-dic) — no OI/PV como el calzado clásico.

### Industria: Mixto_Zap_Dep (frontera calzado/deporte)

| subrubro | descripción           | tipo_talle  | acepta_MP | notas               |
|----------|-----------------------|-------------|-----------|---------------------|
| 52       | ZAPATILLA CASUAL      | CALZADO     | Sí        | Lifestyle / sneaker urbano |
| 55       | ZAPATILLA SNEAKERS    | CALZADO     | Sí        | Moda + deporte      |

**Nota**: Este segmento usa período H1/H2 (igual que Deportes) en el calce financiero,
según `crear_calce_avanzado.sql`: `IN ('Deportes','Mixto_Zap_Dep')`.

### Industria: Marroquinería

| subrubro | descripción           | tipo_talle  | notas               |
|----------|-----------------------|-------------|---------------------|
| 18       | CARTERAS              | ACCESORIO   |                     |
| 24       | PARAGUAS              | ACCESORIO   |                     |
| 25       | MOCHILAS              | ACCESORIO   |                     |
| 26       | BILLETERAS            | ACCESORIO   |                     |
| 30       | BOLSOS                | ACCESORIO   |                     |
| 31       | (incluido en script)  | —           |                     |
| 39       | ACC. MARRO            | ACCESORIO   | Riñoneras, bandoleras |
| 58       | CINTOS                | CINTO       |                     |
| 68       | VALIJAS               | VALIJA      | Agregado en `agregar_industrias.sql` |
| 71       | RIÑONERA              | ACCESORIO   | (puede estar también en Marroquinería) |

### Industria: Indumentaria

| subrubro | descripción           | tipo_talle       | notas               |
|----------|-----------------------|------------------|---------------------|
| 23       | PANTALON              | INDUMENTARIA     |                     |
| 46       | CAMPERAS              | INDUMENTARIA     |                     |
| 57       | REMERAS               | INDUMENTARIA     |                     |
| 61       | BUZO                  | INDUMENTARIA     |                     |
| 62       | CALZA                 | INDUMENTARIA     |                     |
| 63       | MALLA                 | INDUMENTARIA     |                     |
| 70       | BOXER                 | INDUMENTARIA     |                     |

### Industria: Cosmética

| subrubro | descripción                | tipo_talle  | notas               |
|----------|----------------------------|-------------|---------------------|
| 27       | PLANTILLAS                 | ACCESORIO   | También insumo calzado |
| 28       | CORDONES                   | ACCESORIO   |                     |
| 29       | MEDIAS                     | ACCESORIO   |                     |
| 32       | COSMETICA DE CALZADO       | ACCESORIO   | Cremas, limpiadoras |

### Industria: Ferretero (seguridad / lluvia)

| subrubro | descripción           | tipo_talle  | notas               |
|----------|-----------------------|-------------|---------------------|
| 64       | ZAPATO DE TRABAJO     | CALZADO     | Agregado en `agregar_industrias.sql` |
| 65       | BOTA DE LLUVIA        | CALZADO     | Agregado en `agregar_industrias.sql` |

### Sin clasificar (subrubro 67 excluido intencionalmente)

- Subrubro **67** = PROMO FIN DE TEMPORADA → no clasificado en ninguna industria (decisión de negocio).

---

## Equivalencias de período por industria

| Industria           | Sistema de períodos | Meses temporada OI/H1    | Meses temporada PV/H2    |
|---------------------|---------------------|--------------------------|--------------------------|
| Zapatería           | OI / PV             | Mar-Ago (3-8)            | Sep-Feb (9-2)            |
| Marroquinería       | OI / PV             | Mar-Ago (3-8)            | Sep-Feb (9-2)            |
| Bijouterie          | OI / PV             | Mar-Ago (3-8)            | Sep-Feb (9-2)            |
| Cosmética           | OI / PV             | Mar-Ago (3-8)            | Sep-Feb (9-2)            |
| Deportes            | H1 / H2             | Ene-Jun (1-6)            | Jul-Dic (7-12)           |
| Mixto_Zap_Dep       | H1 / H2             | Ene-Jun (1-6)            | Jul-Dic (7-12)           |

---

## Dict Python equivalente (para scripts)

Basado en `fix_sp_recupero_inversion.sql` + `agregar_industrias.sql`:

```python
SUBRUBRO_INDUSTRIA = {
    # Zapatería — calzado clásico y de moda
    1:  'Zapatería',   # ALPARGATAS
    2:  'Zapatería',   # BORCEGOS
    3:  'Zapatería',   # MAQUILLAJE (histórico)
    4:  'Zapatería',
    5:  'Zapatería',   # CHATA
    6:  'Zapatería',   # CHINELA
    7:  'Zapatería',   # MOCASINES
    8:  'Zapatería',
    9:  'Zapatería',
    11: 'Zapatería',   # OJOTAS
    12: 'Zapatería',   # SANDALIAS
    13: 'Zapatería',   # ZUECOS
    14: 'Zapatería',   # BORCEGOS (variante)
    15: 'Zapatería',   # BOTAS
    16: 'Zapatería',
    17: 'Zapatería',   # GUILLERMINA
    20: 'Zapatería',   # ZAPATO DE VESTIR
    21: 'Zapatería',   # CASUAL
    34: 'Zapatería',
    35: 'Zapatería',   # PANCHA
    37: 'Zapatería',   # FRANCISCANA
    38: 'Zapatería',   # MERREL
    40: 'Zapatería',   # NAUTICO
    41: 'Zapatería',
    42: 'Zapatería',
    43: 'Zapatería',
    44: 'Zapatería',
    56: 'Zapatería',   # FIESTA
    60: 'Zapatería',   # PANTUFLA

    # Deportes — calzado deportivo especializado
    10: 'Deportes',    # ACC. DEPORTIVOS
    19: 'Deportes',    # BOTINES TAPON
    22: 'Deportes',    # CANILLERA
    33: 'Deportes',    # PELOTAS
    45: 'Deportes',    # BOTINES PISTA
    47: 'Deportes',    # ZAPATILLA RUNNING
    48: 'Deportes',    # ZAPATILLA TENNIS
    49: 'Deportes',    # ZAPATILLA TRAINING
    50: 'Deportes',    # ZAPATILLA BASKET
    51: 'Deportes',    # ZAPATILLA OUTDOOR
    53: 'Deportes',    # ZAPATILLA SKATER
    54: 'Deportes',    # BOTIN INDOOR
    59: 'Deportes',    # ROLLER/PATIN

    # Mixto_Zap_Dep — lifestyle / sneaker urbano
    52: 'Mixto_Zap_Dep',   # ZAPATILLA CASUAL
    55: 'Mixto_Zap_Dep',   # ZAPATILLA SNEAKERS

    # Marroquinería — bolsos, carteras, accesorios de moda
    18: 'Marroquinería',   # CARTERAS
    24: 'Marroquinería',   # PARAGUAS
    25: 'Marroquinería',   # MOCHILAS
    26: 'Marroquinería',   # BILLETERAS
    30: 'Marroquinería',   # BOLSOS
    31: 'Marroquinería',
    39: 'Marroquinería',   # ACC. MARRO (riñoneras, bandoleras)
    58: 'Marroquinería',   # CINTOS
    68: 'Marroquinería',   # VALIJAS

    # Indumentaria
    23: 'Indumentaria',    # PANTALON
    46: 'Indumentaria',    # CAMPERAS
    57: 'Indumentaria',    # REMERAS
    61: 'Indumentaria',    # BUZO
    62: 'Indumentaria',    # CALZA
    63: 'Indumentaria',    # MALLA

    # Cosmética — accesorios de cuidado / insumos
    27: 'Cosmética',       # PLANTILLAS
    28: 'Cosmética',       # CORDONES
    29: 'Cosmética',       # MEDIAS
    32: 'Cosmética',       # COSMETICA DE CALZADO

    # Ferretero — seguridad laboral y lluvia
    64: 'Ferretero',       # ZAPATO DE TRABAJO
    65: 'Ferretero',       # BOTA DE LLUVIA
}
```

---

## Query SQL para usarlo en scripts (sin JOIN a la tabla)

Si la tabla `map_subrubro_industria` no existe o se quiere evitar el JOIN:

```sql
CASE a.subrubro
    WHEN 1  THEN 'Zapatería' WHEN 2  THEN 'Zapatería' WHEN 3  THEN 'Zapatería'
    WHEN 4  THEN 'Zapatería' WHEN 5  THEN 'Zapatería' WHEN 6  THEN 'Zapatería'
    WHEN 7  THEN 'Zapatería' WHEN 8  THEN 'Zapatería' WHEN 9  THEN 'Zapatería'
    WHEN 11 THEN 'Zapatería' WHEN 12 THEN 'Zapatería' WHEN 13 THEN 'Zapatería'
    WHEN 14 THEN 'Zapatería' WHEN 15 THEN 'Zapatería' WHEN 16 THEN 'Zapatería'
    WHEN 17 THEN 'Zapatería' WHEN 20 THEN 'Zapatería' WHEN 21 THEN 'Zapatería'
    WHEN 34 THEN 'Zapatería' WHEN 35 THEN 'Zapatería' WHEN 37 THEN 'Zapatería'
    WHEN 38 THEN 'Zapatería' WHEN 40 THEN 'Zapatería' WHEN 41 THEN 'Zapatería'
    WHEN 42 THEN 'Zapatería' WHEN 43 THEN 'Zapatería' WHEN 44 THEN 'Zapatería'
    WHEN 56 THEN 'Zapatería' WHEN 60 THEN 'Zapatería'
    WHEN 10 THEN 'Deportes'  WHEN 19 THEN 'Deportes'  WHEN 22 THEN 'Deportes'
    WHEN 33 THEN 'Deportes'  WHEN 45 THEN 'Deportes'  WHEN 47 THEN 'Deportes'
    WHEN 48 THEN 'Deportes'  WHEN 49 THEN 'Deportes'  WHEN 50 THEN 'Deportes'
    WHEN 51 THEN 'Deportes'  WHEN 53 THEN 'Deportes'  WHEN 54 THEN 'Deportes'
    WHEN 59 THEN 'Deportes'
    WHEN 52 THEN 'Mixto_Zap_Dep' WHEN 55 THEN 'Mixto_Zap_Dep'
    WHEN 18 THEN 'Marroquinería' WHEN 24 THEN 'Marroquinería'
    WHEN 25 THEN 'Marroquinería' WHEN 26 THEN 'Marroquinería'
    WHEN 30 THEN 'Marroquinería' WHEN 31 THEN 'Marroquinería'
    WHEN 39 THEN 'Marroquinería' WHEN 58 THEN 'Marroquinería'
    WHEN 68 THEN 'Marroquinería'
    WHEN 23 THEN 'Indumentaria'  WHEN 46 THEN 'Indumentaria'
    WHEN 57 THEN 'Indumentaria'  WHEN 61 THEN 'Indumentaria'
    WHEN 62 THEN 'Indumentaria'  WHEN 63 THEN 'Indumentaria'
    WHEN 27 THEN 'Cosmética' WHEN 28 THEN 'Cosmética'
    WHEN 29 THEN 'Cosmética' WHEN 32 THEN 'Cosmética'
    WHEN 64 THEN 'Ferretero' WHEN 65 THEN 'Ferretero'
    ELSE 'Sin clasificar'
END AS industria
```

---

## Notas de negocio

### Deportes vs Calzado clásico vs Infantil

- **Deportes puro** (47, 48, 49, 50, 51, 53, 54): zapatillas con función técnica.
  - No tienen estacionalidad marcada, se venden todo el año.
  - Running (47) y Training (49) son los de mayor volumen.
- **Mixto_Zap_Dep** (52, 55): zapatilla casual/lifestyle, mezcla de Zapatería y Deportes.
  - Se usa período H1/H2 como Deportes en el calce financiero.
- **Zapatería clásica** (20, 21, 35, 37, 40, 56): OI/PV estricto.
- **Infantil**: No es una industria propia; los rubros 4 (Niños) y 5 (Niñas) con subrubros
  49/48/40 caen en **Deportes** o **Zapatería** según el subrubro del artículo.
  - Ejemplo: rubro=4, subrubro=40 (Náutico) → Zapatería.
  - Ejemplo: rubro=5, subrubro=49 (Training) → Deportes.

### Subrubros sin clasificar en `map_subrubro_industria`

- **67** = PROMO FIN DE TEMPORADA → intencionalmente excluido.
- **69** = ZAPATILLA HOCKEY → no en el mapa original; podría agregarse a Deportes.
- **70** = BOXER → podría agregarse a Indumentaria.
- **71** = RIÑONERA → podría agregarse a Marroquinería.
- **59** = ROLLER/PATIN → ya en Deportes vía `fix_sp_recupero_inversion.sql`.

### Sobre la tabla `map_subrubro_industria` en producción

- Creada originalmente con los datos de `fix_sp_recupero_inversion.sql` (SP que usa tabla temporal `#Industria`).
- Filas adicionales en `agregar_industrias.sql`: subrubros 60, 64, 65, 68.
- Verificar existencia en 111: `SELECT * FROM omicronvt.dbo.map_subrubro_industria ORDER BY subrubro`.
- Si no existe, usar el `CASE WHEN` de la sección anterior o recrear con el dict Python.

---

## Fuentes en el proyecto

| Archivo | Tipo | Contenido |
|---------|------|-----------|
| `_scripts_oneshot/_archivo/fix_sp_recupero_inversion.sql` | SQL | Mapa completo en tabla temporal `#Industria` (INSERT ~50 filas) |
| `_informes/calzalindo_informes_DEPLOY/sql/agregar_industrias.sql` | SQL | 4 filas adicionales: 60, 64, 65, 68 |
| `_informes/calzalindo_informes_DEPLOY/sql/crear_equivalencias_calzado_iram.sql` | SQL | `regla_talle_subrubro` (clasificación tipo_talle por subrubro, no industria) |
| `app_carga.py` línea 840 | Python | `SUBRUBROS` dict: código → nombre descriptivo |
| `app_reposicion.py` línea 201 | Python | `SUBRUBRO_TEMPORADA` dict: temporadas de compra/venta por subrubro |
| `app_locales.py` línea 171 | Python | Uso de `map_subrubro_industria` en query Streamlit |
