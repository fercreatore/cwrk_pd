# -*- coding: utf-8 -*- 
from PIL import Image

marcas_excluidas = (1316, 1317, 1158, 436)

#### 12/12/18 TODAS las compras se toman desde omicron_compras1_remitos en base a remitos de compra y devolucion

#Devuelve: Unidades compradas, total compras sin iva, total devoluciones sin iva,codigo de marca, descripcion de marca
@auth.requires_membership('usuarios_nivel_1')
def get_compras(desde,hasta):
	data=db1.executesql("SELECT SUM((CASE WHEN omicron_compras1_remitos.operacion='+' THEN omicron_compras1_remitos.cantidad WHEN omicron_compras1_remitos.operacion='-' THEN -omicron_compras1_remitos.cantidad END)) as items, "\
	"SUM((CASE WHEN omicron_compras1_remitos.operacion='+' THEN omicron_compras1_remitos.monto_facturado END) / 1.21) AS totalcomp, "\
	"SUM((CASE WHEN omicron_compras1_remitos.operacion='-' THEN omicron_compras1_remitos.precio END)) AS totaldevs, "\
	"articulo.marca, marcas.descripcion FROM omicron_compras1_remitos "\
	"LEFT JOIN articulo ON omicron_compras1_remitos.articulo=articulo.codigo "\
	"LEFT JOIN marcas ON articulo.marca=marcas.codigo "\
	"WHERE omicron_compras1_remitos.fecha>='%s' AND omicron_compras1_remitos.fecha<='%s' "\
	"GROUP BY articulo.marca, marcas.descripcion"%(desde,hasta))		
	return data

#Devuelve: Unidades vendidas, total ventas sin iva, total devoluciones sin iva,codigo de marca, descripcion de marca
@auth.requires_membership('usuarios_nivel_1')
def get_ventas(desde,hasta):
	data=dbC.executesql("SELECT SUM((CASE WHEN ventas1.operacion='+' THEN ventas1.cantidad WHEN ventas1.operacion='-' THEN -ventas1.cantidad END)) as items, "\
	"SUM((CASE WHEN ventas1.operacion='+' THEN ventas1.monto_facturado END) / 1.21) AS totalvent, "\
	"SUM((CASE WHEN ventas1.operacion='-' THEN ventas1.precio END) / 1.21) AS totaldevs, "\
	"articulo.marca, marcas.descripcion FROM ventas1 "\
	"LEFT JOIN articulo ON ventas1.articulo=articulo.codigo "\
	"LEFT JOIN marcas ON articulo.marca=marcas.codigo "\
	"WHERE ventas1.codigo<>7 AND ventas1.fecha>='%s' AND ventas1.fecha<='%s' "\
	"GROUP BY articulo.marca, marcas.descripcion"%(desde,hasta))
	return data

#Devuelve: total de unidades compradas por curva(codigo_sinonimo-2), fecha última compra, código sinónimo recortado(curva) para el período especificado,
#agrupado por curva
@auth.requires_membership('usuarios_nivel_1')
def get_uc(desde,hasta):
	data=db1.executesql("SELECT MAX(omicron_compras1_remitos.fecha) AS ultima_fecha, SUM(omicron_compras1_remitos.cantidad) AS total_compras, SUBSTRING(articulo.codigo_sinonimo,1,10) AS csr, "\
	"MAX(articulo.descripcion_1) AS descrip "\
	"FROM omicron_compras1_remitos "\
	"LEFT JOIN articulo ON articulo.codigo=omicron_compras1_remitos.articulo "\
	"WHERE omicron_compras1_remitos.fecha>='%s' AND omicron_compras1_remitos.fecha<='%s' AND omicron_compras1_remitos.operacion='+' AND SUBSTRING(articulo.codigo_sinonimo,1,10)<>'0' AND SUBSTRING(articulo.codigo_sinonimo,1,10) <>'' "\
	"GROUP BY SUBSTRING(articulo.codigo_sinonimo,1,10)"%(desde,hasta))
	return data
#Devuelve: total de ventas en el período especificado agrupado por curva(codigo_sinonimo-2)
@auth.requires_membership('usuarios_nivel_1')
def get_ventas_uc(desde, hasta):
	data=db1.executesql("SELECT SUM((CASE WHEN ventas1.operacion='+' THEN ventas1.cantidad WHEN ventas1.operacion='-' THEN -ventas1.cantidad END)) as items, "\
	"SUBSTRING(articulo.codigo_sinonimo,1,10) AS csr "\
	"FROM ventas1 "\
	"LEFT JOIN articulo ON articulo.codigo=ventas1.articulo "\
	"WHERE ventas1.codigo<>7 AND ventas1.fecha>='%s' and ventas1.fecha<='%s' AND SUBSTRING(articulo.codigo_sinonimo,1,10)<>'0' AND SUBSTRING(articulo.codigo_sinonimo,1,10) <>'' "\
	"GROUP BY SUBSTRING(articulo.codigo_sinonimo,1,10)"%(desde,hasta))
	return data


# #Devuelve: total de unidades compradas por curva(codigo_sinonimo-2), fecha última compra, código sinónimo recortado(curva) para el período especificado,
# #agrupado por curva. Usa datos consolidados
# #@auth.requires_membership('usuarios_nivel_1')
# def get_uc_2(desde):
# 	data=db1.executesql("SELECT MAX(omicron_compras1_remitos.fecha) AS ultima_fecha, SUM(omicron_compras1_remitos.cantidad) AS total_compras, SUBSTRING(articulo.codigo_sinonimo,1,10) AS csr, "\
# 	"MAX(articulo.descripcion_1) AS descrip , articulo.marca, articulo.subrubro, marcas.descripcion, subrubro.descripcion "\
# 	"FROM omicron_compras1_remitos "\
# 	"LEFT JOIN articulo ON articulo.codigo=omicron_compras1_remitos.articulo "\
# 	"LEFT JOIN marcas ON articulo.marca=marcas.codigo "\
# 	"LEFT JOIN subrubro ON articulo.subrubro=subrubro.codigo "\
# 	"WHERE omicron_compras1_remitos.fecha>='%s' AND omicron_compras1_remitos.operacion='+' AND SUBSTRING(articulo.codigo_sinonimo,1,10)<>'0' AND SUBSTRING(articulo.codigo_sinonimo,1,10) <>'' "\
# 	"GROUP BY SUBSTRING(articulo.codigo_sinonimo,1,10), articulo.marca, marcas.descripcion, articulo.subrubro, subrubro.descripcion"%(desde))
# 	return data


# #Devuelve: total de ventas en el período especificado agrupado por curva(codigo_sinonimo-2). Usa datos consolidados
# #@auth.requires_membership('usuarios_nivel_1')
# def get_ventas_uc_2(desde,codigo):
# 	data=db1.executesql("SELECT SUM((CASE WHEN omicron_ventas1.operacion='+' THEN omicron_ventas1.cantidad WHEN omicron_ventas1.operacion='-' THEN -omicron_ventas1.cantidad END)) as items "\
# 	"FROM omicron_ventas1 "\
# 	"LEFT JOIN articulo ON articulo.codigo=omicron_ventas1.articulo "\
# 	"WHERE omicron_ventas1.codigo<>7 AND omicron_ventas1.fecha>='%s' "\
# 	"AND omicron_ventas1.codigo<>7 "\
# 	"AND SUBSTRING(articulo.codigo_sinonimo,1,10)='%s'"%(desde,codigo))
# 	cantidad=float(data[0][0]) if data[0][0] is not None else 0
# 	return cantidad

# #Para informes_nuevos/ventas_x_hora
# # @auth.requires_membership('usuarios_nivel_1')
# def get_ventas_xhora(desde,hasta,sucursal):
# 	data=db1.executesql("SELECT SUM((CASE WHEN ventas1.operacion='+' THEN ventas1.monto_facturado END) / 1.21) as total_ventas, SUM((CASE WHEN ventas1.operacion='-' THEN ventas1.precio END) / 1.21) AS total_devs, "\
# 	"COUNT(distinct numero) AS tickets, MAX(DATENAME(DW,fecha_hora)) AS dia, MAX(DATEPART(DW,fecha_hora)) AS dia_num, (DATEPART(HOUR, fecha_hora) / 1) * 1 as hora, fecha "\
# 	"FROM ventas1 "\
# 	"WHERE fecha>='%s' AND fecha<='%s' AND deposito=%s AND codigo<>7 "\
# 	"GROUP BY (DATEPART(HOUR, fecha_hora) / 1) * 1, datepart(DW,fecha_hora), fecha "\
# 	"ORDER BY fecha, (DATEPART(HOUR, fecha_hora) / 1) * 1 "%(desde,hasta,sucursal))
# 	return data

###PARA MARGEN BRUTO
def calc_mb(compras,ventas):
	ven=ventas if ventas>0 else 1
	mb=(ventas-compras)/ven*100
	return mb

#Devuelve: Unidades vendidas, total ventas sin iva, total devoluciones sin iva,codigo de marca, descripcion de marca
# @auth.requires_membership('usuarios_nivel_1')
def get_ventas_xlinea(desde,hasta,linea):
	data=db1.executesql("SELECT SUM((CASE WHEN ventas1.operacion='+' THEN ventas1.cantidad WHEN ventas1.operacion='-' THEN -ventas1.cantidad END)) as items, "\
	"SUM((CASE WHEN ventas1.operacion='+' THEN ventas1.monto_facturado END) / 1.21) AS totalvent, "\
	"SUM((CASE WHEN ventas1.operacion='-' THEN ventas1.precio END) / 1.21) AS totaldevs, "\
	"articulo.marca, marcas.descripcion FROM ventas1 "\
	"LEFT JOIN articulo ON ventas1.articulo=articulo.codigo "\
	"LEFT JOIN marcas ON articulo.marca=marcas.codigo "\
	"WHERE ventas1.codigo<>7 AND ventas1.fecha>='%s' AND ventas1.fecha<='%s' AND articulo.linea='%s' "\
	"GROUP BY articulo.marca, marcas.descripcion"%(desde,hasta,linea))
	return data

@auth.requires_membership('usuarios_nivel_1')
def get_compras_xlinea(desde,hasta,linea):
	data=db1.executesql("SELECT SUM((CASE WHEN omicron_compras1_remitos.operacion='+' THEN omicron_compras1_remitos.cantidad WHEN omicron_compras1_remitos.operacion='-' THEN -omicron_compras1_remitos.cantidad END)) as items, "\
	"SUM((CASE WHEN omicron_compras1_remitos.operacion='+' THEN omicron_compras1_remitos.monto_facturado END)) AS totalcomp, "\
	"SUM((CASE WHEN omicron_compras1_remitos.operacion='-' THEN omicron_compras1_remitos.precio END) / 1.21) AS totaldevs, "\
	"articulo.marca, marcas.descripcion FROM omicron_compras1_remitos "\
	"LEFT JOIN articulo ON omicron_compras1_remitos.articulo=articulo.codigo "\
	"LEFT JOIN marcas ON articulo.marca=marcas.codigo "\
	"WHERE omicron_compras1_remitos.codigo<>7 AND omicron_compras1_remitos.fecha>='%s' AND omicron_compras1_remitos.fecha<='%s' AND articulo.linea='%s' "\
	"GROUP BY articulo.marca, marcas.descripcion"%(desde,hasta,linea))		
	return data

#retorna el stock actual consolidado de un producto buscando por 'csr'(codigo_sinonimo recortado a 10 primeros caracteres)
def get_stock(csr):
	qstock=db1.executesql("SELECT SUM(stock_actual) AS stock FROM web_stock LEFT JOIN articulo ON articulo.codigo=web_stock.articulo WHERE articulo.codigo_sinonimo like '%s'"%(csr+'%'))[0][0]
	return qstock

#### imagen para mostrar en la tabla
#### genera una miniatura de la imagen por codigo sinonimo recortadoa a 10 primeroas caracteres.
#### se usa en /informes_consolidados/rank_productos_xmarca
#### se usa en /informes_nuevos/dias_stock_fc_sf 
def get_imagen_mini(csr,codigo=None):
	#Carpeta de imagenes
	carpeta_imagenes='F:/Macroges/Imagenes/'
	#busco un codigo de producto para la curva
	try:
		if (csr>0) & (codigo is None):
			codprod=db1.executesql("select top(1) codigo from articulo where codigo_sinonimo like '%s'"%(csr+'%'))[0][0]
		elif (csr==0) & (codigo is not None):
			codprod=codigo
		#obtener el nombre de la imagen, lo encuentro con una función de macrogestion que está en la base de datos
		query=db1.executesql("SELECT dbo.f_sql_nombre_imagen (empresa, tipo,sistema,codigo,letra, sucursal ,numero,orden,renglon,extencion) AS nombre_imagen FROM imagen WHERE numero=%s AND codigo=0 AND tipo='AR' AND empresa=1 AND sistema=0"%codprod)
		# le recorto lo que no sirve, porque viene con el path completo del server
		if query:
			nombre=query[0][0].replace('\\','')[24:]
			archivo=os.path.join(carpeta_imagenes,nombre)
			#hacer una miniatura
			size = 80,100 
			try:
				img = Image.open(archivo)
				img.thumbnail(size,Image.ANTIALIAS)
				miniatura_file=os.path.join(request.folder,'static','images','thumbnails',nombre)
				img.save(miniatura_file)
				miniatura=URL('static/images/thumbnails',str(nombre))
			except IOError:
				miniatura=''
			except ValueError:
				miniatura=''
		else:
			miniatura=''
	except:
		miniatura=''
	return miniatura

def get_imagen(csr):
	#Carpeta de imagenes
	#carpeta_imagenes='F:/Macroges/Imagenes/'
	#busco un codigo de producto para la curva
	try:
		qnun=db1.executesql("select top(1) codigo from articulo where codigo_sinonimo like '%s'"%(csr+'%'))[0][0]
		#obtener el nombre de la imagen, lo encuentro con una función de macrogestion que está en la base de datos
		query=db1.executesql("SELECT dbo.f_sql_nombre_imagen (empresa, tipo,sistema,codigo,letra, sucursal ,numero,orden,renglon,extencion) AS nombre_imagen FROM imagen WHERE numero=%s AND codigo=0 AND tipo='AR' AND empresa=1 AND sistema=0"%qnun)
		# le recorto lo que no sirve, porque viene con el path completo del server
		if query:
			nombre=query[0][0].replace('\\','')[24:]
			#imagen=os.path.join(carpeta_imagenes,nombre)		
			imagen=nombre
		else:
			imagen=''
	except IndexError:
		imagen=''
	return imagen

#para calcular los turnos llamados por cada vendedor - 21/09/18
def turnos_vendedor(desde,hasta,viajante):
	query=db5.executesql("SELECT COUNT(nro) as turno from turnos where diaingreso>='%s' AND diaingreso<='%s' AND vendedor=%s"%(desde,hasta,viajante))
	return query[0][0]


# obtengo los nummax y min de la curva por CSR(codigo sinonimo_recortado)
def get_numeracion(csr):
	query=db1.executesql("SELECT MIN(descripcion_5) as min, MAX(descripcion_5) as max FROM web_articulo WHERE LEFT(codigo_sinonimo,10)='%s'"%csr)
	results='%s|%s'%(query[0][0] if query[0][0] is not None else 'ND', query[0][1] if query[0][1] is not None else 'ND') if query else 'SD|SD'
	return results	


### retorna un string en formato (v1,v2,v3) o (v1) para meter en las querys sql
def fx_list_4_sql(lista):
	res = str(tuple(lista)) if len(lista)>1 else str(tuple(lista)).replace(',','')

	return res


### filtros para informes_consolidados y algunos otros
### retorna un string para el where de algunas querys sql
def fx_filtros_art(**kwargs):
	results = ""

	results+="AND a.linea IN ({0}) ".format(kwargs['linea']) if kwargs['linea'] else ""
	results+="AND a.marca IN ({0}) ".format(kwargs['marca']) if kwargs['marca'] else ""
	results+="AND a.rubro IN ({0}) ".format(kwargs['rubro']) if kwargs['rubro'] else ""
	results+="AND a.subrubro IN ({0}) ".format(kwargs['subrubro']) if kwargs['subrubro'] else ""

	#busco agrupador de marcas
	if kwargs['agrupador_marca']>0:
		lista_marcas=db_omicronvt.executesql("SELECT marcas_codigo FROM agrupador_marca WHERE id=%s"%kwargs['agrupador_marca'])[0][0]
		results+="AND a.marca IN (%s) "%lista_marcas
	else:
		results+=""

	#busco los subrubros si hay agrupador
	if kwargs['agrupador_subrubro']>0:
		lista_subrubros=db_omicronvt.executesql("SELECT subrubros_codigo FROM agrupador_subrubro WHERE id=%s"%kwargs['agrupador_subrubro'])[0][0]
		results+="AND a.subrubro IN (%s) "%lista_subrubros
	else:
		results+=""

	#busco los subrubros si hay agrupador
	if kwargs['agrupador_rubro']>0:
		lista_rubros=db_omicronvt.executesql("SELECT rubros_codigo FROM agrupador_rubro WHERE id=%s"%kwargs['agrupador_rubro'])[0][0]
		results+="AND a.rubro IN (%s) "%lista_rubros
	else:
		results+=""			

	results+= "AND a.codigo_sinonimo LIKE '%{0}%' ".format(kwargs['sinonimo']) if kwargs['sinonimo'] else ""

	results+= "AND a.descripcion_1 LIKE '%{0}%' ".format(kwargs['descripcion']) if kwargs['descripcion'] else ""

	return results

