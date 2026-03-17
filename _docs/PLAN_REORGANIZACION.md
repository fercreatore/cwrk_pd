# Plan de Reorganización — cowork_pedidos

## El problema

La carpeta tiene 3800+ archivos y 5 proyectos distintos mezclados. No se encuentra nada, hay docs que dicen lo mismo, scripts ejecutados mezclados con pendientes, y 1.2GB de PDFs/Excel en `compras/`.

## Diagnóstico rápido

| Lo que hay | Tamaño | Pertenece acá? |
|---|---|---|
| Pipeline pedidos (paso*.py, config, apps) | ~500KB | ✅ SÍ — es el core |
| _scripts_oneshot/ (63 archivos) | ~600KB | ✅ Pero necesita limpieza |
| compras/ (PDFs, Excel facturas) | **1.2GB** | ⚠️ Son datos, no código |
| clz_wpu/ (Web2py framework) | 41MB | ❌ Otro proyecto |
| _informes/ (productividad, deploy) | 1.7MB | ❌ Otro proyecto |
| _freelance/ (vendedor freelance) | 256KB | ❌ Otro proyecto |
| valijas/ (proyecto GO) | 6.8MB | ❌ Otro proyecto |
| _tiendanube/ (web, SEO) | 832KB | ❌ Otro proyecto |
| _archivo/ (histórico) | 8.9MB | ⚠️ Basura a limpiar |
| 8 docs raíz (.md, .txt) | ~115KB | ⚠️ Se superponen |

## Propuesta: 3 pasos

### PASO 1 — Sacar lo que no es pedidos

Mover a carpetas propias en el Desktop (o donde prefieras):

```
~/Desktop/calzalindo_informes/    ← ex _informes/
~/Desktop/calzalindo_freelance/   ← ex _freelance/
~/Desktop/calzalindo_tiendanube/  ← ex _tiendanube/
~/Desktop/calzalindo_valijas/     ← ex valijas/
~/Desktop/clz_wpu/                ← ex clz_wpu/
```

Con esto cowork_pedidos baja de 1.3GB a ~1.2GB (los PDFs de compras siguen).

### PASO 2 — Limpiar oneshot y docs

**_scripts_oneshot/** quedaría así:

```
_scripts_oneshot/
├── _pendientes/          ← lo que falta ejecutar
│   ├── insertar_comoditas.py
│   ├── insertar_confortable.py
│   ├── insertar_wake_inv26.py
│   ├── crear_tabla_asignacion.py
│   └── borrar_54_juana_va.py
├── _fixes/               ← fixes puntuales pendientes
│   ├── fix_piccadilly_catag.py    (EJECUTADO hoy)
│   ├── fix_stock_ppx3941_dep0.py
│   ├── fix_stock_ls879_footy.py   (EJECUTADO)
│   └── fix_desc1_wake.py
├── _herramientas/        ← scripts reutilizables
│   ├── alta_masiva_faltantes.py
│   ├── poblar_asignacion.py
│   ├── auto_sync_pedidos.py
│   ├── ejecutar_todo_pendiente.sh
│   ├── update_ean_footy.py
│   └── verificar_e_insertar_111.py
└── _archivo/             ← TODO lo ya ejecutado (ya existe, ampliar)
    ├── insertar_knu_gtn.py ✅
    ├── insertar_carmel_ringo.py ✅
    ├── insertar_diadora.py ✅
    ├── insertar_piccadilly.py ✅
    ├── insertar_footy.py ✅
    ├── insertar_atomik_runflex.py ✅
    ├── insertar_go_dance.py ✅
    ├── insertar_lesedife.py ✅
    ├── fix_barra_tivory.py ✅
    ├── fix_fecha_alta_y_ls879.py ✅
    ├── fix_stock_footy.py ✅
    ├── fix_stock_footy_rev.py ✅
    ├── fix_stock_remito_tivory.py ✅
    ├── fix_stock_tivory_base01.py ✅
    ├── fix_stock_tivory_dep0.py ✅
    ├── revertir_remito_tivory.py ✅
    ├── modificar_carmel_134069.py ✅
    ├── recrear_diadora_1134068.py ✅
    ├── (+ los que ya estaban en _archivo)
    └── *.json (lesedife_cross, lesedife_items, quiebre_confortable)
```

**Docs** — unificar los 8 archivos de la raíz:

| Ahora (8 archivos) | Después (3 archivos) |
|---|---|
| CLAUDE.md | **CLAUDE.md** (mantener, es el maestro) |
| BITACORA_DESARROLLO.md | **BITACORA_DESARROLLO.md** (mantener) |
| ESTADO_PROYECTOS.md | Absorber en CLAUDE.md |
| INSTRUCCIONES_COWORK.md | Absorber en CLAUDE.md |
| ANALISIS_PEDIDOS_INV_2026.txt | Mover a `_docs/` |
| INDICE_ANALISIS_INV_2026.txt | Mover a `_docs/` |
| PANTUFLAS_COMODITAS_ANALYSIS.txt | Mover a `_docs/` |
| RESUMEN_RAPIDO_PEDIDOS.txt | Mover a `_docs/` |

### PASO 3 — Estructura final de cowork_pedidos

```
cowork_pedidos/
├── CLAUDE.md                    ← único doc maestro
├── BITACORA_DESARROLLO.md       ← historial cronológico
├── config.py                    ← configuración proveedores
├── requirements.txt
│
├── paso1_verificar_bd.py        ← pipeline core
├── paso2_buscar_articulo.py         (se queda en raíz porque
├── paso3_calcular_periodo.py         deploy.sh ya los copia)
├── paso4_insertar_pedido.py
├── paso5_parsear_excel.py
├── paso5b_parsear_topper.py
├── paso6_flujo_completo.py
├── paso6b_flujo_topper.py
├── paso7_buscar_imagenes.py
├── paso7_reconstruir_colores.py
├── paso8_carga_factura.py
├── ocr_factura.py
├── proveedores_db.py
│
├── app_carga.py                 ← apps Streamlit
├── app_pedido_auto.py
├── app_reposicion.py
│
├── _scripts_oneshot/            ← reorganizado (ver arriba)
├── _excel_pedidos/              ← se queda
├── _sync_tools/                 ← se queda
├── _docs/                       ← análisis, contexto, instrucciones
├── compras/                     ← datos facturas (1.2GB)
├── .streamlit/
├── tests/
└── logos/
```

## Resumen de impacto

- **Sacar**: clz_wpu (41MB), _informes, _freelance, valijas, _tiendanube
- **Archivar**: ~20 scripts ejecutados → _archivo
- **Unificar**: 8 docs → 3
- **Resultado**: carpeta limpia, solo pipeline pedidos, oneshot organizados por estado
