#feriados, los que caen en domingo no se cuentan
db.define_table('feriados',
Field('yea','integer',4, requires=IS_IN_SET([2019,2020,2021,2022,2023,2024,2025,2026,2027,2028,2029])),
Field('mes','integer',2, requires=IS_IN_SET([1,2,3,4,5,6,7,8,9,10,11,12])),
Field('cantidad','integer',1),
migrate=False)

db.define_table('feriados_2',
Field('fecha','date'),
migrate=False)


#porcentaje de incremento para objetivos
db.define_table('objetivos',
Field('inc_pares','float', requires=IS_FLOAT_IN_RANGE(0,10)),
Field('inc_ppp','float', requires=IS_FLOAT_IN_RANGE(0,10)),
Field('periodo_mes','integer', requires=IS_INT_IN_RANGE(1,13)),
Field('periodo_year','integer', requires=IS_INT_IN_RANGE(2015,2030)),
Field('periodo','string', unique=True, compute=lambda r: str(r['periodo_year'])+str(r['periodo_mes'])),
Field('fecha_modif','datetime', requires=IS_DATETIME(), default=request.now),
migrate=False)
db.objetivos.periodo_year.requires=IS_NOT_IN_DB(db(db.objetivos.periodo_mes==request.vars.periodo_mes),'objetivos.periodo_year',
error_message='Ese período ya tiene un objetivo asignado !')

#porcentaje de incremento para objetivos mayoristas
db.define_table('objetivos_otros',
Field('inc_pares','float', requires=IS_FLOAT_IN_RANGE(0,10)),
Field('inc_ppp','float', requires=IS_FLOAT_IN_RANGE(0,10)),
Field('periodo_mes','integer', requires=IS_INT_IN_RANGE(1,13)),
Field('periodo_year','integer', requires=IS_INT_IN_RANGE(2015,2030)),
Field('periodo','string', unique=True, compute=lambda r: str(r['periodo_year'])+str(r['periodo_mes'])),
Field('fecha_modif','datetime', requires=IS_DATETIME(), default=request.now),
migrate=False
)
db.objetivos_otros.periodo_year.requires=IS_NOT_IN_DB(db(db.objetivos_otros.periodo_mes==request.vars.periodo_mes),'objetivos_otros.periodo_year',
error_message='Ese período ya tiene un objetivo asignado !')

#sucursales
db.define_table('sucursales',
Field('nro','integer'),
Field('nombre','string', 50),
Field('direccion','string', 50),
Field('obj_fijo','boolean', default=False),
Field('monitor','boolean', default=True),
format='%(nombre)s',
migrate=False)

#objetivos fijos, para sucursales sin historial
db.define_table('objetivos_fijos',
Field('id_sucursal', 'reference sucursales'),
Field('pares','integer', requires=IS_INT_IN_RANGE(0,100000000)),
Field('monto','float', requires=IS_FLOAT_IN_RANGE(0,1000000000)),
Field('periodo_mes','integer', requires=IS_INT_IN_RANGE(1,13)),
Field('periodo_year','integer', requires=IS_INT_IN_RANGE(2015,2030)),
Field('periodo','integer', unique=True, compute=lambda r: int(str(r['id_sucursal'])+str(r['periodo_year'])+str(r['periodo_mes'])), requires=IS_NOT_IN_DB(db,'objetivos_fijos.periodo')),
migrate=False)
db.objetivos_fijos.periodo_year.requires=IS_NOT_IN_DB(db((db.objetivos_fijos.id_sucursal==request.vars.id_sucursal)&(db.objetivos_fijos.periodo_mes==request.vars.periodo_mes)),'objetivos_fijos.periodo_year',
error_message='Ese período ya tiene un objetivo asignado !')

#tabla de historial de inflación mensual para ajustar precios
db.define_table('inflacion',
Field('cod_mes','integer',6),
Field('porcentaje','float'),
migrate=False)
db.inflacion.cod_mes.requires=IS_NOT_IN_DB(db(db.inflacion.cod_mes==request.vars.cod_mes),'inflacion.cod_mes', error_message='Ese período ya tiene datos asignados !')

db.define_table('objetivos_estat',
Field('sucursal'),
Field('obj_year','integer'),
Field('obj_mes','integer'),
Field('obj_monto','float'),
Field('obj_pares','float'),
Field('obj_dias','integer'),
Field('obj_ppd', compute=lambda row: row.obj_pares/row.obj_dias),
Field('obj_mnt', compute=lambda row: row.obj_monto/row.obj_dias),
migrate=False)

db.define_table('diario_suc',
Field('fecha','datetime'),
Field('sucursal','integer'),
Field('clima','string'),
Field('obs_clima','string'),
Field('objetivo','float'),
Field('cumplido','float'),
Field('vidriera','integer'),
Field('orden_vidriera','string'),
Field('vereda_responsable','string'),
Field('vereda_horario','string'),
Field('vereda_con_bolsa','integer'),
Field('vereda_sin_bolsa','integer'),
Field('vereda_no_atendido','integer'),
Field('vereda_no_encontro','integer'),
Field('vereda_no_encontro_gusto','integer'),
Field('vereda_no_encontro_nro','integer'),
Field('vereda_no_encontro_modelo','integer'),
Field('vereda_no_encontro_otro','integer'),
Field('vereda_no_espera','integer'),
Field('producto_faltante','string'),
Field('perdido_por_stock','boolean'),
Field('perdido_por_vendedor','boolean'),
Field('deposito_ordenado','boolean'),
Field('detalle_pendientes','string'),
Field('limpieza','string'),
Field('observaciones','text'),
Field('vendedor_bueno','string'),
Field('vendedor_malo','string'),
Field('vendedor_evaluado','string'),
Field('marca_evaluada','string'),
Field('nivel_conoc','string'),
Field('procesado','boolean', default=False),
Field('procesado_usuario', 'integer', writable=False),
Field('procesado_fecha','datetime'),
Field('ingresado_usuario', 'integer', default=auth.user_id, writable=False),
migrate=False)

db.define_table('diario_suc_vendedores',
Field('id_diario_suc','string'),
Field('vendedor','string'),
Field('apariencia','string'),
migrate=False)

##### TABLAS ANVIZ - LECTORES DE HUELLA - CONTROL DE PERSONAL
# tabla con datos de los relojes
db.define_table('anviz_datos',
Field('device_id','integer'),
Field('ip','string',15),
Field('port','integer',5),
Field('ubicacion', 'reference sucursales'),
migrate=False)

#tabla que almacena los registros del reloj
db.define_table('anviz_registros',
Field('device','integer'),#numero de id del reloj, por si tengo varios
#Field('data_id','integer'),#id del registro del reloj, hace falta ?
Field('user_code','integer'),
Field('fechahora','datetime'),#fecha y hora del registro
Field('bkp_type','integer'),
Field('type_code','integer'),
migrate=False)
# esto evita registros duplicados basandose en device y fechahora.
# El reloj tiene su propio precedimiento para evitar registros duplicados.. pero por ahora lo soluciono con esto (bajo todos los registros y omito los duplicados)
db.anviz_registros._before_insert.append(lambda f: not db((db.anviz_registros.device == f['device']) & (db.anviz_registros.fechahora == f['fechahora'])).isempty())	


db.define_table('horario_empleados',
Field('tm_in','time'),
Field('tm_out','time'),
Field('tt_in','time'),
Field('tt_out','time'),
migrate=False)


### 10/10/18
### Objetivos vendedores
db.define_table('objetivos_vendedores_fijos',
Field('cod_vendedor','integer', requires=IS_IN_DB(db1,'viajantes.codigo','%(descripcion)s')),
Field('pares','integer', requires=IS_INT_IN_RANGE(0,10000000, error_message='Ingrese cantidad de pares.')),
Field('monto','float', requires=IS_FLOAT_IN_RANGE(0,100000000, error_message='Ingrese monto')),
Field('monto_ofertas', requires=IS_FLOAT_IN_RANGE(0,100000000, error_message='Ingrese monto de ofertas')), #este es el monto directo a vender (04/03/2020)
Field('periodo_mes','integer', requires=IS_IN_SET([1,2,3,4,5,6,7,8,9,10,11,12], error_message='Ingrese mes')),
Field('periodo_year','integer', IS_IN_SET([2020,2021,2022,2023,2024,2025,2026,2027,2028,2029], error_message='Ingrese nro de año')),
Field('periodo','string', unique=True, compute=lambda r: str(r['periodo_year'])+str(r['periodo_mes']).zfill(2)+'-'+str(r['cod_vendedor'])),
Field('fecha_modif','datetime', requires=IS_DATETIME(), default=request.now),
Field('sis_gen', 'boolean', default=False),
migrate=False)
db.objetivos_vendedores_fijos.cod_vendedor.requires=IS_NOT_IN_DB(db((db.objetivos_vendedores_fijos.periodo_mes==request.vars.periodo_mes)&(db.objetivos_vendedores_fijos.periodo_year==request.vars.periodo_year)),'objetivos_vendedores_fijos.cod_vendedor',
error_message='Ese vendedor ya tiene un objetivo asignado para este período!')

db.define_table('objetivos_vendedores_auto',
Field('cod_vendedor','integer', requires=IS_IN_DB(db1,'viajantes.codigo','%(descripcion)s')),
Field('inc_pares','float', requires=IS_FLOAT_IN_RANGE(0,10, error_message='Ingrese porcentaje de incremento de pares.')),
Field('inc_monto','float', requires=IS_FLOAT_IN_RANGE(0,10, error_message='Ingrese porcentaje de incremento de monto.')),
Field('monto_ofertas','float', requires=IS_FLOAT_IN_RANGE(0,100000000, error_message='Ingrese monto de ofertas')), #este es el monto directo a vender (04/03/2020)	
Field('periodo_mes','integer', requires=IS_IN_SET([1,2,3,4,5,6,7,8,9,10,11,12], error_message='Ingrese mes')),
Field('periodo_year','integer', requires=IS_IN_SET([2020,2021,2022,2023,2024,2025,2026,2027,2028,2029], error_message='Ingrese año')),
Field('periodo','string', unique=True, compute=lambda r: str(r['periodo_year'])+str(r['periodo_mes']).zfill(2)+'-'+str(r['cod_vendedor'])),
Field('fecha_modif','datetime', requires=IS_DATETIME(), default=request.now),
migrate=False)
db.objetivos_vendedores_auto.cod_vendedor.requires=IS_NOT_IN_DB(db((db.objetivos_vendedores_auto.periodo_mes==request.vars.periodo_mes)&(db.objetivos_vendedores_auto.periodo_year==request.vars.periodo_year)),'objetivos_vendedores_auto.cod_vendedor',
error_message='Ingrese nro de vendedor o ese vendedor ya tiene un objetivo asignado para este período!')


# db.define_table('prueba_vendedor',
# 	Field('cod_vendedor', 'integer', requires=IS_IN_DB(db1,'viajantes.codigo','%(descripcion)s')))

#guardo el cer publicado por el bcra
db.define_table('cer',
Field('fecha','date'),
Field('coef','float'),
migrate=False)

db.define_table('cer_update',
Field('fecha','date'),
Field('fechahora','datetime'),
Field('intento','integer'),
Field('respuesta','string'),
migrate=False)

#historial de buscas en consulta de precio por descripcion
db.define_table('histo_busq',
Field('fecha','datetime', default=request.now),
Field('cadena','string',128),
Field('origen','string',128),
Field('ip_addr','string'),
Field('usuario','string'),
migrate=False
)

#historial de buscas en consulta de precio por producto
db.define_table('producto_busq',
Field('fecha','datetime', default=request.now),
Field('articulo','integer'),
Field('cod_barra','string'),
Field('cod_sinonimo','string'),
Field('descrip_1','string'),
Field('descrip_5','string'),
Field('origen','string',128),
Field('ip_addr','string'),
Field('usuario','string'),
migrate=False)

db.define_table('contactos',
Field('nombre','string',250, requires=IS_NOT_EMPTY()),
Field('tel','string',100),
Field('mail','string',100, requires=IS_EMPTY_OR(IS_EMAIL())),
Field('obs','text',1000),
migrate=False)

db.define_table('comandas_config',
Field('dayback','integer', default=0),
Field('refresh','integer', default=20),
migrate=False)


db.define_table('stock_mg_snapshot',
Field('nombre','string', requires=IS_NOT_EMPTY(error_message='Ingrese una referencia')),
Field('fecha','datetime'),
Field('usuario'),
migrate=False)


db.define_table('stock_mg_snapshot_detalle',
Field('snap_id','reference stock_mg_snapshot'),	
Field('deposito', 'integer'),
Field('articulo', 'integer'),
Field('stock_actual', 'float'),
migrate=False)

db.define_table('informes_autogenerados',
Field('nombre','string'),
Field('consulta','text'),
migrate=False)


db.define_table('params_sistema',
Field('descrip', requires=IS_NOT_EMPTY()),
Field('valor','float'),
migrate=False)


