import requests, datetime

################## REEMPLAZADO POR fx_AjustarPorCer ###################################################################################################################################################
# ### Este token hay que pedirlo acá y dura un año, este vence aprox. 30/09/23:
# ### https://estadisticasbcra.com/api/documentacion
# token_bcra = 'BEARER eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2OTY2ODczNTksInR5cGUiOiJleHRlcm5hbCIsInVzZXIiOiJvbWljcm9udnRAZ21haWwuY29tIn0.g8dlI76HEvDljYon0tOguogZrOES5sKC4yI7bvcpZMZp4ahkfB3v5RFQaBEDbe1GA9PLdN-zPJfwOdQ6RYClAA'


# ### CLASE PARA ACTUALIZAR CER - 31/08/2023
# class Cer():
# 	def __init__(self, *args, **kwargs):
# 		self.token = token_bcra
# 		self.last_update = db().select(db.cer_update.ALL, orderby=db.cer_update.fecha).last()

# 	def update(self):

# 		if self.last_update:
			
# 			if (self.last_update['fecha']==request.now.date()) & (self.last_update['respuesta']=='OK'):
# 				return 'OK'

# 			else:

# 				self.consulta_bcra()

# 				return self.bcra
		
# 		# si nunca se hizo un update
# 		else:
# 			self.consulta_bcra()

# 			return self.bcra
				
# 	def consulta_bcra(self):
# 		try:
# 			api_call='https://api.estadisticasbcra.com/cer'
# 			data = requests.get(api_call, headers={'Authorization': self.token}).json()
		
# 			for row in data:	
# 	 			db.cer.update_or_insert(
# 	 				fecha=row['d'],
# 	 				coef=row['v'])

# 	 		db.cer_update.update_or_insert(db.cer_update.fecha==request.now.date(),
# 	 			fecha=request.now.date,
# 	 			fechahora=request.now,
# 	 			intento=1,## por ahora no reintento en el mismo día-
# 	 			respuesta='OK')

# 	 		self.bcra='OK'
	 	
# 	 	except:

# 	 		db.cer_update.update_or_insert(db.cer_update.fecha==request.now.date(),
# 	 			fecha=request.now.date,
# 	 			fechahora=request.now,
# 	 			intento=1,## por ahora no reintento en el mismo día-
# 	 			respuesta='Error')

# 	 		self.bcra='Error'


# def cer_get_today(monto,fecha):
# 	cer_fecha=db(db.cer.fecha<=fecha).select(db.cer.coef, orderby=~db.cer.fecha).first()
# 	cer_hoy=db(db.cer.fecha<=datetime.date.today()).select(db.cer.coef, orderby=~db.cer.fecha).first()
# 	monto_ajustado=float(cer_hoy.coef)*float(monto)/float(cer_fecha.coef)
# 	return monto_ajustado
################## FIN REEMPLAZADO POR fx_AjustarPorCer ###############################################################################################################################################


### 23/10/2023, retorna monto ajustado por Cer desde tabla omicronvt.cer, esta tabla se actualiza diariamente desde data_informes.py
### ejemplo de uso: fx_AjustarPorCer(100,'2023-01-01')
### uso una función sql directo en la db
def fx_AjustarPorCer(monto,fecha):
	# logger.debug('models/cer/fx_AjustaPorCer(%s, %s)'%(monto, fecha))
	if isinstance(fecha, str):
		fecha = datetime.datetime.strptime(fecha, '%Y-%m-%d').date()

	#si la fecha es futura, tomar fecha hoy
	fecha = request.now.date() if fecha>request.now.date() else fecha
	# logger.debug('models/cer/fx_AjustaPorCer, se toma fecha: %s'%fecha)

	try:
		t_sql = "SELECT omicronvt.dbo.AjustarPorCer(%s,'%s')"%(monto,fecha)
		# logger.debug('models/cer/fx_AjustaPorCer, query: %s'%t_sql)
		q = db_omicronvt.executesql(t_sql)
		# logger.debug('models/cer/fx_AjustaPorCer, resultado: %s'%q)

		res = q[0][0] if q[0][0]>0 else monto
	except:
		logger.error('models/cer/fx_AjustaPorCer, fallo al actualizar monto por Cer')
		res =  monto
	# logger.debug('models/cer/fx_AjustaPorCer, devuelve valor:%s'%res)

	return res

def fx_get_cer_date():

	t_sql = "SELECT top 1 MAX(fecha) as fecha, coef AS coef FROM dbo.cer WHERE fecha<=CAST(GETDATE() AS DATE) group by coef order by fecha desc"
	query = db_omicronvt.executesql(t_sql, as_dict=True)
	res = query[0]['fecha'].strftime('%d/%m/%Y') + ' ' + str(query[0]['coef'])



	return res



	