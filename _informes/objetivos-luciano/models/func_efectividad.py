####### TICKET PROMEDIO (Monto vendido/cantidad de comprobantes) y EFECTIVIDAD para surcursales con turnero ########
def tickets_por_sucursal(suc,desde,hasta):	
	#tickets de venta
	tks=db1.executesql("SELECT (COUNT(DISTINCT (CASE WHEN omicron_ventas1.operacion='+' THEN omicron_ventas1.numero END)) - COUNT(DISTINCT (CASE WHEN omicron_ventas1.operacion='-' THEN omicron_ventas1.numero END))) AS tkts from omicron_ventas1 WHERE deposito=%s AND (fecha>='%s' AND fecha<='%s') AND codigo<>7"%(suc,desde,hasta))
	return tks[0][0]
