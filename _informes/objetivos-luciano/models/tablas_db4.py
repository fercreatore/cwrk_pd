#MULTISUCURSAL - SUCURSAL ACTIVA
db4.define_table('sucursal',
	Field('nombre','string'),
	Field('activa','boolean',default=False))

# SECTORES DE ATENCION
db4.define_table('sectores',
	Field('descripcion','string',20, requires=IS_NOT_EMPTY()),
	Field('activo','boolean', default=True))

# LETRAS PARA LOS TICKETS
db4.define_table('letras',
	Field('letra','string',1),
	Field('sector_default','reference sectores', requires=IS_EMPTY_OR(IS_IN_DB(db3,db3.sectores.id,'%(descripcion)s'))),
	Field('texto','string'),
	Field('mostrar','boolean', default=True))


db4.define_table('turnos',
	#Field('letra','string', requires=IS_IN_SET(['D','C'])),
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
	Field('vendedor','integer')
	)

db4.define_table('monitores',
	Field('mon_01','boolean', default=False),
	Field('mon_02','boolean', default=False),
	Field('mon_03','boolean', default=False),
	Field('mon_04','boolean', default=False),
	Field('mon_05','boolean', default=False),
	Field('mon_06','boolean', default=False),
	Field('mon_07','boolean', default=False),
	Field('mon_08','boolean', default=False),
	Field('mon_09','boolean', default=False))
