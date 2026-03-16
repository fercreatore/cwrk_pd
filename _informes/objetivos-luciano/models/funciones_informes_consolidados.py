# -*- coding: utf-8 -*-

### funciones comunes que se usan en diferentes informes

### MODIFICADO 17/01/23 PARA CALCULAR RENTABILIDAD EN BASE A PRECIO DE COSTO(ESTA EN LA VENTA)
#USA VISTA CONSOLIDADA : dbo.omicron_ventas1
#Devuelve: Unidades vendidas, total ventas sin iva, total devoluciones sin iva,codigo de marca, descripcion de marca
### Se usa en: informes_encargados_sucursal
def get_ventas_consolidado(**kwargs):

	filtros = fx_filtros_art(**kwargs)

	t_sql = "SELECT SUM((CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END)) as cant, "\
		"SUM((case when v.operacion='+' then v.precio when v.operacion='-' then -v.precio end) / 1.21 * v.cantidad)  AS totalvent, "\
		"SUM(case when v.operacion='+' then v.precio_costo when v.operacion='-' then -v.precio_costo end * v.cantidad) as costovent,"\
		"a.marca, m.descripcion, v.deposito FROM omicron_ventas1 v "\
		"LEFT JOIN articulo a ON v.articulo=a.codigo "\
		"LEFT JOIN marcas m ON a.marca=m.codigo "\
		"LEFT JOIN subrubro s ON a.subrubro=s.codigo "\
		"WHERE v.codigo<>7 AND v.fecha>='%s' AND v.fecha<='%s'"%(kwargs['desde'], kwargs['hasta'])\
		+ filtros +\
		"GROUP BY a.marca, m.descripcion, v.deposito"



	data=db1.executesql(t_sql)

	return data

#USA VISTA CONSOLIDADA: dbo.omicron_compras1_remitos 12/12/18
# def get_compras_consolidado(desde,hasta,linea,marca,rubro,subrubro,agrupador, agrupador_subrubro, agrupador_rubro, sinonimo):
def get_compras_consolidado(**kwargs):	

	filtros = fx_filtros_art(**kwargs)


	t_sql="SELECT SUM((CASE WHEN r.operacion='+' THEN r.cantidad WHEN r.operacion='-' THEN -r.cantidad END)) as items, "\
		"SUM((CASE WHEN r.operacion='+' THEN r.monto_facturado END)) AS totalcomp, "\
		"SUM((CASE WHEN r.operacion='-' THEN r.precio END)) AS totaldevs, "\
		"a.marca, m.descripcion FROM omicron_compras1_remitos r "\
		"LEFT JOIN articulo a ON r.articulo=a.codigo "\
		"LEFT JOIN marcas m ON a.marca=m.codigo "\
		"WHERE r.fecha>='%s' AND r.fecha<='%s'"%(kwargs['desde'], kwargs['hasta'])\
		+ filtros +\
		"GROUP BY a.marca, m.descripcion"

	data=db1.executesql(t_sql)	
	return data






### 19/07/22, STOCK FILTRADO PARA rank_marcas_comp_vent
#def get_stock_consolidado(lista_marcas, linea,rubro,subrubro, agrupador_rubro, agrupador_subrubro):
### 11/08/23
##depos_para_informes se define en models/tablas1.py
### Se usa en: informes_encargados_sucursal
def get_stock_consolidado(**kwargs):	

	filtros = fx_filtros_art(**kwargs)

	t_sql="SELECT SUM(ws.stock_actual), MAX(m.codigo), MAX(ws.deposito) FROM articulo a "\
		"LEFT JOIN web_stock ws ON ws.articulo=a.codigo "\
		"LEFT JOIN marcas m on m.codigo=a.marca "\
		"WHERE a.marca>0 AND ws.deposito in {0} ".format(depos_para_informes)\
		+ filtros +\
		"GROUP BY a.marca, ws.deposito"

	print t_sql

	data = db1.executesql(t_sql)

	return data


## Datos para Tabulator
#Devuelve: Unidades compradas, total compras sin iva, total devoluciones sin iva,codigo de marca, descripcion de marca
# @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('admins')))
#def get_compras_consolidado_xmarca(desde,hasta,linea,marca,rubro,subrubro, agrupador_subrubro, agrupador_rubro, sinonimo):
def get_compras_consolidado_xmarca(**kwargs):	


	filtros = fx_filtros_art(**kwargs)
	
	t_sql = "SELECT SUM((CASE WHEN rc.operacion='+' THEN rc.cantidad WHEN rc.operacion='-' THEN -rc.cantidad END)) as items, "\
		"SUM((CASE WHEN rc.operacion='+' THEN rc.monto_facturado END)) AS totalcomp, "\
		"SUM((CASE WHEN rc.operacion='-' THEN rc.precio END)) AS totaldevs, "\
		"LEFT(a.codigo_sinonimo,10) as csr "\
		"FROM omicron_compras1_remitos rc "\
		"LEFT JOIN articulo a ON rc.articulo=a.codigo "\
		"LEFT JOIN marcas m ON a.marca=m.codigo "\
		"LEFT JOIN subrubro s ON a.subrubro=s.codigo "\
		"LEFT JOIN rubros r ON a.rubro=r.codigo "\
		"WHERE rc.fecha>='%s' AND rc.fecha<='%s' "%(kwargs['c_desde'],kwargs['c_hasta'])\
		+ filtros +\
		"GROUP BY left(a.codigo_sinonimo,10)"




	data=db1.executesql(t_sql)		

	return data	


### MODIFICADA 17/01/23 PARA OBTENER RENTABILIDAD DE VENTA, SE CALCULA EN LA FUNCION PRINCIPAL
#Devuelve: Unidades vendidas, total ventas sin iva, total devoluciones sin iva,codigo de marca, descripcion de marca

# @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('admins')))
def get_ventas_consolidado_xmarca(**kwargs):

	
	filtros = fx_filtros_art(**kwargs)

	t_sql = "SELECT SUM((CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END)) as items, "\
		"SUM((case when v.operacion='+' then v.precio when v.operacion='-' then -v.precio end) / 1.21 * v.cantidad)  AS totalvent, "\
		"SUM(case when v.operacion='+' then v.precio_costo when v.operacion='-' then -v.precio_costo end * v.cantidad) as costovent, "\
		"LEFT(a.codigo_sinonimo,10) as csr "\
		"FROM omicron_ventas1 v "\
		"LEFT JOIN articulo a ON v.articulo=a.codigo "\
		"LEFT JOIN marcas m ON a.marca=m.codigo "\
		"LEFT JOIN subrubro s ON a.subrubro=s.codigo "\
		"LEFT JOIN rubros r ON a.rubro=r.codigo "\
		"WHERE v.codigo<>7 AND v.fecha>='%s' AND v.fecha<='%s' "%(kwargs['v_desde'], kwargs['v_hasta'])\
		+ filtros +\
		"GROUP BY left(a.codigo_sinonimo,10)"

	data=db1.executesql(t_sql)

	return data

### PID-221
##depos_para_informes se define en models/tablas1.py
def get_stock_consolidado_xmarca(**kwargs):

	filtros = fx_filtros_art(**kwargs)

	t_sql="SELECT SUM(s.stock_actual), s.deposito, a.csr "\
		"FROM omicron_articulos a "\
		"LEFT JOIN web_stock s ON a.codigo=s.articulo "\
		"WHERE a.marca=%s AND s.deposito in %s "%(kwargs['marca'], depos_para_informes)\
		+ filtros +\
		"GROUP BY s.deposito, csr"
		#"GROUP BY s.deposito, csr HAVING SUM(s.stock_actual)>0"

	print ' '
	print '-------------------------------------------------------------------------------------'
	print 'get_stock_consolidado_xmarca'
	print t_sql

	data=db1.executesql(t_sql)

	return data







def get_distrib_ventas_xmarca(**kwargs):

	filtros = fx_filtros_art(**kwargs)

	t_sql = "SELECT SUM((CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END)), v.deposito, left(a.codigo_sinonimo, len(a.codigo_sinonimo)-2) "\
		"FROM web_articulo a "\
		"LEFT JOIN omicron_ventas1 v ON a.codigo=v.articulo "\
		"WHERE LEN(a.codigo_sinonimo)=12 AND a.marca=%s "%kwargs['marca']\
		+ filtros +\
		"GROUP BY v.deposito, left(a.codigo_sinonimo, len(a.codigo_sinonimo)-2)"

	data=db1.executesql(t_sql)

	return data


########## DATA PARA GRAFICOS DE : informes_consolidados/rank_productos_xmarca   ################################################################################################################################

# @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('admins')))
# def get_compras_consolidado_xmarca_graf_anmes(linea,marca,rubro,subrubro, agrupador_subrubro):
def get_compras_consolidado_xmarca_graf_anmes(**kwargs):

	
	filtros = fx_filtros_art(**kwargs)

	data=db1.executesql("SELECT SUM((CASE WHEN rc.operacion='+' THEN rc.cantidad WHEN rc.operacion='-' THEN -rc.cantidad END)) as items, "\
		"CONCAT(DATEPART(YEAR, rc.fecha),'-',CONVERT(char(2), rc.fecha,101)) AS anmes, "\
		"DATEPART(YEAR, rc.fecha) AS an, DATEPART(MONTH, rc.fecha) as me "\
		"FROM omicron_compras1_remitos rc "\
		"LEFT JOIN articulo a ON rc.articulo=a.codigo "\
		"LEFT JOIN marcas m ON a.marca=m.codigo "\
		"WHERE a.codigo>1 "\
		+ filtros +\
		"GROUP BY CONCAT(DATEPART(YEAR, rc.fecha),'-',CONVERT(char(2), rc.fecha,101)), "\
		"DATEPART(YEAR, rc.fecha), DATEPART(MONTH, rc.fecha)")		

	return data	
#Devuelve: Unidades vendidas, total ventas sin iva, total devoluciones sin iva,codigo de marca, descripcion de marca

# @auth.requires_membership('usuarios_nivel_1')
def get_ventas_consolidado_xmarca_graf_anmes(**kwargs):

	filtros = fx_filtros_art(**kwargs)

	data=db1.executesql("SELECT SUM((CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END)) as items, "\
		"CONCAT(DATEPART(YEAR, v.fecha),'-',CONVERT(char(2), v.fecha,101)) AS anmes, "\
		"DATEPART(YEAR, v.fecha) AS an, DATEPART(MONTH, v.fecha) as me "\
		"FROM omicron_ventas1 v "\
		"LEFT JOIN articulo a ON v.articulo=a.codigo "\
		"LEFT JOIN marcas m ON a.marca=m.codigo "\
		"WHERE v.codigo<>7 "\
		+ filtros +\
		"GROUP BY CONCAT(DATEPART(YEAR, v.fecha),'-',CONVERT(char(2), v.fecha,101)), "\
		"DATEPART(YEAR, v.fecha), DATEPART(MONTH, v.fecha)")
	return data

# @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('admins')))
def get_compras_consolidado_xmarca_graf_mes(**kwargs):

	filtros = fx_filtros_art(**kwargs)
	
	data=db1.executesql("SELECT SUM((CASE WHEN rc.operacion='+' THEN rc.cantidad WHEN rc.operacion='-' THEN -rc.cantidad END)) as items, "\
		"CONVERT(char(2), rc.fecha,101) AS mes "\
		"FROM omicron_compras1_remitos rc "\
		"LEFT JOIN articulo a ON rc.articulo=a.codigo "\
		"LEFT JOIN marcas m ON a.marca=m.codigo "\
		"WHERE a.codigo>1 "\
		+ filtros +\
		"GROUP BY CONVERT(char(2), rc.fecha,101) "\
		"ORDER BY 2")		
	return data
#Devuelve: Unidades vendidas, total ventas sin iva, total devoluciones sin iva,codigo de marca, descripcion de marca

# @auth.requires_membership('usuarios_nivel_1')
def get_ventas_consolidado_xmarca_graf_mes(**kwargs):

	filtros = fx_filtros_art(**kwargs)

	t_sql = "SELECT CAST(SUM(i.items) AS INT) AS items, i.mes AS mes, CAST(SUM(i.items)/COUNT(i.yeames) AS INT) as promedio FROM "\
		"(SELECT SUM((CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END)) as items, "\
		"CONCAT(YEAR(fecha),'-',MONTH(fecha)) as yeames, MAX(CONVERT(char(2), v.fecha,101)) as mes "\
		"FROM omicron_ventas1 v "\
		"LEFT JOIN articulo a ON v.articulo=a.codigo "\
		"LEFT JOIN marcas m ON a.marca=m.codigo "\
		"WHERE v.codigo<>7 "\
		+ filtros +\
		"GROUP BY CONCAT(YEAR(fecha),'-',MONTH(fecha))) i "\
		"GROUP BY (i.mes)"

	data = db1.executesql(t_sql)

	return data
		



#retorna las compras por curva de un producto
# @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('admins')))
def get_compras_curva_producto(desde,hasta,csr):
	data=db1.executesql("SELECT SUM((CASE WHEN omicron_compras1_remitos.operacion='+' THEN omicron_compras1_remitos.cantidad WHEN omicron_compras1_remitos.operacion='-' THEN -omicron_compras1_remitos.cantidad END)) as items, "\
			"SUM((CASE WHEN omicron_compras1_remitos.operacion='+' THEN omicron_compras1_remitos.monto_facturado END)) AS totalcomp, "\
			"SUM((CASE WHEN omicron_compras1_remitos.operacion='-' THEN omicron_compras1_remitos.precio END)) AS totaldevs, "\
			"articulo.codigo_sinonimo, articulo.descripcion_5, "\
			"omicron_compras1_remitos.fecha "\
			"FROM omicron_compras1_remitos "\
			"LEFT JOIN articulo ON omicron_compras1_remitos.articulo=articulo.codigo "\
			"LEFT JOIN marcas ON articulo.marca=marcas.codigo "\
			"WHERE omicron_compras1_remitos.fecha>='%s' AND omicron_compras1_remitos.fecha<='%s' AND articulo.codigo_sinonimo like '%s' "\
			"GROUP BY articulo.descripcion_5, articulo.codigo_sinonimo, omicron_compras1_remitos.fecha"%(desde,hasta,csr+'%'))
	return data

#retorna las ventas por curva de un producto
# @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('admins')))
def get_ventas_curva_producto(desde,hasta,csr):
	data=db1.executesql("SELECT SUM((CASE WHEN omicron_ventas1.operacion='+' THEN omicron_ventas1.cantidad WHEN omicron_ventas1.operacion='-' THEN -omicron_ventas1.cantidad END)) as items, "\
			"SUM((CASE WHEN omicron_ventas1.operacion='+' THEN omicron_ventas1.monto_facturado END) / 1.21) AS totalcomp, "\
			"SUM((CASE WHEN omicron_ventas1.operacion='-' THEN omicron_ventas1.precio END) / 1.21) AS totaldevs, "\
			"articulo.codigo_sinonimo, articulo.descripcion_5, "\
			"omicron_ventas1.fecha "\
			"FROM omicron_ventas1 "\
			"LEFT JOIN articulo ON omicron_ventas1.articulo=articulo.codigo "\
			"LEFT JOIN marcas ON articulo.marca=marcas.codigo "\
			"WHERE omicron_ventas1.codigo<>7 AND omicron_ventas1.fecha>='%s' AND omicron_ventas1.fecha<='%s' AND articulo.codigo_sinonimo like '%s' "\
			"GROUP BY articulo.descripcion_5, articulo.codigo_sinonimo, omicron_ventas1.fecha"%(desde,hasta,csr+'%'))
	return data


################ DATOS PARA GRAFICO ############################################################################################################################################################################
#retorna las compras por curva de un producto

# @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('admins')))
def get_compras_curva_producto_anmes(csr):
	data=db1.executesql("SELECT SUM((CASE WHEN omicron_compras1_remitos.operacion='+' THEN omicron_compras1_remitos.cantidad WHEN omicron_compras1_remitos.operacion='-' THEN -omicron_compras1_remitos.cantidad END)) as items, "\
			"CONCAT(DATEPART(YEAR, omicron_compras1_remitos.fecha),'-',CONVERT(char(2),omicron_compras1_remitos.fecha,101)) AS anmes "\
			"FROM omicron_compras1_remitos "\
			"LEFT JOIN articulo ON omicron_compras1_remitos.articulo=articulo.codigo "\
			"WHERE articulo.codigo_sinonimo like '%s' "\
			"GROUP BY CONCAT(DATEPART(YEAR, omicron_compras1_remitos.fecha),'-',CONVERT(char(2),omicron_compras1_remitos.fecha,101)) "\
			"ORDER BY 2"%(csr+'%'))
	return data

#retorna las ventas por curva de un producto
# @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('admins')))
def get_ventas_curva_producto_anmes(csr):
	data=db1.executesql("SELECT SUM((CASE WHEN omicron_ventas1.operacion='+' THEN omicron_ventas1.cantidad WHEN omicron_ventas1.operacion='-' THEN -omicron_ventas1.cantidad END)) as items, "\
			"CONCAT(DATEPART(YEAR, omicron_ventas1.fecha),'-',CONVERT(char(2),omicron_ventas1.fecha,101)) AS anmes "\
			"FROM omicron_ventas1 "\
			"LEFT JOIN articulo ON omicron_ventas1.articulo=articulo.codigo "\
			"WHERE omicron_ventas1.codigo<>7 AND articulo.codigo_sinonimo like '%s' "\
			"GROUP BY CONCAT(DATEPART(YEAR, omicron_ventas1.fecha),'-',CONVERT(char(2),omicron_ventas1.fecha,101)) "\
			"ORDER BY 2"%(csr+'%'))
	return data
#retorna las compras por curva de un producto

# @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('admins')))
def get_compras_curva_producto_mes(csr):
	data=db1.executesql("SELECT SUM((CASE WHEN omicron_compras1_remitos.operacion='+' THEN omicron_compras1_remitos.cantidad WHEN omicron_compras1_remitos.operacion='-' THEN -omicron_compras1_remitos.cantidad END)) as items, "\
			"CONVERT(char(2),omicron_compras1_remitos.fecha,101) AS mes "\
			"FROM omicron_compras1_remitos "\
			"LEFT JOIN articulo ON omicron_compras1_remitos.articulo=articulo.codigo "\
			"WHERE articulo.codigo_sinonimo like '%s' "\
			"GROUP BY CONVERT(char(2),omicron_compras1_remitos.fecha,101) "\
			"ORDER BY 2"%(csr+'%'))
	return data

#retorna las ventas por curva de un producto
# @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('admins')))
def get_ventas_curva_producto_mes(csr):
	# t_sql = "SELECT SUM((CASE WHEN omicron_ventas1.operacion='+' THEN omicron_ventas1.cantidad WHEN omicron_ventas1.operacion='-' THEN -omicron_ventas1.cantidad END)) as items, "\
	# 		"CONVERT(char(2),omicron_ventas1.fecha,101) AS mes "\
	# 		"FROM omicron_ventas1 "\
	# 		"LEFT JOIN articulo ON omicron_ventas1.articulo=articulo.codigo "\
	# 		"WHERE omicron_ventas1.codigo<>7 AND articulo.codigo_sinonimo like '%s' "\
	# 		"GROUP BY CONVERT(char(2),omicron_ventas1.fecha,101) "\
	# 		"ORDER BY 2"%(csr+'%')

	t_sql = """
		SELECT 
		    CAST(SUM(i.items) AS INT) AS items,
		    i.mes,
		    CAST(SUM(i.items) / COUNT(i.yeames) AS INT) AS promedio
		FROM (
		    SELECT 
		        SUM(CASE 
		                WHEN v.operacion = '+' THEN v.cantidad 
		                WHEN v.operacion = '-' THEN -v.cantidad 
		            END) AS items,
		        CONCAT(YEAR(v.fecha), '-', MONTH(v.fecha)) AS yeames,
		        CONVERT(CHAR(2), v.fecha, 101) AS mes
		    FROM omicron_ventas1 v
		    LEFT JOIN articulo a ON v.articulo = a.codigo
		    WHERE v.codigo <> 7 AND a.codigo_sinonimo LIKE '%s'
		    GROUP BY CONCAT(YEAR(v.fecha), '-', MONTH(v.fecha)), CONVERT(CHAR(2), v.fecha, 101)
		) i
		GROUP BY i.mes
		ORDER BY i.mes
		""" % (csr + '%')

	data = db1.executesql(t_sql)

	return data	

#funcion para calcular temporas de ventas
def season_calc(mes,yea,tipo):
	if tipo==0:
		if mes in (2,3,4,5,6):
			season='%s-INV'%yea
		elif mes in (7,8,9,10,11,12):
			season='%s-VER'%yea
		elif mes==1:
			season='%s-VER'%(yea-1)
	elif tipo==1:
		if mes in (3,4,5,6,7,8):
			season='%s-INV'%yea
		elif mes in (9,10,11,12):
			season='%s-VER'%yea
		elif mes in (1,2):
			season='%s-VER'%(yea-1)
	return season

#retorna solo ventas de un depo determinado en un período y marca determinados y su historial para años anteriores
# @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('encargados_sucursal')))
def get_ventas_depo_histo_marca(mon_d,day_d,mon_h,day_h,depo,marca):
	var_depo="AND omicron_ventas1.deposito=%s "%depo if depo is not None else ""
	data=db1.executesql("SELECT SUM((CASE WHEN omicron_ventas1.operacion='+' THEN omicron_ventas1.cantidad WHEN omicron_ventas1.operacion='-' THEN -omicron_ventas1.cantidad END)) as items, "\
		"DATEPART(YEAR, omicron_ventas1.fecha) AS yea , LEFT(articulo.codigo_sinonimo,len(articulo.codigo_sinonimo)-2) as csr, articulo.descripcion_1, marcas.descripcion "\
		"FROM omicron_ventas1 "\
		"LEFT JOIN articulo ON omicron_ventas1.articulo=articulo.codigo "\
		"LEFT JOIN marcas ON articulo.marca=marcas.codigo "\
		"WHERE omicron_ventas1.codigo<>7 "\
		# " AND omicron_ventas1.deposito=0 "\
		+ var_depo +\
		"AND DATEPART(MONTH, omicron_ventas1.fecha)>=%s AND DATEPART(DAY, omicron_ventas1.fecha)>=%s "\
		"AND DATEPART(MONTH, omicron_ventas1.fecha)<=%s AND DATEPART(DAY, omicron_ventas1.fecha)<=%s "\
		"AND marcas.codigo=%s "\
		"GROUP BY LEFT(articulo.codigo_sinonimo,len(articulo.codigo_sinonimo)-2), articulo.descripcion_1, marcas.descripcion, DATEPART(YEAR, omicron_ventas1.fecha)"%(mon_d,day_d,mon_h,day_h,marca))
	return data


#retorna solo ventas de un depo determinado en un período y marca determinados y su historial para años anteriores
# @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('encargados_sucursal')))
def lx_get_compras_depo_histo_marca(mon_d,day_d,mon_h,day_h,depo,marca):
	var_depo="AND compras1.deposito=%s "%depo if depo is not None else ""
	data=dbC.executesql("SELECT SUM((CASE WHEN compras1.operacion='+' THEN compras1.cantidad WHEN compras1.operacion='-' THEN -compras1.cantidad END)) as items, "\
		"DATEPART(YEAR, compras1.fecha) AS yea , LEFT(articulo.codigo_sinonimo,len(articulo.codigo_sinonimo)-2) as csr, articulo.descripcion_1, marcas.descripcion "\
		"FROM compras1 "\
		"LEFT JOIN articulo ON compras1.articulo=articulo.codigo "\
		"LEFT JOIN marcas ON articulo.marca=marcas.codigo "\
		"WHERE compras1.codigo NOT IN (7,36) "\
		# " AND omicron_ventas1.deposito=0 "\
		+ var_depo +\
		"AND DATEPART(MONTH, compras1.fecha)>=%s AND DATEPART(DAY, compras1.fecha)>=%s "\
		"AND DATEPART(MONTH, compras1.fecha)<=%s AND DATEPART(DAY, compras1.fecha)<=%s "\
		"AND marcas.codigo=%s "\
		"GROUP BY LEFT(articulo.codigo_sinonimo,len(articulo.codigo_sinonimo)-2), articulo.descripcion_1, marcas.descripcion, DATEPART(YEAR, compras1.fecha)"%(mon_d,day_d,mon_h,day_h,marca))
	return data


################################# FIN DESARROLLANDO 07/06/2021 ###########################################################




def get_stock_curva(csr):
	t_sql = "SELECT SUM(web_stock.stock_actual) AS stock, articulo.codigo_sinonimo, articulo.descripcion_5 FROM web_stock LEFT JOIN articulo ON articulo.codigo=web_stock.articulo "\
			"WHERE articulo.codigo_sinonimo like '%s' AND web_stock.deposito in %s GROUP BY articulo.codigo_sinonimo, articulo.descripcion_5"%(csr+'%', depos_para_informes)

	qstock=db1.executesql(t_sql)

	print ' '
	print '-------------------------------'
	print 'get_stock_curva'
	print t_sql


	return qstock

def marca_graf_tiempo(desde,hasta,marca):
	data=db1.executesql("")
	return data


def func_grafico_1(**kwargs):
	#GRAFICO 1
	dam=pandas.DataFrame.from_records(get_compras_consolidado_xmarca_graf_anmes(**kwargs),columns=['cantidad_c','anmes','an','me'])#datos de compras
	damm=dam[['anmes','cantidad_c']]#cambio orden de las columnas de compras
	dav=pandas.DataFrame.from_records(get_ventas_consolidado_xmarca_graf_anmes(**kwargs),columns=['cantidad_v','anmes','an','me'])#datos de ventas
	davm=dav[['anmes','cantidad_v']]#cambio orden de las columnas de venta
	dat=pandas.merge(damm,davm, on=['anmes'], how='outer')#junto los 2 dfs
	dat['cantidad_c']=dat['cantidad_c'].astype(float).round(2)
	dat['cantidad_v']=dat['cantidad_v'].astype(float).round(2)
	serie_compras={'name':'Compras'}#creo la serie de compras
	xcl=dat[['anmes','cantidad_c']].sort_values('anmes').values.tolist()#solo las compras, ordeno por anmes y convierto a lista
	serie_compras['data']=xcl#armo los datos de la serie
	hc_datos=[serie_compras]#junto nombre y datos
	serie_ventas={'name':'Ventas'}#creo la serie de ventas
	xvl=dat[['anmes','cantidad_v']].sort_values('anmes').values.tolist()#solo las ventas, ordeno por anmes y convierto a lista
	serie_ventas['data']=xvl#armo los datos de la serie
	hc_datos.append(serie_ventas)#los agrego a las compras
	hc_graf=json.dumps(hc_datos, default=str)#default=str para que no de error serializando datetime
	return hc_graf

def func_grafico_3(**kwargs):		
	#GRAFICO 3
	#----------------- compras -----------------------------------
	dfc3=pandas.DataFrame.from_records(get_compras_consolidado_xmarca_graf_anmes(**kwargs),columns=['cantidad','anmes','an','me'])#datos de compras
	dfc3['temp']=dfc3.apply(lambda x : season_calc(x['me'],x['an'],0), axis=1)#busco las compras historicas por temporada para cada producto
	dfc3=dfc3[['temp','cantidad']]#cambio orden de las columnas de compras
	dfc3['cantidad']=dfc3['cantidad'].astype(float).round(2)#si no tira error en windows
	dfc3=dfc3.groupby(['temp'], as_index=False).sum()#agrupo compras por temporada
	serie_compras3={'name':'Compras'}#creo la serie de compras
	xcl=dfc3[['temp','cantidad']].sort_values('temp').values.tolist()#solo las compras, ordeno por anmes y convierto a lista
	serie_compras3['data']=xcl#armo los datos de la serie
	#----------------- ventas ------------------------------------
	dfv3=pandas.DataFrame.from_records(get_ventas_consolidado_xmarca_graf_anmes(**kwargs),columns=['cantidad','anmes','an','me'])#datos de ventas
	dfv3['temp']=dfv3.apply(lambda x : season_calc(x['me'],x['an'],1), axis=1)
	dfv3=dfv3[['temp','cantidad']]#cambio orden de las columnas de venta
	dfv3['cantidad']=dfv3['cantidad'].astype(float).round(2)#si no tira error en windows
	dfv3=dfv3.groupby(['temp'], as_index=False).sum()#agrupo compras por temporada
	serie_ventas3={'name':'Ventas'}#creo la serie de ventas
	xvl=dfv3[['temp','cantidad']].sort_values('temp').values.tolist()#solo las ventas, ordeno por anmes y convierto a lista
	serie_ventas3['data']=xvl#armo los datos de la serie	
	#---------- junto y convierto a json --------------------
	hc_datos3=[serie_compras3]#junto nombre y datos, compras
	hc_datos3.append(serie_ventas3)#agrego las ventas
	hc_graf3=json.dumps(hc_datos3, default=str)#default=str para que no de error serializando datetime
	return hc_graf3

def func_grafico_2(**kwargs):

	#try:
	#DATOS PARA GRAFICO 2
	dm=pandas.DataFrame.from_records(get_compras_consolidado_xmarca_graf_mes(**kwargs),columns=['cantidad_c','mes',])#traigo las compras
	dm=dm[['mes','cantidad_c']]#cambio el orden de las columnas de compras

	dv=pandas.DataFrame.from_records(get_ventas_consolidado_xmarca_graf_mes(**kwargs),columns=['cantidad_v','mes','promedio_v'])#traigo las ventas
	dv=dv[['mes','cantidad_v','promedio_v']]#cambio el orden de las columnas de ventas	
	dv['prom_gral_v'] = dv['cantidad_v'].mean()
	dv['prom_mensual_gral_v'] = dv['promedio_v'].mean()

	dt=pandas.merge(dm, dv, on=['mes'], how='outer')#junto los dos dfs
	dt['cantidad_c']=dt['cantidad_c'].astype(float).round(2)
	dt['cantidad_v']=dt['cantidad_v'].astype(float).round(2)
	
	serie_compras2={'name':'Compras'}#creo la serie de compras
	xcl=dt[['mes','cantidad_c']].sort_values('mes').values.tolist()#solo los datos de compra, los ordeno por mes y los convierto a lista.
	serie_compras2['data']=xcl#agrego la lista a la serie de compras
	serie_compras2['type']='column'
	hc_datos2=[serie_compras2]#junto nombre y datos

	serie_ventas2={'name':'Ventas'}#creo la serie con nombre
	xvl=dt[['mes','cantidad_v']].values.tolist()#convierto a lista
	serie_ventas2['data']=xvl#armo los datos de la 
	serie_ventas2['type']='column'
	hc_datos2.append(serie_ventas2)#los agrego a las compras
	
	serie_prom_gral2={'name':'Media Venta Total Gral'}
	xgl = dt[['mes','prom_gral_v']].values.tolist()#convierto a lista
	serie_prom_gral2['type'] = 'line'
	serie_prom_gral2['data'] = xgl
	hc_datos2.append(serie_prom_gral2)#los agrego a las compras

	serie_promedio2={'name':'Venta Promedio Mensual'}#creo la serie con nombre
	xpl = dt[['mes','promedio_v']].values.tolist()#convierto a lista
	serie_promedio2['type']='column'
	serie_promedio2['data']=xpl#armo los datos de la serie
	hc_datos2.append(serie_promedio2)#los agrego a las compras

	serie_prom_mensual_gral2={'name':'Media Venta Mensual Gral'}
	xml = dt[['mes','prom_mensual_gral_v']].values.tolist()#convierto a lista
	serie_prom_mensual_gral2['type'] = 'line'
	serie_prom_mensual_gral2['data'] = xml
	hc_datos2.append(serie_prom_mensual_gral2)#los agrego a las compras
	# except:
	# 	hc_datos2 = []


	hc_graf2=json.dumps(hc_datos2, default=str)#default=str para que no de error serializando datetime
	return hc_graf2



#############################################################
### GRAFICO 4 - PONDERADOS POR SUBRUBRO #####################
### Compras

# def gr_pond_subrubro_global(vd,vh,ln,mc,rb,sr,agrupador, agrupador_subrubro, agrupador_rubro):
### Se usa en informes_encargados_sucursal
def gr_pond_subrubro_global(**kwargs):

	filtros = fx_filtros_art(**kwargs)

	t_sql_compras="SELECT SUM((CASE WHEN rc.operacion='+' THEN rc.cantidad WHEN rc.operacion='-' THEN -rc.cantidad END)) as items, "\
		"SUM((CASE WHEN rc.operacion='+' THEN rc.monto_facturado END)) AS totalcomp, "\
		"SUM((CASE WHEN rc.operacion='-' THEN rc.precio END)) AS totaldevs, "\
		"a.subrubro, s.descripcion FROM omicron_compras1_remitos rc "\
		"LEFT JOIN articulo a ON rc.articulo=a.codigo "\
		"LEFT JOIN subrubro s ON a.subrubro=s.codigo "\
		"WHERE rc.fecha>='%s' AND rc.fecha<='%s'"%(kwargs['c_desde'],kwargs['c_hasta'])\
		+ filtros +\
	 	"GROUP BY a.subrubro, s.descripcion "

	t_sql_ventas="SELECT SUM((CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END)) as items, "\
		"SUM((CASE WHEN v.operacion='+' THEN v.monto_facturado END) / 1.21) AS totalvent, "\
		"SUM((CASE WHEN v.operacion='-' THEN v.precio END) / 1.21) AS totaldevs, "\
		"a.subrubro, s.descripcion, SUM(ws.stock_actual) FROM omicron_ventas1 v "\
		"LEFT JOIN articulo a ON v.articulo=a.codigo "\
		"LEFT JOIN subrubro s ON a.subrubro=s.codigo "\
		"LEFT JOIN web_stock ws ON a.codigo=ws.articulo "\
		"WHERE v.codigo<>7 AND v.fecha>='%s' AND v.fecha<='%s'"%(kwargs['v_desde'],kwargs['v_hasta'])\
		+  filtros +\
		"GROUP BY a.subrubro, s.descripcion"

	#busco la data por : desde,hasta,linea,marca
	query_compras=db1.executesql(t_sql_compras)
	for row in query_compras:#reemplazo valores vacíos por 0
		row[1]=0 if row[1]==None else row[1]
		row[2]=0 if row[2]==None else row[2]
	#armo un DF de compras
	dfc=pandas.DataFrame.from_records(query_compras,columns=['cantidad_c','subtotal_c','subtotal_devs_c','subrubro', 'subrubro_descrip_c'])
	dfc['total_c']=dfc['subtotal_c']-dfc['subtotal_devs_c']
	dfc['ppp_c']=dfc['total_c'].astype(float)/dfc['cantidad_c'].astype(float)	

	#
	query_ventas=db1.executesql(t_sql_ventas)
	for row in query_ventas:#reemplazo valores vacíos por 0
		row[1]=0 if row[1]==None else row[1]
		row[2]=0 if row[2]==None else row[2]
	#armo un DF de ventas
	dfv=pandas.DataFrame.from_records(query_ventas,columns=['cantidad_v','subtotal_v','subtotal_devs_v','subrubro', 'subrubro_descrip_v','stock_actual'])		
	dfv['total_v']=dfv['subtotal_v']-dfv['subtotal_devs_v']
	dfv['ppp_v']=dfv['total_v'].astype(float)/dfv['cantidad_v'].astype(float)

	#junto los 2 dfs
	datos = pandas.merge(dfc, dfv, on=['subrubro'], how='outer')

	datos['subrubro_descrip']=datos['subrubro_descrip_v'].fillna(datos['subrubro_descrip_c'])

	df_pond_compra=datos[['cantidad_c','subrubro','subrubro_descrip']].copy()
	df_pond_compra['cantidad_c']=df_pond_compra['cantidad_c'].astype(float)
	df_pond_compra=df_pond_compra.groupby(['subrubro_descrip']).sum().reset_index()
	df_pond_compra['pond'] = ((df_pond_compra['cantidad_c']/df_pond_compra['cantidad_c'].sum())*100).round(2)
	#serie compras
	serie_pond_subr_compras={'name':'Compras'}
	#convierto el df compras a lista y lo pongo en el dict como data
	serie_pond_subr_compras['data']=df_pond_compra[['subrubro_descrip','pond']].values.tolist()

	### Ventas
	df_pond_venta=datos[['cantidad_v','subrubro','subrubro_descrip']].copy()
	df_pond_venta['cantidad_v']=df_pond_venta['cantidad_v'].astype(float)
	df_pond_venta=df_pond_venta.groupby(['subrubro_descrip']).sum().reset_index()
	df_pond_venta['pond'] = ((df_pond_venta['cantidad_v']/df_pond_venta['cantidad_v'].sum())*100).round(2)
	#serie ventas
	serie_pond_subr_ventas={'name':'Ventas'}
	#convierto el df ventas a lista y lo pongo en el dict como data
	serie_pond_subr_ventas['data']=df_pond_venta[['subrubro_descrip','pond']].values.tolist()

	### Stock actual
	df_pond_stock=datos[['stock_actual','subrubro','subrubro_descrip']].copy()
	df_pond_stock['stock_actual']=df_pond_stock['stock_actual'].astype(float)
	df_pond_stock=df_pond_stock.groupby(['subrubro_descrip']).sum().reset_index()
	df_pond_stock['pond'] = ((df_pond_stock['stock_actual']/df_pond_stock['stock_actual'].sum())*100).round(2)	
	#serie stock
	serie_pond_subr_stock={'name':'Stock actual'}
	#convierto el df stock a lista y lo pongo en el dict como data
	serie_pond_subr_stock['data']=df_pond_stock[['subrubro_descrip','pond']].values.tolist()


	#meto la data de compras en un dict
	hc_datos4=[serie_pond_subr_compras]
	#le agrego la data de ventas
	hc_datos4.append(serie_pond_subr_ventas)
	#le agrego la data de stock actual
	hc_datos4.append(serie_pond_subr_stock)

	#tiro la data para el graf de highcharts
	hc_graf4=json.dumps(hc_datos4, default=str)

	return hc_graf4
	# ### FIN GRAFICO 4 ###########################################
	# #############################################################


	#############################################################
### GRAFICO 5 - PONDERADOS POR RUBRO #####################
### Compras

# def gr_pond_subrubro_global(vd,vh,ln,mc,rb,sr,agrupador, agrupador_subrubro, agrupador_rubro):
### Se usa en informes_encargados_sucursal
def gr_pond_rubro_global(**kwargs):

	filtros = fx_filtros_art(**kwargs)

	t_sql_compras="SELECT SUM((CASE WHEN rc.operacion='+' THEN rc.cantidad WHEN rc.operacion='-' THEN -rc.cantidad END)) as items, "\
		"SUM((CASE WHEN rc.operacion='+' THEN rc.monto_facturado END)) AS totalcomp, "\
		"SUM((CASE WHEN rc.operacion='-' THEN rc.precio END)) AS totaldevs, "\
		"a.rubro, r.descripcion FROM omicron_compras1_remitos rc "\
		"LEFT JOIN articulo a ON rc.articulo=a.codigo "\
		"LEFT JOIN rubros r ON a.rubro=r.codigo "\
		"WHERE rc.fecha>='%s' AND rc.fecha<='%s'"%(kwargs['c_desde'],kwargs['c_hasta'])\
		+ filtros +\
	 	"GROUP BY a.rubro, r.descripcion "

	t_sql_ventas="SELECT SUM((CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END)) as items, "\
		"SUM((CASE WHEN v.operacion='+' THEN v.monto_facturado END) / 1.21) AS totalvent, "\
		"SUM((CASE WHEN v.operacion='-' THEN v.precio END) / 1.21) AS totaldevs, "\
		"a.rubro, r.descripcion, SUM(ws.stock_actual) FROM omicron_ventas1 v "\
		"LEFT JOIN articulo a ON v.articulo=a.codigo "\
		"LEFT JOIN rubros r ON a.rubro=r.codigo "\
		"LEFT JOIN web_stock ws ON a.codigo=ws.articulo "\
		"WHERE v.codigo<>7 AND v.fecha>='%s' AND v.fecha<='%s'"%(kwargs['v_desde'],kwargs['v_hasta'])\
		+ filtros +\
		"GROUP BY a.rubro, r.descripcion"

	#busco la data por : desde,hasta,linea,marca
	query_compras=db1.executesql(t_sql_compras)
	for row in query_compras:#reemplazo valores vacíos por 0
		row[1]=0 if row[1]==None else row[1]
		row[2]=0 if row[2]==None else row[2]
	#armo un DF de compras
	dfc=pandas.DataFrame.from_records(query_compras,columns=['cantidad_c','subtotal_c','subtotal_devs_c','subrubro', 'subrubro_descrip_c'])
	dfc['total_c']=dfc['subtotal_c']-dfc['subtotal_devs_c']
	dfc['ppp_c']=dfc['total_c'].astype(float)/dfc['cantidad_c'].astype(float)	

	#
	query_ventas=db1.executesql(t_sql_ventas)
	for row in query_ventas:#reemplazo valores vacíos por 0
		row[1]=0 if row[1]==None else row[1]
		row[2]=0 if row[2]==None else row[2]
	#armo un DF de ventas
	dfv=pandas.DataFrame.from_records(query_ventas,columns=['cantidad_v','subtotal_v','subtotal_devs_v','subrubro', 'subrubro_descrip_v','stock_actual'])		
	dfv['total_v']=dfv['subtotal_v']-dfv['subtotal_devs_v']
	dfv['ppp_v']=dfv['total_v'].astype(float)/dfv['cantidad_v'].astype(float)

	#junto los 2 dfs
	datos = pandas.merge(dfc, dfv, on=['subrubro'], how='outer')

	datos['subrubro_descrip']=datos['subrubro_descrip_v'].fillna(datos['subrubro_descrip_c'])

	df_pond_compra=datos[['cantidad_c','subrubro','subrubro_descrip']].copy()
	df_pond_compra['cantidad_c']=df_pond_compra['cantidad_c'].astype(float)
	df_pond_compra=df_pond_compra.groupby(['subrubro_descrip']).sum().reset_index()
	df_pond_compra['pond'] = ((df_pond_compra['cantidad_c']/df_pond_compra['cantidad_c'].sum())*100).round(2)
	#serie compras
	serie_pond_subr_compras={'name':'Compras'}
	#convierto el df compras a lista y lo pongo en el dict como data
	serie_pond_subr_compras['data']=df_pond_compra[['subrubro_descrip','pond']].values.tolist()

	### Ventas
	df_pond_venta=datos[['cantidad_v','subrubro','subrubro_descrip']].copy()
	df_pond_venta['cantidad_v']=df_pond_venta['cantidad_v'].astype(float)
	df_pond_venta=df_pond_venta.groupby(['subrubro_descrip']).sum().reset_index()
	df_pond_venta['pond'] = ((df_pond_venta['cantidad_v']/df_pond_venta['cantidad_v'].sum())*100).round(2)
	#serie ventas
	serie_pond_subr_ventas={'name':'Ventas'}
	#convierto el df ventas a lista y lo pongo en el dict como data
	serie_pond_subr_ventas['data']=df_pond_venta[['subrubro_descrip','pond']].values.tolist()

	### Stock actual
	df_pond_stock=datos[['stock_actual','subrubro','subrubro_descrip']].copy()
	df_pond_stock['stock_actual']=df_pond_stock['stock_actual'].astype(float)
	df_pond_stock=df_pond_stock.groupby(['subrubro_descrip']).sum().reset_index()
	df_pond_stock['pond'] = ((df_pond_stock['stock_actual']/df_pond_stock['stock_actual'].sum())*100).round(2)	
	#serie stock
	serie_pond_subr_stock={'name':'Stock actual'}
	#convierto el df stock a lista y lo pongo en el dict como data
	serie_pond_subr_stock['data']=df_pond_stock[['subrubro_descrip','pond']].values.tolist()


	#meto la data de compras en un dict
	hc_datos5=[serie_pond_subr_compras]
	#le agrego la data de ventas
	hc_datos5.append(serie_pond_subr_ventas)
	#le agrego la data de stock actual
	hc_datos5.append(serie_pond_subr_stock)

	#tiro la data para el graf de highcharts
	hc_graf5=json.dumps(hc_datos5, default=str)

	return hc_graf5
	# ### FIN GRAFICO 5 ###########################################
	# #############################################################