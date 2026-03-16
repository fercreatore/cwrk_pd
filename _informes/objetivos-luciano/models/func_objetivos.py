#importo módulos necesarios
import datetime, calendar, locale, numpy

#Calendario de numpy para dias habiles(todos los dias menos los domingos)
calendario_calza=numpy.busdaycalendar([1,1,1,1,1,1,0])

def master_check_objetivos(mes,yea,depo):
	logger.debug('Master Check OBJETIVOS')
	left=[db.sucursales.on(db.sucursales.id==db.objetivos_fijos.id_sucursal)]
	fijo_suc = db((db.objetivos_fijos.periodo_mes==mes)&(db.objetivos_fijos.periodo_year==yea)&(db.sucursales.nro==depos)).select(db.objetivos_fijos.ALL, left=left).first()
	return


#Chequea los porcentajes de incremento de la tabla:OBJETIVOS, si no están cargados para el mes en curso copia los del mes anterior
def check_objetivos(m,y):
	#logger.debug('Check OBJETIVOS')
	actual = db((db.objetivos.periodo_mes==m)&(db.objetivos.periodo_year==y)).select(db.objetivos.ALL, orderby=db.objetivos.fecha_modif).first()
	if not actual:
		last = db().select(db.objetivos.ALL, orderby=db.objetivos.fecha_modif).first()
		db.objetivos.insert(
			inc_pares=last.inc_pares,
			inc_ppp=last.inc_ppp,
			periodo_mes=m,
			periodo_year=y
			)
		logger.debug('Check OBJETIVOS: No existe objetivo para el mes actual se usa el último anterior (%s-%s)'%(last.periodo_mes, last.periodo_year))
	return 

def check_objetivos_fijos(m,y,d):
	logger.debug('Check OBJETIVOS FIJOS (%s-%s) para sucursal: %s'%(m,y,d))
	left=[db.sucursales.on(db.sucursales.id==db.objetivos_fijos.id_sucursal)]
	actual = db((db.objetivos_fijos.periodo_mes==m)&(db.objetivos_fijos.periodo_year==y)&(db.sucursales.nro==d)).select(db.objetivos_fijos.ALL, left=left).first()
	if not actual or actual==None:
		last = db(db.sucursales.nro==d).select(db.objetivos_fijos.ALL, left=left, orderby=~db.objetivos_fijos.periodo).first()
		db.objetivos_fijos.insert(
			id_sucursal=last.id_sucursal,
			pares=last.pares,
			monto=last.monto,
			periodo_mes=m,
			periodo_year=y
			)
		logger.debug('Check OBJETIVOS FIJOS: No existe objetivo para el mes actual se usa el último anterior (%s-%s)'%(last.periodo_mes, last.periodo_year))	
	return actual	

#Chequea los porcentajes de incremento de la tabla:OBJETIVOS_OTROS, si no están cargados para el mes en curso copia los del mes anterior
def check_objetivos_otros(m,y):
	#logger.debug('Check OBJETIVOS OTROS')
	actual = db((db.objetivos_otros.periodo_mes==m)&(db.objetivos_otros.periodo_year==y)).select(db.objetivos_otros.ALL, orderby=db.objetivos_otros.fecha_modif).first()
	if not actual:
		last = db().select(db.objetivos_otros.ALL, orderby=db.objetivos_otros.fecha_modif).first()
		db.objetivos_otros.insert(
			inc_pares=last.inc_pares,
			inc_ppp=last.inc_ppp,
			periodo_mes=m,
			periodo_year=y
			)
		logger.debug('Check OBJETIVOS OTROS: No existe objetivo para el mes actual se usa el último anterior (%s-%s)'%(last.periodo_mes, last.periodo_year))
	return 

#Calculo de dias del mes
def mes_laborable(dia,mes,yea):
	#combino mes y año para comparar
	combo=str(yea)+str('%02d'%mes)
	combo_actual=str(datetime.date.today().year)+str('%02d'%datetime.date.today().month)
	
	if combo<combo_actual:
		dia=dias_total=calendar.monthrange(int(yea),int(mes))[1]
		porcent=100
	elif combo==combo_actual:
		dia=int(dia)
		dias_total=calendar.monthrange(int(yea),int(mes))[1]
		porcent=round(dia*100/dias_total,2)
		domingos=len([1 for i in calendar.monthcalendar(yea,mes) if i[6] !=0])
		sin_domingos=dias_total-domingos
		#q=db((db.feriados.mes==mes)&(db.feriados.yea==yea)).select(db.feriados.cantidad).first()
		#sin_feriados=sin_domingos-q.cantidad
		sin_feriados=sin_domingos-1
	elif combo>combo_actual:
		dia=0
		dias_total=0
		porcent=0
	return {'total':dias_total,'porcent':porcent,'diasl':sin_domingos,'diaslsf':sin_feriados}

def calc_ddm(dia,mes,yea):
	#busco los feriados ya cumplidos del mes
	fer_pas=db((db.feriados_2.fecha.day()<=dia)&(db.feriados_2.fecha.month()==mes)&(db.feriados_2.fecha.year()==yea)).count()
	#busco los feriados totales del mes
	fer_tot=db((db.feriados_2.fecha.month()==mes)&(db.feriados_2.fecha.year()==yea)).count()

	dt=datetime.date	#abrevio
	mesf='%02d'%(mes)
	monthf='%02d'%(datetime.date.today().month)
	#combo periodo parametros
	p1=int(str(yea)+str(mesf))
	#combo periodo actual
	p2=int(str(datetime.date.today().year)+(str(monthf)))
	if p1<p2:# mes anterior
		desde=dt(int(yea),int(mes),1)
		hasta=dt(int(yea),int(mes),calendar.monthrange(int(yea),int(mes))[1])+datetime.timedelta(days=1)
		dias=dias_total=numpy.busday_count(desde,hasta,weekmask='1111110')-fer_tot
		porcent=100
	elif p1==p2:#mes actual
		hoy=datetime.date.today()
		desde=dt(int(yea),int(mes),1)
		hasta=dt(int(yea),int(mes),calendar.monthrange(int(yea),int(mes))[1])+datetime.timedelta(days=1)
		dias_total=numpy.busday_count(desde,hasta,weekmask='1111110')-fer_tot
		dias=numpy.busday_count(desde,hoy,weekmask='1111110')-fer_pas+1
		porcent=float(dias)/float(dias_total)*100
	elif p1>p2:#mes posterior
		dias=0
		dias_total=0
		porcent=0


	return dict(dias=dias,diast=dias_total,porcent=porcent, p1=p1, p2=p2, monthf=monthf)	


def pvso(mon,yea,dep):
	
	###PID-225 - Se cambia base de datos
	t_sql ="SELECT SUM(total_item) AS valor, SUM(cantidad) AS pares FROM ventas1_vendedor WHERE deposito=%s AND DATEPART(MONTH, fecha)=%s AND DATEPART(YEAR, fecha)=%s"%(dep,mon,yea)

	data=db_omicronvt.executesql(t_sql)
	pares=data[0][1] if data[0][1] else 0
	total=data[0][0] if data[0][0] else 0
	return float(pares),float(total)	

#pares vendidos sin ofertas por dia y sucursal(SIRVE SOLO PARA CALCULO MENSUAL, YA QUE CHEQUEA CONTRA FECHA ACTUAL) y sin remitos internos(codigo 7)
def pvh(dia,mon,yea,dep):
	if datetime.date(int(yea),int(mon),int(dia))==datetime.date.today():
		###PID-225 - Se cambia base de datos
		t_sql="SELECT SUM(cantidad) AS pares FROM ventas1_vendedor WHERE deposito=%s AND DATEPART(DAY, fecha)=%s AND DATEPART(MONTH, fecha)=%s AND DATEPART(YEAR, fecha)=%s"%(dep, dia, mon, yea)
		data=db_omicronvt.executesql(t_sql)
		pares=data[0][0]
	else:
		pares=0
	return pares

#Devuelve las ventas del día de la fecha por depósito, calcula ppp.
def vhoy(depo):
	###PID-225 - Se cambia base de datos	
	t_sql = "SELECT SUM(total_item) AS valor, SUM(cantidad) as pares FROM ventas1_vendedor WHERE fecha='%s' AND deposito='%s' "%(datetime.date.today().strftime('%Y-%m-%d'),str(depo))
	results=db_omicronvt.executesql(t_sql)
	monto,pares=results[0]
	if monto is None:
		monto=0
	if pares is None:
		pares=0
	if pares==0:
		ppp=0
	else:
		ppp=monto/pares
	return float(monto),int(pares),float(ppp)