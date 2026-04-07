# Deploy: Módulo Productividad e Incentivos

## Archivos a copiar al servidor 192.168.2.111

### 1. Controller (NUEVO)
```
controllers/informes_productividad.py
→ copiar a: C:\web2py\applications\calzalindo_objetivos_v2\controllers\informes_productividad.py
```

### 2. Vistas (NUEVAS — crear carpeta)
```
views/informes_productividad/dashboard.html
views/informes_productividad/vendedor.html
views/informes_productividad/estacionalidad.html
views/informes_productividad/incentivos.html
→ copiar a: C:\web2py\applications\calzalindo_objetivos_v2\views\informes_productividad\
```

### 3. Menú — agregar entrada (EDITAR menu.py existente)

Agregar ANTES de la línea `response.menu+=[('CLZ VENTAS'...`:

```python
response.menu+=[
    ('Productividad', False, URL(),[
        ('Dashboard RRHH', False, URL('informes_productividad','dashboard')),
        ('Estacionalidad', False, URL('informes_productividad','estacionalidad')),
        ('Simulador Incentivos', False, URL('informes_productividad','incentivos')),
    ])
]
```

### 4. Dependencia: pandas
Si no está instalado:
```
pip install pandas
```
(En el server Windows con Python 2.7, probablemente ya está por el uso en informes_efectividad)

## URLs después del deploy

- Dashboard: http://192.168.2.111:8000/calzalindo_objetivos_v2/informes_productividad/dashboard
- Estacionalidad: http://192.168.2.111:8000/calzalindo_objetivos_v2/informes_productividad/estacionalidad
- Simulador: http://192.168.2.111:8000/calzalindo_objetivos_v2/informes_productividad/incentivos
- Vendedor individual: http://192.168.2.111:8000/calzalindo_objetivos_v2/informes_productividad/vendedor/{codigo}
- API JSON productividad: http://192.168.2.111:8000/calzalindo_objetivos_v2/informes_productividad/api_productividad
- API JSON estacionalidad: http://192.168.2.111:8000/calzalindo_objetivos_v2/informes_productividad/api_estacionalidad_vendedor?cod={codigo}

## Acceso
- Requiere login y pertenecer al grupo `usuarios_nivel_1`
- Las APIs JSON no requieren auth (para gráficos AJAX)

## Qué incluye el módulo

1. **Dashboard RRHH**: KPIs globales, scatter productividad vs margen (Highcharts), tabla ranking con bandas de incentivo, alertas de vendedores estrella y a revisar
2. **Detalle vendedor**: Evolución mensual con CER, comisiones ajustadas por estacionalidad, conversión (turnos), gráfico Highcharts
3. **Estacionalidad**: Índice estacional real vs factor propuesto, explicación del modelo
4. **Simulador**: RRHH puede simular cuánto ganaría un vendedor en distintos escenarios

## Notas técnicas
- Usa las mismas conexiones de db.py (db1, dbC, db_omicronvt, db5)
- Sueldos de moviempl1 (codigo_movimiento 8,10,30,31)
- Ventas de ventas1_vendedor (omicronvt)
- Turnos de db5 (MySQL turnos_todos)
- CER via fx_AjustarPorCer (models/cer.py)
- Compatible Python 2.7 (web2py 2.24.1)
