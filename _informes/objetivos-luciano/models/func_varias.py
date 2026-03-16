#importo módulos necesarios
import datetime, calendar, locale, dateutil.relativedelta as rdel

#Chequea inflacion para el mes anterior al actual, si no están cargados para el mes en curso copia los del mes anterior
def check_inflacion():
	#inflacion vigente/actual(es la del mes anterior)
	mes_vigente='%02d'%(datetime.date.today()+rdel.relativedelta(months=-1)).month
	yea_vigente=(datetime.date.today()+rdel.relativedelta(months=-1)).year
	#actual=str((datetime.date.today()+rdel.relativedelta(months=-1)).year)+str((datetime.date.today()+rdel.relativedelta(months=-1)).month)
	actual=str(yea_vigente)+str(mes_vigente)
	#reviso si existe en la db
	existe = db(db.inflacion.cod_mes==actual).select().first()
	if not existe:
		#ultimo mes que existe
		getlast=db(db.inflacion.id>0).select(db.inflacion.cod_mes, db.inflacion.porcentaje, orderby=~db.inflacion.cod_mes).first()
		#mes anterior al faltante
		mes_precedente='%02d'%(datetime.date.today()+rdel.relativedelta(months=-2)).month
		yea_precedente=(datetime.date.today()+rdel.relativedelta(months=-2)).year
		precedente=str(yea_precedente)+str(mes_precedente)
		#chequeo que no falte un mes en el medio
		if str(getlast['cod_mes'])==precedente:
			db.inflacion.insert(cod_mes=actual, porcentaje=getlast['porcentaje'])
			status=1#(No existe pero se inserto nueva OK)
		else:
			status=0#(No existe y no se puede insertar porque tampoco existe mes anterior)
	else:
		status=2#(ya existe)

	return status



## retorna string de fecha en formato argentina
def FF(dt):
	try:		
		if isinstance(dt, datetime.datetime):
			return dt.strftime('%d/%m/%Y %H:%M:%S')
		else:
			return dt.strftime('%d/%m/%Y')
	except:
		return ''


## retorna string de fechahora en formato ingles, para insertar en DB
def FFT(dt):
	try:		
		if isinstance(dt, datetime.datetime):
			return dt.strftime('%Y-%m-%d %H:%M:%S')
		else:
			return dt.strftime('%Y-%m-%d 00:00:00')
	except:
		return ''

## retorna string de fecha en formato ingles, para insertar en DB
def FFD(dt):
	try:		
		if isinstance(dt, datetime.datetime):
			return dt.strftime('%Y-%m-%d')
		else:
			return dt.strftime('%Y-%m-%d')
	except:
		return ''

## retorna numeros formateados
def FN(num):
	try:
		return '{:,}'.format(int(num)).replace(',','.')
	except:
		return 0

## retorna precios formateados, con 2 decimales
def FND(num):
	# return "{:.2f}".format(precio)
	try:
		return '{:,.2f}'.format(int(num)).replace(',','*').replace('.',',').replace('*','.')
	except:
		return 0
