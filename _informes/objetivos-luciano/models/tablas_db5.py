## no tienen ID y por lo tanto dan error en DAL, pero si se usan con "db5.executesql()" andan ok, ver si se puede solucionar

# SECTORES DE ATENCION
db5.define_table('sectores',
	Field('sucursal','string'),
	Field('descripcion','string',20, requires=IS_NOT_EMPTY()),
	Field('activo','boolean', default=True),
	migrate=False)

# LETRAS PARA LOS TICKETS
db5.define_table('letras',
	Field('sucursal','string'),
	Field('letra','string',1),
	Field('sector_default','reference sectores', requires=IS_EMPTY_OR(IS_IN_DB(db3,db3.sectores.id,'%(descripcion)s'))),
	Field('texto','string'),
	Field('mostrar','boolean', default=True),
	migrate=False)


db5.define_table('turnos',
	Field('sucursal','string'),
	Field('sucursal_nro','integer'),
	Field('letra_id', 'reference letras'),
	Field('nro','integer'),
	Field('sector','string',1),
	Field('prioridad','integer',2, requires=IS_INT_IN_RANGE(1,3)),#valores admitidos 1 o 2
	Field('ingreso','datetime'),
	Field('diaingreso','date'),
	Field('llamado','datetime'),
	Field('llamado_activo','boolean', default=False),
	Field('llamado_procesado','boolean', default=False),
	Field('atendido','datetime'),
	Field('atendido_activo','boolean', default=False),
	Field('perdido','datetime'),
	Field('perdido_activo','boolean', default=False),
	Field('finalizado','date'),
	Field('activo','boolean', default=True),
	Field('transf_desde', 'reference turnos'),
	Field('vendedor','integer'),
	migrate=False)