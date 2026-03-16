#Son las tablas que usa el software Crosschek para descargar los datos de los relojes Anviz A300 de control de asistencia.
#Hay que configurar el Crosscheck para que use al DB Anviz2 del server MSSQL.
#Hay que configurar el Crosscehck para que descargue registros automaticamente y dejarlo abierto en alguna pc.

#REGISTROS DE ENTRADA-SALIDA
db_anviz2.define_table('Checkinout',
	Field('Logid','id'),
	Field('Userid','integer'),
	Field('CheckTime','datetime'),
	Field('CheckType','integer'),
	Field('Sensorid','integer'),
	Field('WorkType','integer'),
	Field('AttFlag','integer'),
	Field('Checked','integer'),
	Field('Exported','integer'),
	Field('OpenDoorFlag','integer'),
	migrate=False
	)