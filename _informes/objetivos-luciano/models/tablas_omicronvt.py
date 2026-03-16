# -*- coding: utf-8 -*-

### total de cheques emitidos por mes.
### Trae datos desde dbC.movibanc1
db_omicronvt.define_table('cheques_emitidos_mensual',
	Field('mes','integer'),
	Field('mes_nombre','string'),
	Field('yea','integer'),
	Field('fecha_min','date'),
	Field('fecha_max','date'),
	Field('importe','float'),
	migrate=False
	)

### total de recibidas por mes.
### Trae datos desde dbC.movibanc1
db_omicronvt.define_table('tarjetas_banco_mensual',
	Field('mes','integer'),
	Field('mes_nombre','string'),
	Field('yea','integer'),
	Field('fecha_min','date'),
	Field('fecha_max','date'),
	Field('importe','float'),
	migrate=False
	)

### total de cheques emitidos por mes.
### Trae datos desde dbC.movibanc1
db_omicronvt.define_table('bancos_emitido_mensual',
	Field('mes','integer'),
	Field('mes_nombre','string'),
	Field('yea','integer'),
	Field('fecha_min','date'),
	Field('fecha_max','date'),
	Field('importe','float'),
	Field('codigo_movimiento','integer'),
	Field('descripcion','string'),
	migrate=False
	)




db_omicronvt.define_table('marcas_rentabilidad',
	Field('yea','string'),
	Field('pares','integer'),
	Field('monto','float'),
	Field('monto_costo','float'),
	Field('margen_B','float'),
	Field('marca','integer'),
	Field('marca_descrip','string'),
	migrate=False)

db_omicronvt.define_table('actualizaciones_data',
	Field('fecha','datetime'),
	Field('tabla','string'),
	Field('obs','text'),
	Field('desde','string'),
	migrate=False)

### se comparte con CLZ_VENTAS
db_omicronvt.define_table('agrupador_marca',
	Field('nombre','string', requires=IS_NOT_EMPTY()),
	Field('marcas_codigo','string', requires=IS_NOT_EMPTY()),
	migrate=False)

### se comparte con CLZ_VENTAS
db_omicronvt.define_table('agrupador_subrubro',
	Field('nombre','string', requires=IS_NOT_EMPTY()),
	Field('subrubros_codigo','string', requires=IS_NOT_EMPTY()),
	migrate=False)

### se comparte con CLZ_VENTAS
db_omicronvt.define_table('agrupador_rubro',
	Field('nombre','string', requires=IS_NOT_EMPTY()),
	Field('rubros_codigo','string', requires=IS_NOT_EMPTY()),
	migrate=False)


### guardo las notificaciones enviadas por mail
db_omicronvt.define_table('notificaciones_mail',
	Field('fecha','datetime', default=request.now),
	Field('enviado','boolean'),
	Field('estado','string'),
	Field('asunto','string'),
	Field('para','string'),
	Field('mensaje','text'),
	Field('aplicacion','string'),
	migrate=False)

### para guardar historico C.E.R.
#guardo el cer publicado por el bcra
db_omicronvt.define_table('cer',
	Field('fecha','date'),
	Field('coef','float'),
	Field('update_fechahora','datetime', default=request.now),
	Field('update_origen','string'),## desde donde tomo el dato
	Field('update_por','string'),## que aplición lo actualizo
	migrate=False)

db_omicronvt.define_table('dolar',
	Field('fecha','date'),
	Field('oficial','integer'),
	Field('libre','integer'),
	Field('update_fechahora','datetime', default=request.now),
	Field('update_origen','string'),## desde donde tomo el dato
	Field('update_por','string'),## que aplición lo actualizo
	Field('update_desde','string'),###pc desde donde se actualizo
	migrate=False)

### guarda los 10 mas vendidos en monto de ventas1 
### data_informes.py
db_omicronvt.define_table('ventas1_top10',
	Field('csr','string'),
	Field('monto','float'),
	Field('descrip','string'),
	Field('first_fecha','date'),
	Field('last_fecha','date'),
	Field('actualizado_fecha','datetime'),
	migrate=False
	)

### compras por local, se usa en data_informes.py
db_omicronvt.define_table('compras_por_local',
	Field('codigo','string'),
	Field('mes','string'),
	Field('depo','integer'),
	Field('cant','integer'),
	Field('costo','float'),
	Field('costo_cer','float'),
	Field('ult_compra','date'),
	Field('fecha_cer'),
	migrate=False)

db_omicronvt.define_table('ventas1_rentab',
	Field('codigo','integer'),
	Field('codigo_sinonimo','string'),
	Field('fecha','date'),
	Field('depo','integer'),
	Field('precio_venta','float'),
	Field('precio_venta_s_iva','float'),
	Field('precio_costo','float'),
	Field('fecha_ult_act','date'),
	Field('precio_costo_cer','float'),
	Field('cantidad','float'),
	Field('rentab','float'),
	migrate=False)

db_omicronvt.define_table('articulos_precios',
	Field('codigo','integer'),
	Field('codigo_sinonimo','string'),
	Field('precio_costo','float'),
	Field('precio_costo_cer','float'),
	Field('fecha_ult_act','date'),
	Field('iva','float'),
	Field('margen_2','float'),
	Field('precio_venta_2','float'),
	migrate=False)



db_omicronvt.define_table('indices_tiempo',
	Field('fecha', 'date'),
	Field('salario_minimo_vital_movil_mensual', 'float'),
	Field('salario_minimo_vital_movil_diario', 'float'),
	Field('salario_minimo_vital_movil_hora', 'float'),
	Field('cer', 'float'),
	Field('dolar', 'float'),
	Field('smvym_cer', 'float'),
	Field('smvym_dolar', 'float'),
	Field('dolar_libre','float'),
	migrate=False
	)


db_omicronvt.define_table('t_ventas_rentab',
	Field('codigo','integer'),
	Field('codigo_sinonimo','string'),
	Field('fecha','date'),
	Field('depo','integer'),
	Field('precio_venta','float'),
	Field('precio_costo','float'),
	Field('cantidad','float'),
	Field('fecha_ult_act','date'),
	Field('precio_costo_cer','float'),
	Field('rentab','float'),
	migrate=False
	)

## 20240102
db_omicronvt.define_table('t_ventas_rentabilidad',
	Field('codigo','integer'),
	Field('codigo_sinonimo','string'),
	Field('fecha','date'),
	Field('depo','integer'),
	Field('precio_venta','float'),
	Field('precio_costo','float'),
	Field('cantidad','float'),
	Field('fecha_ult_act','date'),
	Field('precio_costo_cer','float'),
	Field('oferta','string'),
	Field('marca','integer'),
	Field('marca_descrip'),
	Field('rentab','float'),
	migrate=False
	)


###PID-233
db_omicronvt.define_table('t_articulos_last_audit',
	Field('codigo','integer'),
	Field('codigo_sinonimo','string'),
	Field('codigo_barra','integer'),
	Field('fecha','date'),
	Field('depo_macro','integer'),
	Field('depo_macro_descrip','string'),
	Field('marca','integer'),
	Field('marca_descrip','string'),
	Field('proveedor','integer'),
	Field('proveedor_descrip','string'),
	Field('fecha_actualizacion','date'),
	migrate=False
	)
db_omicronvt.define_table('t_articulos_last_audit_tmp',
	Field('codigo','integer'),
	Field('depo','integer'),
	Field('depo_nombre','string'),
	Field('fecha','date'),
	migrate=False)

db_omicronvt.define_table('t_vendedores_asesores',
	Field('clz_ventas_id','integer'),### id de usuario en CLZ_VENTAS
	Field('viajantes_id','integer'),### numero de viajante en Macroges
	migrate=False)

db_omicronvt.define_table('t_sucursales_transferencias_mes',
	Field('sucursal','string'),
	Field('nombre','string'),
	Field('mes','string'),
	Field('entrada','integer'),
	Field('salida','integer'),
	Field('neto','integer'),
	Field('actualizado','datetime'),
	migrate=False)

db_omicronvt.define_table('t_sucursales_transferencias_mes_valorizadas',
	Field('sucursal','string'),
	Field('nombre','string'),
	Field('mes','string'),
	Field('entrada','float'),
	Field('entrada_costo_cer','float'),
	Field('salida','float'),
	Field('salida_costo_cer','float'),
	Field('neto','float'),
	Field('neto_costo_cer','float'),
	Field('actualizado','datetime'),
	migrate=False)

db_omicronvt.define_table('t_resultados_por_local',
	Field('mes','string'),
	Field('depo','integer'),
	Field('compras_cantidad','float'),
	Field('compras_importe','float'),
	Field('compras_importe_cer','float'),
	Field('ventas_cantidad','float'),
	Field('ventas_importe','float'),
	Field('ventas_importe_cer','float'),
	migrate=False
	)

db_omicronvt.define_table('t_articulos_dias_stock',
	Field('csr','integer'),
	Field('marca','integer'),
	Field('rubro','integer'),
	Field('subrubro','integer'),
	Field('linea','integer'),
	Field('ultima_compra','date'),
	Field('ultima_compra_cant','integer'),
	Field('stock_actual','integer'),
	Field('dias_stock','integer'),
	migrate=False)

### para IN0007
db_omicronvt.define_table('t_articulos_dias_stock_fc_last1M',
Field('csr','string'),
Field('fecha_uc','date'),
Field('cant_uc','float'),
Field('cant_vt','float'),
Field('stock_actual','float'),
Field('stock_anterior','float'),
Field('neto','float'),
Field('transc','float'),
Field('vent_xdia','float'),
Field('dias_stock','float'),
Field('descrip','string'),
Field('marca','integer'),
Field('marca_descrip','string'),
Field('marca_completa','string'),
Field('rubro','integer'),
Field('rubro_descrip','string'),
Field('rubro_completo','string'),
Field('subrubro','integer'),
Field('subrubro_descrip','string'),
Field('subrubro_completo','string'),
Field('linea','integer'),
Field('imagen','string'),
Field('data_desde','date'),
Field('updated_at','datetime'),
migrate=False)

db_omicronvt.define_table('t_articulos_dias_stock_fc_last3M',
Field('csr','string'),
Field('fecha_uc','date'),
Field('cant_uc','float'),
Field('cant_vt','float'),
Field('stock_actual','float'),
Field('stock_anterior','float'),
Field('neto','float'),
Field('transc','float'),
Field('vent_xdia','float'),
Field('dias_stock','float'),
Field('descrip','string'),
Field('marca','integer'),
Field('marca_descrip','string'),
Field('marca_completa','string'),
Field('rubro','integer'),
Field('rubro_descrip','string'),
Field('rubro_completo','string'),
Field('subrubro','integer'),
Field('subrubro_descrip','string'),
Field('subrubro_completo','string'),
Field('linea','integer'),
Field('imagen','string'),
Field('data_desde','date'),
Field('updated_at','datetime'),
migrate=False)

db_omicronvt.define_table('t_articulos_dias_stock_fc_last6M',
Field('csr','string'),
Field('fecha_uc','date'),
Field('cant_uc','float'),
Field('cant_vt','float'),
Field('stock_actual','float'),
Field('stock_anterior','float'),
Field('neto','float'),
Field('transc','float'),
Field('vent_xdia','float'),
Field('dias_stock','float'),
Field('descrip','string'),
Field('marca','integer'),
Field('marca_descrip','string'),
Field('marca_completa','string'),
Field('rubro','integer'),
Field('rubro_descrip','string'),
Field('rubro_completo','string'),
Field('subrubro','integer'),
Field('subrubro_descrip','string'),
Field('subrubro_completo','string'),
Field('linea','integer'),
Field('imagen','string'),
Field('data_desde','date'),
Field('updated_at','datetime'),
migrate=False)

db_omicronvt.define_table('t_articulos_dias_stock_fc',
Field('csr','string'),
Field('fecha_uc','date'),
Field('cant_uc','float'),
Field('cant_vt','float'),
Field('stock_actual','float'),
Field('stock_anterior','float'),
Field('neto','float'),
Field('transc','float'),
Field('vent_xdia','float'),
Field('dias_stock','float'),
Field('descrip','string'),
Field('marca','integer'),
Field('marca_descrip','string'),
Field('marca_completa','string'),
Field('rubro','integer'),
Field('rubro_descrip','string'),
Field('rubro_completo','string'),
Field('subrubro','integer'),
Field('subrubro_descrip','string'),
Field('subrubro_completo','string'),
Field('linea','integer'),
Field('imagen','string'),
Field('data_desde','date'),
Field('updated_at','datetime'),
migrate=False)