# -*- coding: utf-8 -*- 
import datetime, os
from operator import itemgetter
import json, pandas, numpy
from PIL import Image

## MODIFICADO 17/01/23 PARA MOSTRAR RENTABILIDAD DE VENTA
#RANKING DE MARCAS - IC0001
@auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('proveedores')) or auth.has_membership(auth.id_group('admins')))
def rank_marcas_comp_vent():
	
	datos_json=[]
	cd=ch=vd=vh=ln=mc=rb=sr=agrupador_lbl=agrupador_subrubro_lbl=linea=marca=rubro=subrubro=agrupador_rubro_lbl=hc_graf4=hc_graf5=sinonimo=descripcion=''


	if auth.has_membership('proveedores'):

		nro_proveedor = auth.user.nro_proveedor

		marcas_proveedor = db1(db1.articulo.proveedor==nro_proveedor).select(db1.articulo.marca, distinct=True)

		marcas_proveedor = [int(x['marca']) for x in marcas_proveedor]

		form = SQLFORM.factory(
			Field('compras_desde', 'date', requires=IS_DATE(), default=request.now.date()+datetime.timedelta(days=-90)),
			Field('compras_hasta', 'date', requires=IS_DATE(), default=request.now.date()),
			Field('ventas_desde', 'date', requires=IS_DATE(), default=request.now.date()+datetime.timedelta(days=-90)),
			Field('ventas_hasta', 'date', requires=IS_DATE(), default=request.now.date()),
			Field('linea', requires=IS_EMPTY_OR(IS_IN_DB(db1, 'lineas.codigo', '%(descripcion)s', multiple=True))),
			Field('marca', requires=IS_IN_DB( db1(db1.marcas.codigo.belongs(marcas_proveedor)), 'marcas.codigo', '%(descripcion)s', multiple=True, zero=None), notnull=True),
			Field('rubro', requires=IS_EMPTY_OR(IS_IN_DB(db1, 'rubros.codigo', '%(descripcion)s', multiple=True))),
			Field('subrubro', requires=IS_EMPTY_OR(IS_IN_DB(db1, 'subrubro.codigo', '%(descripcion)s', multiple=True))),
			Field('agrupador', requires=IS_EMPTY_OR(IS_IN_DB(db_omicronvt, 'agrupador_marca', '%(nombre)s'))),
			Field('agrupador_subrubro', requires=IS_EMPTY_OR(IS_IN_DB(db_omicronvt, 'agrupador_subrubro', '%(nombre)s'))),
			Field('agrupador_rubro', requires=IS_EMPTY_OR(IS_IN_DB(db_omicronvt, 'agrupador_rubro', '%(nombre)s'))),
			Field('sinonimo','string'),
			Field('descripcion','string'),
			)

	else:

		#formulario, permite sin marca o cualquiera
		form = SQLFORM.factory(
			Field('compras_desde', 'date', requires=IS_DATE(), default=request.now.date()+datetime.timedelta(days=-90)),
			Field('compras_hasta', 'date', requires=IS_DATE(), default=request.now.date()),
			Field('ventas_desde', 'date', requires=IS_DATE(), default=request.now.date()+datetime.timedelta(days=-90)),
			Field('ventas_hasta', 'date', requires=IS_DATE(), default=request.now.date()),
			Field('linea', requires=IS_EMPTY_OR(IS_IN_DB(db1, 'lineas.codigo', '%(descripcion)s', multiple=True))),
			Field('marca', requires=IS_EMPTY_OR(IS_IN_DB(db1, 'marcas.codigo', '%(descripcion)s', multiple=True))),
			Field('rubro', requires=IS_EMPTY_OR(IS_IN_DB(db1, 'rubros.codigo', '%(descripcion)s', multiple=True))),
			Field('subrubro', requires=IS_EMPTY_OR(IS_IN_DB(db1, 'subrubro.codigo', '%(descripcion)s', multiple=True))),
			Field('agrupador', requires=IS_EMPTY_OR(IS_IN_DB(db_omicronvt, 'agrupador_marca', '%(nombre)s'))),
			Field('agrupador_subrubro', requires=IS_EMPTY_OR(IS_IN_DB(db_omicronvt, 'agrupador_subrubro', '%(nombre)s'))),
			Field('agrupador_rubro', requires=IS_EMPTY_OR(IS_IN_DB(db_omicronvt, 'agrupador_rubro', '%(nombre)s'))),
			Field('sinonimo','string'),
			Field('descripcion','string'),
			)

	if form.process().accepted:

		if auth.has_membership('proveedores'):
			if len(form.vars.marca)==0:
				session.flash = 'Seleccione una marca'
				redirect(URL('rank_marcas_comp_vent'))

		if form.vars.compras_desde>form.vars.compras_hasta:
			session.flash='Fecha compras DESDE no puede ser mayor que fecha HASTA !'
			redirect(URL('informes','rank_marcas'))	
		if form.vars.ventas_desde>form.vars.ventas_hasta:
			session.flash='Fecha ventas DESDE no puede ser mayor que fecha HASTA !'
			redirect(URL('informes','rank_marcas'))	

		cd=form.vars.compras_desde
		ch=form.vars.compras_hasta
		vd=form.vars.ventas_desde
		vh=form.vars.ventas_hasta
		ln=','.join(form.vars.linea) if form.vars.linea else None
		# mc=tuple([int(x) for x in form.vars.marca]) if form.vars.marca else None
		mc=','.join(form.vars.marca) if form.vars.marca else None
		rb=','.join(form.vars.rubro) if form.vars.rubro else None
		sr=','.join(form.vars.subrubro) if form.vars.subrubro else None
		agrupador_marca=form.vars.agrupador
		agrupador_subrubro=form.vars.agrupador_subrubro
		agrupador_rubro=form.vars.agrupador_rubro
		sinonimo = form.vars.sinonimo
		descripcion = form.vars.descripcion if form.vars.descripcion else ''
		
		#guardo los campos del formulario en una variable de sesion para usar en informes colgados de este
		#session.inf_con_vars=[cd,ch,vd,vh,ln,mc,rb,sr,agrupador,agrupador_subrubro,agrupador_rubro, sinonimo]
		session.inf_con_vars = dict(c_desde=cd, c_hasta=ch, v_desde=vd, v_hasta=vh,
			linea=ln, marca=mc, rubro=rb, subrubro=sr, agrupador_marca=agrupador_marca, agrupador_subrubro=agrupador_subrubro, agrupador_rubro=agrupador_rubro, sinonimo=sinonimo, descripcion=descripcion)

		#nombre del agrupador para mostrar en título
		agrupador_lbl=db_omicronvt(db_omicronvt.agrupador_marca.id==form.vars.agrupador).select(db_omicronvt.agrupador_marca.nombre).first().nombre if form.vars.agrupador>0 else ''	

		#nombre del agrupador de subrubros para mostrar en título
		agrupador_subrubro_lbl=db_omicronvt(db_omicronvt.agrupador_subrubro.id==form.vars.agrupador_subrubro).select(db_omicronvt.agrupador_subrubro.nombre).first().nombre if form.vars.agrupador_subrubro>0 else ''	

		#nombre del agrupador de subrubros para mostrar en título
		agrupador_rubro_lbl=db_omicronvt(db_omicronvt.agrupador_rubro.id==form.vars.agrupador_rubro).select(db_omicronvt.agrupador_rubro.nombre).first().nombre if form.vars.agrupador_rubro>0 else ''	
		
		#query_compras=get_compras_consolidado(cd,ch,ln,mc,rb,sr,agrupador,agrupador_subrubro, agrupador_rubro, sinonimo)
		query_compras=get_compras_consolidado(desde=cd, hasta=ch, linea=ln, marca=mc, rubro=rb, subrubro=sr, agrupador_marca=agrupador_marca, agrupador_subrubro=agrupador_subrubro, agrupador_rubro=agrupador_rubro, sinonimo=sinonimo, descripcion=descripcion)

		for row in query_compras:#reemplazo valores vacíos por 0
			row[1]=0 if row[1]==None else row[1]
			row[2]=0 if row[2]==None else row[2]
		#armo un DF de compras
		dfc=pandas.DataFrame.from_records(query_compras,columns=['cantidad_c','subtotal_c','subtotal_devs_c','cod_marca','marca_c'])
		#dfc=pandas.DataFrame.from_records(query_compras,columns=['cantidad_c','subtotal_c','subtotal_devs_c','cod_marca','marca_c', 'depo'])
		dfc['total_c']=dfc['subtotal_c']-dfc['subtotal_devs_c']
		dfc['ppp_c']=dfc['total_c'].astype(float)/dfc['cantidad_c'].astype(float)

		#ponderado de compras
		tsql="SELECT LEFT(articulo.codigo_sinonimo,LEN(articulo.codigo_sinonimo)-2), subrubro.descripcion FROM articulo LEFT JOIN subrubro ON articulo.subrubro=subrubro.codigo "\
			"WHERE LEN(articulo.codigo_sinonimo)>3 AND "

	 	#VENTAS
	 	query_ventas=get_ventas_consolidado(desde=vd, hasta=vh, linea=ln, marca=mc, rubro=rb, subrubro=sr, agrupador_marca=agrupador_marca, agrupador_subrubro=agrupador_subrubro, agrupador_rubro=agrupador_rubro, sinonimo=sinonimo, descripcion=descripcion)
		for row in query_ventas:#reemplazo valores vacíos por 0
			row[1]=0 if row[1]==None else row[1]
			row[2]=0 if row[2]==None else row[2]

		# armo un dfv desde los resultados
		dfv_full=pandas.DataFrame.from_records(query_ventas,columns=['cantidad_v','subtotal_v','costo_v','cod_marca','marca_v','deposito_v'])	

		# si no hay compras ni ventas, retorno un json vacío-
		if ((dfc.empty==True) & (dfv_full.empty==True)):
			datos_json=''

		else:
			#si hay ventas
			if dfv_full.empty==False:
			
				# este es para los ponderados por local
				nuevo_dfv=dfv_full.filter(['cantidad_v','cod_marca','deposito_v'], axis=1)
				nuevo_dfv['deposito_v']=nuevo_dfv['deposito_v'].astype(str)
				
				# este para agrupar los marca
				dfv=dfv_full.filter(['cantidad_v','subtotal_v','costo_v','cod_marca','marca_v'], axis=1)
				dfv['cantidad_v']=dfv['cantidad_v'].astype(float)
				dfv['subtotal_v']=dfv['subtotal_v'].astype(float)
				dfv['costo_v']=dfv['costo_v'].astype(float)

				#agrupo por marca
				dfv=dfv.groupby(['cod_marca','marca_v']).sum().reset_index()

				dfv['total_v']=dfv['subtotal_v']
				dfv['ppp_v']=dfv['total_v'].astype(float)/dfv['cantidad_v'].astype(float)

				### calculo la rentabilidad
				dfv['rentab_v'] = (dfv['total_v']-dfv['costo_v']) / dfv['costo_v'] * 100

				# nuevo_dfv=dfv.filter(['cantidad_v','cod_marca','deposito_v'], axis=1)
				nuevo_dfv=nuevo_dfv.pivot(index='cod_marca', columns='deposito_v', values=['cantidad_v'])

				# nuevo_dfv = nuevo_dfv.set_index('cod_marca')
				nuevo_dfv['cantidad_v']=nuevo_dfv['cantidad_v'].astype(float)

				# saco los porcentajes : columna/suma_de_todas_las columnas
				nuevo_dfv=nuevo_dfv.div(nuevo_dfv.sum(axis=1), axis=0).apply(lambda x : x*100 ).round(2).reset_index()

				# achato los headers del multitindex , flatten multiindex
				nuevo_dfv.columns = ['_'.join(col) for col in nuevo_dfv.columns.values]

				#renombro la columna del cod_marca 
				nuevo_dfv.rename(columns={'cod_marca_':'cod_marca'}, inplace=True)

			if ((dfc.empty==True) & (dfv_full.empty==False)):#si no hay compras

				datos=dfv.reset_index()
				datos['marca']=datos['marca_v']


			elif ((dfc.empty==False) & (dfv_full.empty==True)):#si no hay ventas
				datos=dfc
				datos['marca']=datos['marca_c']
			else:


				dfc['marca']=dfc['marca_c']
				dfv['marca']=dfv['marca_v']
				
				#junto los 2 dfs
				datos = pandas.merge(dfc, dfv, on=['cod_marca','marca'], how='outer')

				#redondeo valores
				datos['total_v']=datos['total_v'].astype(float).round(2)
				datos['total_c']=datos['total_c'].astype(float).round(2)
				datos['rentab_v']=datos['rentab_v'].astype(float).round(2)

				#calculo datos relacionados entre los 2
				try:
					datos['ind_vc']=(datos['total_v']/datos['total_c']).astype(float).round(2)#ventas/compras en importe
				except ZeroDivisionError:
					datos['ind_vc']=0
				try:
					datos['ind_vcu']=(datos['cantidad_v'].astype(float)/datos['cantidad_c'].astype(float)).astype(float).round(2)#ventas/compras en unidades
				except ZeroDivisionError:
					datos['ind_vcu']=0


			#genero el ponderado de unidades por deposito
			datos = pandas.merge(datos, nuevo_dfv, on='cod_marca')	

			#STOCK
			lista_marcas=tuple(([int(x) for x in datos['cod_marca'].to_list() if x is not None]))
			#tupla de un solo registro, le remuevo la coma final
			lista_marcas='(%s)'%lista_marcas[0] if len(lista_marcas)==1 else lista_marcas


			### 19/07/22 reemplazadas por las 2 que le siguen para filtrar stock
			# texto_stock="SELECT SUM(s.stock_actual), MAX(m.codigo), MAX(s.deposito) FROM web_articulo a LEFT JOIN web_stock s ON s.articulo=a.codigo LEFT JOIN marcas m on m.codigo=a.marca WHERE a.marca IN {0} GROUP BY a.marca, s.deposito".format(lista_marcas)
			# df_stock=pandas.DataFrame.from_records(db1.executesql(texto_stock), columns=['stock','cod_marca','depo'])
			
			### 19/07/22 traen stock filtrado
			stock_filt = get_stock_consolidado(linea=ln, marca=mc, rubro=rb, subrubro=sr, agrupador_marca=agrupador_marca, agrupador_subrubro=agrupador_subrubro, agrupador_rubro=agrupador_rubro, sinonimo=sinonimo, descripcion=descripcion)
			df_stock=pandas.DataFrame.from_records(stock_filt, columns=['stock','cod_marca','depo'])
			
			# df_stock=df_stock[(df_stock['depo'] < 11) & (df_stock['depo'] >=0)]
			df_stock['depo']=df_stock['depo'].astype(str)
			df_stock['stock']=df_stock['stock'].astype(float)
			df_stock.dropna(inplace=True)		
			df_stock=df_stock.pivot(index='cod_marca', columns='depo', values=['stock'])		
			
			### Nuevo DF para calcular stock global
			df_stock_global=df_stock.copy()
			# achato los headers del multitindex , flatten multiindex
			df_stock_global = df_stock_global.reset_index()
			df_stock_global.columns = ['_'.join(col) for col in df_stock_global.columns.values]
			#sumo los stocks individuales
			df_stock_global['stock_global']=df_stock_global.sum(axis=1)		
			#renombro la columna del cod_marca 
			df_stock_global.rename(columns={'cod_marca_':'cod_marca'}, inplace=True)
			#dejo solo las columnas que me sirven
			df_stock_global=df_stock_global[['cod_marca','stock_global']]
			### Fin nuevo DF para calcular stock gloabl
	
			# saco los porcentajes : columna/suma_de_todas_las columnas
			df_stock=df_stock.div(df_stock.sum(axis=1), axis=0).apply(lambda x : x*100 ).round(2).reset_index()
			df_stock=df_stock.fillna(0)

			# achato los headers del multitindex , flatten multiindex
			df_stock.columns = ['_'.join(col) for col in df_stock.columns.values]

			#renombro la columna del cod_marca 
			df_stock.rename(columns={'cod_marca_':'cod_marca'}, inplace=True)			

			### hago el merge para los porcentajes de stock
			datos = pandas.merge(datos, df_stock, on='cod_marca')	

			### hago el merge para el stock global
			datos = pandas.merge(datos, df_stock_global, on='cod_marca')	

			#convierto el dataframe a json con pandas
			datos_json=datos.to_json(orient='records', date_format='iso')
		
		#para mostrar debajo del form
		desde=form.vars.desde
		hasta=form.vars.hasta
		linea=', '.join([x.descripcion for x in db1(db1.lineas.codigo.belongs(form.vars.linea)).select(db1.lineas.descripcion)]) if ln else ''
		marca=', '.join([x.descripcion for x in db1(db1.marcas.codigo.belongs(form.vars.marca)).select(db1.marcas.descripcion)]) if mc else ''
		rubro=', '.join([x.descripcion for x in db1(db1.rubros.codigo.belongs(form.vars.rubro)).select(db1.rubros.descripcion)]) if rb else ''
		subrubro=', '.join([x.descripcion for x in db1(db1.subrubro.codigo.belongs(form.vars.subrubro)).select(db1.subrubro.descripcion)]) if sr else ''


		#### grafico ponderado subrubro
		hc_graf4 = gr_pond_subrubro_global(
			**session.inf_con_vars)

		#### grafico 5  - ponderado rubro
		hc_graf5 = gr_pond_rubro_global(
			**session.inf_con_vars)


	elif form.errors:
		response.flash = 'Error en fechas'		
	return dict (id_informe='IC0001',form=form, datos_json=datos_json, cd=cd,ch=ch,vd=vd,vh=vh,ln=ln, mc=mc,rb=rb,sr=sr, 
		linea=linea, marca=marca, rubro=rubro, subrubro=subrubro, 
		agrupador_lbl=agrupador_lbl, agrupador_subrubro_lbl=agrupador_subrubro_lbl, agrupador_rubro_lbl=agrupador_rubro_lbl,
		hc_graf4=hc_graf4, hc_graf5=hc_graf5, sinonimo=sinonimo, descripcion=descripcion
		)	


#RANKING DE PRODUCTOS COMPRAS/VENTAS X MARCA - IC0002
@auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('proveedores')) or auth.has_membership(auth.id_group('admins')))
def rank_productos_xmarca():
	datos_json=[]
	desde=''
	hasta=''
	linea=''
	codmar=''

	if request.args(0):#aca traigo el cod. de marca
		# #recupero fechas y linea desde var de sesion
		if session.inf_con_vars:
			session.inf_con_vars['marca']=request.args(0)
		else:
			m = 'Sesión vencida, realice nueva búsqueda principal.'
			redirect(URL('informes_error','index', vars=dict(descrip=m)))
		

		if auth.has_membership('proveedores'):
			nro_proveedor = auth.user.nro_proveedor
			marcas_proveedor = db1(db1.articulo.proveedor==nro_proveedor).select(db1.articulo.marca, distinct=True)
			marcas_proveedor = [int(x['marca']) for x in marcas_proveedor]
			if int(session.inf_con_vars['marca']) not in marcas_proveedor:
				m = 'No tiene permiso para visualizar la marca seleccionada.'
				redirect(URL('informes_error','index', vars=dict(descrip=m)))

		#busco la data por : desde,hasta,linea,marca
		
		#query_compras=get_compras_consolidado_xmarca(cd, ch, ln, request.args(0), rb, sr, agrupador_subrubro, agrupador_rubro, sinonimo)
		query_compras=get_compras_consolidado_xmarca(**session.inf_con_vars)
		
		for row in query_compras:#reemplazo valores vacíos por 0
			row[1]=0 if row[1]==None else row[1]
			row[2]=0 if row[2]==None else row[2]
		#armo un DF de compras
		dfc=pandas.DataFrame.from_records(query_compras,columns=['cantidad_c','subtotal_c','subtotal_devs_c','csr'])
		dfc['total_c']=dfc['subtotal_c']-dfc['subtotal_devs_c']
		dfc['ppp_c']=dfc['total_c'].astype(float)/dfc['cantidad_c'].astype(float)

	 	#VENTAS
	 	#query_ventas=get_ventas_consolidado_xmarca(session.inf_consolidados_vars['desde'],session.inf_consolidados_vars['hasta'],session.inf_consolidados_vars['linea'],request.args(0))
		query_ventas=get_ventas_consolidado_xmarca(**session.inf_con_vars)
		for row in query_ventas:#reemplazo valores vacíos por 0
			row[1]=0 if row[1]==None else row[1]
			row[2]=0 if row[2]==None else row[2]
		#armo un DF de ventas
		dfv=pandas.DataFrame.from_records(query_ventas,columns=['cantidad_v','subtotal_v','costo_v','csr'])		
		dfv['total_v']=dfv['subtotal_v']
		dfv['ppp_v']=dfv['total_v'].astype(float)/dfv['cantidad_v'].astype(float)


		### CALCULO DE RENTABILIDAD
		# dfv['rent_devs']=(dfv['rent_devs'].astype(float)-1)*100
		# dfv['rent_devs'].fillna(0, inplace=True)

		# dfv['rent_vent']=(dfv['rent_vent'].astype(float)-1)*100
		# dfv['rent_vent'].fillna(0, inplace=True)

		# dfv['rentab']=dfv['rent_vent'].astype(float)-dfv['rent_devs'].astype(float)

		dfv['rentab']=(dfv['subtotal_v'].astype(float)-dfv['costo_v'].astype(float)) / dfv['costo_v'].astype(float)	* 100

		dfv['rentab']=dfv['rentab'].round(2)




		

		#junto los 2 dfs
		datos = pandas.merge(dfc, dfv, on=['csr'], how='outer')

		#junto las 2 descripciones en una: si no existe descripcion_v usa descripcion_c
		#datos['descri']=datos['descripcion_v'].fillna(datos['descripcion_c'])
		#junto los 2 subrubros en uno: si no existe subrubro_v usa subrubro_c
		#datos['subrubro']=datos['subrubro_v'].fillna(datos['subrubro_c'])
		#junto los 2 rubros en uno: si no existe rubro_v usa rubro_c
		#datos['rubro']=datos['rubro_v'].fillna(datos['rubro_c'])
		# #agrupo por csr
		# datos=datos.groupby(by=['csr','descri'])['cantidad_v','total_v','cantidad_c','total_c'].apply(lambda x: x.astype(float).sum()).reset_index()
		#redondeo valores
		datos['total_v']=datos['total_v'].astype(float).round(2)
		datos['total_c']=datos['total_c'].astype(float).round(2)
		#calculo datos relacionados entre los 2
		datos['ind_vc']=(datos['total_v']/datos['total_c']).astype(float).round(2)#ventas/compras en importe
		try:
			datos['ind_vcu']=(datos['cantidad_v']/datos['cantidad_c']).astype(float).round(2)#ventas/compras en unidades		
		except ZeroDivisionError:
			datos['ind_vcu']=0
		#calculo rentabilidad
		#datos['rent']=(((datos['total_v'].astype(float)/datos['cantidad_v'].astype(float))/(datos['total_c'].astype(float)/datos['cantidad_c'].astype(float))-1)*100).astype(float).round(2)
		datos['rent']=datos['rentab']

		#ordeno por vc
		datos=datos.sort_values('ind_vc')
		
		#agrego el stock actual
		# usa funcion get_stock en models/funciones_informes.py
		#datos['stock_actual']=datos.apply(lambda x: get_stock(x['csr']), axis=1)
		# traigo la num max y min de la curva
		# datos['num']=datos.apply(lambda x: get_numeracion(x['csr']), axis=1)
		# datos[['num_min','num_max']]=datos.num.str.split('|', expand=True)


		############## DISTRIB STOCK ###
		################################
		# texto_stock="SELECT SUM(s.stock_actual), s.deposito, left(a.codigo_sinonimo, len(a.codigo_sinonimo)-2) FROM web_articulo a "\
		# 	"LEFT JOIN web_stock s ON a.codigo=s.articulo WHERE a.marca=%s AND len(a.codigo_sinonimo)>5 AND s.deposito in (0,1,2,3,4,5,6,7,8,9,198) "\
		# 	"GROUP BY s.deposito, left(a.codigo_sinonimo, len(a.codigo_sinonimo)-2) HAVING SUM(s.stock_actual)>0"%request.args(0)

		query_stock = get_stock_consolidado_xmarca(**session.inf_con_vars)

		# df_stock=pandas.DataFrame.from_records(db1.executesql(texto_stock), columns=['stock_actual','depo','csr'])
		df_stock=pandas.DataFrame.from_records(query_stock, columns=['stock_actual','depo','csr'])

		df_stock['depo']=df_stock['depo'].astype(str)
		df_stock['stock_actual']=df_stock['stock_actual'].astype(float)
		
		df_stock=df_stock.pivot(index='csr', columns='depo', values=['stock_actual'])

		### obtengo el stock_total
		df_stock['stock_total']=df_stock.sum(axis=1)

		### DF PARA LOS PORCENTAJES: saco los porcentajes : columna/suma_de_todas_las columnas excepto stock_total
		df_stock_porcents=df_stock.drop('stock_total', axis=1).div(df_stock.drop('stock_total', axis=1).sum(axis=1), axis=0).apply(lambda x : x*100 ).round(2).reset_index()
		df_stock_porcents=df_stock_porcents.fillna(0)			
		# achato los headers del multitindex , flatten multiindex
		df_stock_porcents.columns = ['_'.join(col) for col in df_stock_porcents.columns.values]
		#renombro la columna del cod
		df_stock_porcents.rename(columns={'csr_':'csr'}, inplace=True)	


		### DF PARA EL EL STOCK TOTAL
		# achato los headers del multitindex , flatten multiindex
		df_stock.columns = ['_'.join(col) for col in df_stock.columns.values]
		#renombro la columna del cod
		df_stock.rename(columns={'csr_':'csr','stock_total_':'stock_actual'}, inplace=True)	
		df_stock.reset_index(inplace=True)
		### me quedo solo con el stock total
		df_stock = df_stock[['csr','stock_actual']]
		
		### MERGE
		#datos=datos.merge(df_stock, on='csr', how='left')
		datos=datos.merge(df_stock, on='csr', how='outer')
		datos=datos.merge(df_stock_porcents, on='csr', how='outer')
		############# FIN DISTRIB STOCK ###



		############## DISTRIB VENTAS ###
		################################
		# texto_ventas="SELECT SUM((CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END)), v.deposito, left(a.codigo_sinonimo, len(a.codigo_sinonimo)-2) FROM web_articulo a "\
		# "LEFT JOIN omicron_ventas1 v ON a.codigo=v.articulo WHERE a.marca=%s GROUP BY v.deposito, left(a.codigo_sinonimo, len(a.codigo_sinonimo)-2)"%request.args(0)

		query_distrib_ventas = get_distrib_ventas_xmarca(**session.inf_con_vars)

		# df_ventas=pandas.DataFrame.from_records(db1.executesql(texto_ventas), columns=['cant_dv','depo_dv','csr'])
		df_ventas=pandas.DataFrame.from_records(query_distrib_ventas, columns=['cant_dv','depo_dv','csr'])

		df_ventas['depo_dv']=df_ventas['depo_dv'].astype(str)
		df_ventas['cant_dv']=df_ventas['cant_dv'].astype(float)

		df_ventas=df_ventas.pivot(index='csr', columns='depo_dv', values=['cant_dv'])

		# saco los porcentajes : columna/suma_de_todas_las columnas
		df_ventas=df_ventas.div(df_ventas.sum(axis=1), axis=0).apply(lambda x : x*100 ).round(2).reset_index()
		df_ventas=df_ventas.fillna(0)

		# achato los headers del multitindex , flatten multiindex
		df_ventas.columns = ['_'.join(col) for col in df_ventas.columns.values]

		#renombro la columna del cod
		df_ventas.rename(columns={'csr_':'csr'}, inplace=True)	

		### MERGE
		datos=datos.merge(df_ventas, on='csr', how='left')

		############## FIN DISTRIB VENTAS ###


		#lista_csr = tuple([str(x) for x in datos['csr'].values.tolist()])
		lista_csr = fx_list_4_sql([str(x) for x in datos['csr'].values.tolist()])

		###DATA DE LOS PRODUCTOS
		t_sql = "SELECT MAX(LEFT(a.codigo_sinonimo,10)) , MAX(a.descripcion_1), MAX(m.descripcion), MAX(r.descripcion), MAX(s.descripcion), MAX(a.descripcion_5), MIN(a.descripcion_5) "\
			"FROM web_articulo a LEFT JOIN marcas m on m.codigo=a.marca LEFT JOIN rubros r on r.codigo=a.rubro LEFT JOIN subrubro s ON s.codigo=a.subrubro "\
			"WHERE LEFT(a.codigo_sinonimo,10) IN {0} GROUP BY LEFT(codigo_sinonimo, 10)".format(lista_csr)


		df_prods = pandas.DataFrame.from_records(db1.executesql(t_sql), columns=['csr', 'descri', 'marca', 'rubro', 'subrubro','num_max','num_min' ])

		datos = datos.merge(df_prods, on='csr', how='outer')

		#agrego las imagenes. Funcion en /models/func_informes.py
		datos['imagen']=datos.apply(lambda x: get_imagen_mini(x['csr']), axis=1)

		#convierto el dataframe a json con pandas
		datos_json=datos.to_json(orient='records', date_format='iso')
		#vuelvo el json a otro json - sino no anda el JS Tabulator
		# datos_json=json.dumps(datosj, ensure_ascii=False)
		


		#para mostrar debajo del form
		desde=''
		hasta=''
		linea=db1(db1.lineas.codigo==session.inf_con_vars['linea']).select(db1.lineas.descripcion).first().descripcion if session.inf_con_vars['linea']>0 else ''
		marca=db1(db1.marcas.codigo==request.args(0)).select(db1.marcas.descripcion).first().descripcion

		#GRAFICO 1
		dam=pandas.DataFrame.from_records(get_compras_consolidado_xmarca_graf_anmes(**session.inf_con_vars), columns=['cantidad_c','anmes','an','me'])#datos de compras
		damm=dam[['anmes','cantidad_c']]#cambio orden de las columnas de compras

		dav=pandas.DataFrame.from_records(get_ventas_consolidado_xmarca_graf_anmes(**session.inf_con_vars), columns=['cantidad_v','anmes','an','me'])#datos de ventas
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


		hc_graf=func_grafico_1(**session.inf_con_vars)

		hc_graf2=func_grafico_2(**session.inf_con_vars)

		hc_graf3=func_grafico_3(**session.inf_con_vars)


		#############################################################
		### GRAFICO 4 - PONDERADOS POR SUBRUBRO #####################
		### Compras
		df_pond_compra=datos[['cantidad_c','subrubro']].copy()
		df_pond_compra['cantidad_c']=df_pond_compra['cantidad_c'].astype(float)
		df_pond_compra=df_pond_compra.groupby(['subrubro']).sum().reset_index()
		df_pond_compra['pond'] = ((df_pond_compra['cantidad_c']/df_pond_compra['cantidad_c'].sum())*100).round(2)
		#serie compras
		serie_pond_subr_compras={'name':'Compras'}
		#convierto el df compras a lista y lo pongo en el dict como data
		serie_pond_subr_compras['data']=df_pond_compra[['subrubro','pond']].values.tolist()

		### Ventas
		df_pond_venta=datos[['cantidad_v','subrubro']].copy()
		df_pond_venta['cantidad_v']=df_pond_venta['cantidad_v'].astype(float)
		df_pond_venta=df_pond_venta.groupby(['subrubro']).sum().reset_index()
		df_pond_venta['pond'] = ((df_pond_venta['cantidad_v']/df_pond_venta['cantidad_v'].sum())*100).round(2)
		#serie ventas
		serie_pond_subr_ventas={'name':'Ventas'}
		#convierto el df ventas a lista y lo pongo en el dict como data
		serie_pond_subr_ventas['data']=df_pond_venta[['subrubro','pond']].values.tolist()

		### Stock actual
		df_pond_stock=datos[['stock_actual','subrubro']].copy()
		df_pond_stock['stock_actual']=df_pond_stock['stock_actual'].astype(float)
		df_pond_stock=df_pond_stock.groupby(['subrubro']).sum().reset_index()
		df_pond_stock['pond'] = ((df_pond_stock['stock_actual']/df_pond_stock['stock_actual'].sum())*100).round(2)	
		#serie stock
		serie_pond_subr_stock={'name':'Stock actual'}
		#convierto el df stock a lista y lo pongo en el dict como data
		serie_pond_subr_stock['data']=df_pond_stock[['subrubro','pond']].values.tolist()


		#meto la data de compras en un dict
		hc_datos4=[serie_pond_subr_compras]
		#le agrego la data de ventas
		hc_datos4.append(serie_pond_subr_ventas)
		#le agrego la data de stock actual
		hc_datos4.append(serie_pond_subr_stock)

		#tiro la data para el graf de highcharts
		hc_graf4=json.dumps(hc_datos4, default=str)
		### FIN GRAFICO 4 ###########################################
		#############################################################

		#############################################################
		### GRAFICO 5 - PONDERADOS POR RUBRO ########################
		### Compras
		df_pond_compra=datos[['cantidad_c','rubro']].copy()
		df_pond_compra['cantidad_c']=df_pond_compra['cantidad_c'].astype(float)
		df_pond_compra=df_pond_compra.groupby(['rubro']).sum().reset_index()
		df_pond_compra['pond'] = ((df_pond_compra['cantidad_c']/df_pond_compra['cantidad_c'].sum())*100).round(2)
		#serie compras
		serie_pond_rub_compras={'name':'Compras'}
		#convierto el df compras a lista y lo pongo en el dict como data
		serie_pond_rub_compras['data']=df_pond_compra[['rubro','pond']].values.tolist()

		### Ventas
		df_pond_venta=datos[['cantidad_v','rubro']].copy()
		df_pond_venta['cantidad_v']=df_pond_venta['cantidad_v'].astype(float)
		df_pond_venta=df_pond_venta.groupby(['rubro']).sum().reset_index()
		df_pond_venta['pond'] = ((df_pond_venta['cantidad_v']/df_pond_venta['cantidad_v'].sum())*100).round(2)
		#serie ventas
		serie_pond_rub_ventas={'name':'Ventas'}
		#convierto el df ventas a lista y lo pongo en el dict como data
		serie_pond_rub_ventas['data']=df_pond_venta[['rubro','pond']].values.tolist()

		### Stock actual
		df_pond_stock=datos[['stock_actual','rubro']].copy()
		df_pond_stock['stock_actual']=df_pond_stock['stock_actual'].astype(float)
		df_pond_stock=df_pond_stock.groupby(['rubro']).sum().reset_index()
		df_pond_stock['pond'] = ((df_pond_stock['stock_actual']/df_pond_stock['stock_actual'].sum())*100).round(2)	
		#serie stock
		serie_pond_rub_stock={'name':'Stock actual'}
		#convierto el df stock a lista y lo pongo en el dict como data
		serie_pond_rub_stock['data']=df_pond_stock[['rubro','pond']].values.tolist()


		#meto la data de compras en un dict
		hc_datos5=[serie_pond_rub_compras]
		#le agrego la data de ventas
		hc_datos5.append(serie_pond_rub_ventas)
		#le agrego la data de stock actual
		hc_datos5.append(serie_pond_rub_stock)

		#tiro la data para el graf de highcharts
		hc_graf5=json.dumps(hc_datos5, default=str)
		### FIN GRAFICO 5 ###########################################
		#############################################################



		#############################################################
		### GRAFICO 6 - STOCK POR NRO ########################
		t_sql = "SELECT SUM(s.stock_actual) as stock_actual, a.descripcion_5 as nro "\
			"FROM omicronvt.dbo.stock_por_codigo s "\
			"LEFT JOIN msgestion01.dbo.articulo a ON a.codigo=s.articulo "\
			"WHERE LEFT(a.codigo_sinonimo,10) IN {0} AND s.deposito in {1} GROUP BY a.descripcion_5".format(lista_csr, depos_para_informes)

		data = db1.executesql(t_sql, as_dict=True)

		df6 = pandas.DataFrame.from_dict(data)
		df6['stock_actual'] = df6['stock_actual'].fillna(0).astype(int)
		#df6['nro'] = df6['nro'].astype(int)
		#df6['nro'] = df6['nro'].astype("Int64")
		df6['nro'] = df6['nro'].fillna(0).astype(str)

		#serie stock
		serie_stock_por_nro={'name':'Stock actual'}
		#convierto el df6 a lista y lo pongo en el dict como data
		serie_stock_por_nro['data']=df6[['nro','stock_actual']].values.tolist()

		hc_datos6 = [serie_stock_por_nro]
				#tiro la data para el graf de highcharts
		hc_graf6=json.dumps(hc_datos6, default=str)
		### FIN GRAFICO 6 ###########################################
		#############################################################



		
	elif form.errors:
		response.flash = 'Error en fechas'		

	return dict (id_informe='IC0002',datos_json=datos_json, 
		cd = session.inf_con_vars['c_desde'], ch = session.inf_con_vars['c_hasta'], vd = session.inf_con_vars['v_desde'], vh = session.inf_con_vars['v_hasta'], 
		linea=linea, marca=marca, codmar=codmar, hc_graf=hc_graf, hc_graf2=hc_graf2, hc_graf3=hc_graf3, 
		hc_graf4=hc_graf4, hc_graf5=hc_graf5, hc_graf6=hc_graf6, rb = session.inf_con_vars['rubro'], sr = session.inf_con_vars['subrubro'])	


#CURVA POR PRODUCTO COMPRA/VENTA - IC0003
@auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('proveedores')) or auth.has_membership(auth.id_group('admins')))
def producto_curva():
	import time
	datos_json=[]
	desde=''
	hasta=''
	linea=''
	csr=''
	imagen=''
	ppc=ppv=''
	ts = ''
	if request.args(0):#aca traigo el cod. sinonimo recortado
		
		if session.inf_con_vars:
			pass
		else:
			m = 'Sesión vencida, realice nueva búsqueda principal.'
			redirect(URL('informes_error','index', vars=dict(descrip=m)))	

		if auth.has_membership('proveedores'):
			nro_proveedor = auth.user.nro_proveedor
			marcas_proveedor = db1(db1.articulo.proveedor==nro_proveedor).select(db1.articulo.marca, distinct=True)
			marcas_proveedor = [int(x['marca']) for x in marcas_proveedor]

			marca_del_articulo = db1(db1.articulo.codigo_sinonimo.startswith(request.args(0))).select(db1.articulo.marca).first()['marca']

			if int(marca_del_articulo) not in marcas_proveedor:
				m = 'No tiene permiso para visualizar la marca seleccionada.'
				redirect(URL('informes_error','index', vars=dict(descrip=m)))

		###meto las fecha en session para poder linkear informes_000/art_comp_vent
		ts=str(time.time())
		session.informe_000={}
		session.informe_000[ts]=[session.inf_con_vars['c_desde'], session.inf_con_vars['c_hasta'], session.inf_con_vars['v_desde'], session.inf_con_vars['v_hasta']]


		#Dataframe de COMPRAS, busco la data por : desde,hastacodigo_sinonimo recortado
		query_compras=get_compras_curva_producto(session.inf_con_vars['c_desde'] ,session.inf_con_vars['c_hasta'] ,request.args(0))

		for row in query_compras:#reemplazo valores vacíos por 0
			row[1]=0 if row[1]==None else row[1]
			row[2]=0 if row[2]==None else row[2]
		#armo el DF de compras
		dfc=pandas.DataFrame.from_records(query_compras,columns=['cantidad_c','subtotal_c','subtotal_devs_c','cs','nro_c','fecha'])
		dfc['total_c']=dfc['subtotal_c']-dfc['subtotal_devs_c']
		dfc['ppp_c']=dfc['total_c'].astype(float)/dfc['cantidad_c'].astype(float)

		#Dataframe de VENTAS, busco la data por : desde,hasta,linea,codigo_sinonimo recortado
		query_ventas=get_ventas_curva_producto(session.inf_con_vars['v_desde'], session.inf_con_vars['v_hasta'], request.args(0))
		for row in query_ventas:#reemplazo valores vacíos por 0
			row[1]=0 if row[1]==None else row[1]
			row[2]=0 if row[2]==None else row[2]
		#armo el DF de ventas
		dfv=pandas.DataFrame.from_records(query_ventas,columns=['cantidad_v','subtotal_v','subtotal_devs_v','cs','nro_v','fecha'])			
		dfv['total_v']=dfv['subtotal_v']-dfv['subtotal_devs_v']
		dfv['ppp_v']=dfv['total_v'].astype(float)/dfv['cantidad_v'].astype(float)

		#junto los 2 dfs
		datos = pandas.merge(dfc, dfv, on=['cs','fecha'], how='outer')

		#junto las 2 descripciones en una: si no existe descripcion_v usa descripcion_c
		datos['nro']=datos['nro_v'].fillna(datos['nro_c'])

		#agrupo por cod. sinonimo
		datos['nro']=999#uso un nro. trucho para que no de error el groupby, mas abajo se borra. OMICRON-VT(Revisar)
		datos=datos.groupby(by=['cs','nro'])['cantidad_v','total_v','cantidad_c','total_c'].apply(lambda x: x.astype(float).sum()).reset_index()

		#agrego el stock actual
		#datos['stock_actual']=datos.apply(lambda x: get_stock_prod(x['cs']), axis=1)
		dfs=pandas.DataFrame.from_records(get_stock_curva(request.args(0)), columns=['stock_actual','cs','nro'])

		
		### si el producto no tiene ventas ni compras, invento un df en 0 para que no tire error al mergear con stock y en data de gráficos - 10/02/23
		if len(datos)<1:
			columns = ['cantidad_c', 'subtotal_c', 'subtotal_devs_c', 'nro_c', 'total_c', 'ppp_c', 'cantidad_v', 'subtotal_v', 'subtotal_devs_v', 'cs', 'nro_v', 'fecha', 'total_v', 'ppp_v','nro']
			data_en_cero = [(0, 0, 0, 0, 0, 0, 0, 0, 0, '0', 0, '', 0 , 0, 0 )]
			datos = pandas.DataFrame.from_records(data_en_cero, columns=columns)

		#redondeo valores
		datos['total_v']=datos['total_v'].astype(float).round(2)
		datos['total_c']=datos['total_c'].astype(float).round(2)
		#calculo datos relacionados entre los 2
		datos['ind_vc']=(datos['total_v']/datos['total_c']).astype(float).round(2)#ventas/compras en importe
		datos['ind_vcu']=(datos['cantidad_v']/datos['cantidad_c']).astype(float).round(2)#ventas/compras en unidades

		#borro el nro - temporal SACARLO DE LOS DF DE COMPRAS Y VENTAS - OMICRON-VT(Revisar)
		datos=datos.drop('nro', axis=1)

		#junto con el stock - este trae la curva completa con nro y stock actual independientemente de las fechas ingresadas
		datos2=pandas.merge(datos,dfs,on='cs',how='outer')
		#ordeno por nro.
		datos2=datos2.sort_values(by='nro')

		#precio promedio de compra
		ppc=datos2['total_c'].sum()/datos2['cantidad_c'].sum()
		#precio promedio de venta
		ppv=datos2['total_v'].sum()/datos2['cantidad_v'].sum()





		#convierto el dataframe a json con pandas
		datos_json=datos2.to_json(orient='records', date_format='iso')
		#vuelvo el json a otro json - sino no anda el JS Tabulator
		# datos_json=json.dumps(datosj, ensure_ascii=False)

		# ##INICIO DATOS PARA GRAFICO 1
		# #agrupo los datos por fecha(1 x dia)
		# datagraf=datos.groupby(by='fecha')['cantidad_v','total_v','cantidad_c','total_c'].apply(lambda x: x.astype(float).sum()).reset_index()
		dam=pandas.DataFrame.from_records(get_compras_curva_producto_anmes(request.args(0)),columns=['cantidad_c','anmes',])#datos de compras
		dam=dam[['anmes','cantidad_c']]#cambio orden de las columnas de compras
		dav=pandas.DataFrame.from_records(get_ventas_curva_producto_anmes(request.args(0)),columns=['cantidad_v','anmes',])#datos de ventas
		dav=dav[['anmes','cantidad_v']]#cambio orden de las columnas de venta
		dat=pandas.merge(dam,dav, on=['anmes'], how='outer')#junto los 2 dfs
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
		# ## FIN DATOS PARA GRAFICO 1

		# ##INICIO DATOS PARA GRAFICO 2
		dm=pandas.DataFrame.from_records(get_compras_curva_producto_mes(request.args(0)),columns=['cantidad_c','mes',])#traigo las compras
		dm=dm[['mes','cantidad_c']]#cambio el orden de las columnas de compras
		dv=pandas.DataFrame.from_records(get_ventas_curva_producto_mes(request.args(0)),columns=['cantidad_v','mes','promedio_v'])#traigo las ventas
		dv=dv[['mes','cantidad_v','promedio_v']]#cambio el orden de las columnas de ventas
		dv['prom_gral_v'] = dv['cantidad_v'].mean()
		dv['prom_mensual_gral_v'] = dv['promedio_v'].mean()

		dt=pandas.merge(dm, dv, on=['mes'], how='outer')#junto los dos dfs
		dt['cantidad_c']=dt['cantidad_c'].astype(float).round(2)
		dt['cantidad_v']=dt['cantidad_v'].astype(float).round(2)

		serie_compras2={'name':'Compras'}#creo la serie de compras
		xcl=dt[['mes','cantidad_c']].sort_values('mes').values.tolist()#solo los datos de compra, los ordeno por mes y los convierto a lista.
		serie_compras2['data']=xcl#agrego la lista a la serie de compras
		hc_datos2=[serie_compras2]#junto nombre y datos
		
		serie_ventas2={'name':'Ventas'}#creo la serie con nombre
		xvl=dt[['mes','cantidad_v']].values.tolist()#convierto a lista
		serie_ventas2['data']=xvl#armo los datos de la serie
		hc_datos2.append(serie_ventas2)#los agrego a las ventas

		serie_prom_gral2={'name':'Media Venta Total Gral'}
		xgl = dt[['mes','prom_gral_v']].values.tolist()#convierto a lista
		serie_prom_gral2['type'] = 'line'
		serie_prom_gral2['data'] = xgl
		hc_datos2.append(serie_prom_gral2)

		serie_promedio2={'name':'Venta Promedio Mensual'}#creo la serie con nombre
		xpl = dt[['mes','promedio_v']].values.tolist()#convierto a lista
		serie_promedio2['type']='column'
		serie_promedio2['data']=xpl#armo los datos de la serie
		hc_datos2.append(serie_promedio2)#los agrego

		serie_prom_mensual_gral2={'name':'Media Venta Mensual Gral'}
		xml = dt[['mes','prom_mensual_gral_v']].values.tolist()#convierto a lista
		serie_prom_mensual_gral2['type'] = 'line'
		serie_prom_mensual_gral2['data'] = xml
		hc_datos2.append(serie_prom_mensual_gral2)#los agrego
		
		hc_graf2=json.dumps(hc_datos2, default=str)#default=str para que no de error serializando datetime
		# ## FIN DATOS PARA GRAFICO 2


		# ##INICIO GRAF CURVA IDEAL PRODUCTO
		dfvp=datos2[['nro','cantidad_v']].copy()
		dfvp['porcent']=dfvp['cantidad_v']/dfvp['cantidad_v'].sum()*100
		dfvp['comprar']=(dfvp['porcent']/dfvp['porcent'].min()).round(0)
		serie_curva_producto={'name':'xxxxxx'}
		#convierto el df stock a lista y lo pongo en el dict como data
		serie_curva_producto['data']=dfvp[['nro','comprar']].values.tolist()
		hc_datos3=[serie_curva_producto]
		hc_graf3=json.dumps(hc_datos3, default=str)		
		# ##FIN GRAF CURVA IDEAL PRODUCTO

		# ##INICIO GRAF CURVA IDEAL MARCA-SUBRUBRO
		texto_sql="SELECT DISTINCT a.marca, a.subrubro, m.descripcion, s.descripcion, a.descripcion_1 FROM web_articulo a LEFT JOIN marcas m ON a.marca=m.codigo LEFT JOIN subrubro s ON a.subrubro=s.codigo WHERE a.codigo_sinonimo LIKE '{0}%' ORDER BY marca".format(request.args(0))
		datax=db1.executesql(texto_sql)
		texto_sql2="SELECT SUM((CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END)) as items, a.descripcion_5 "\
			"FROM web_articulo a "\
			"LEFT JOIN omicron_ventas1 v ON a.codigo=v.articulo "\
			"WHERE a.marca={0} AND a.subrubro={1} "\
			"AND v.fecha>='{2}' AND v.fecha<='{3}'"\
			"GROUP BY a.descripcion_5".format(datax[0][0], datax[0][1], session.inf_con_vars['c_desde'], session.inf_con_vars['c_hasta'])
		dfv=pandas.DataFrame.from_records(db1.executesql(texto_sql2), columns=['vendidos','nro'])
		try:
			dfv['nro']=dfv['nro'].astype(float)
		except:
			dfv['nro']=dfv['nro']
		dfv['vendidos']=dfv['vendidos'].astype(float)
		dfv['porcent']=dfv['vendidos']/dfv['vendidos'].sum()*100
		dfv['comprar']=(dfv['porcent']/dfv.query('porcent>0')['porcent'].min()).round(0)
		serie_curva_subrubromarca={'name':'%s (%s)'%(datax[0][2], datax[0][3])}
		#convierto el df stock a lista y lo pongo en el dict como data
		serie_curva_subrubromarca['data']=dfv[['nro','comprar']].values.tolist()
		hc_datos4=[serie_curva_subrubromarca]
		hc_graf4=json.dumps(hc_datos4, default=str)		
		# ##FIN GRAF CURVA IDEAL MARCA-SUBRUBRO

		# ##INICIO GRAF CURVA IDEAL PRODUCTO
		dfvp=datos2[['nro','cantidad_v']].copy()
		dfvp['porcent']=dfvp['cantidad_v']/dfvp['cantidad_v'].sum()*100
		dfvp['comprar']=(dfvp['porcent']/dfvp.query('porcent>0')['porcent'].min()).round(0)
		serie_curva_producto={'name':'%s-%s'%(datax[0][2], datax[0][4])}
		#convierto el df stock a lista y lo pongo en el dict como data
		serie_curva_producto['data']=dfvp[['nro','comprar']].values.tolist()
		hc_datos3=[serie_curva_producto]
		hc_graf3=json.dumps(hc_datos3, default=str)		
		# ##FIN GRAF CURVA IDEAL PRODUCTO

		# ##INICIO GRAF CURVA IDEAL SUBRUBRO
		texto_sql3="SELECT SUM((CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END)) as items, a.descripcion_5 "\
			"FROM web_articulo a "\
			"LEFT JOIN omicron_ventas1 v ON a.codigo=v.articulo "\
			"WHERE a.subrubro={0} "\
			"AND v.fecha>='{1}' AND v.fecha<='{2}'"\
			"GROUP BY a.descripcion_5".format(datax[0][1], session.inf_con_vars['c_desde'], session.inf_con_vars['c_hasta'])
		dfvs=pandas.DataFrame.from_records(db1.executesql(texto_sql3), columns=['vendidos','nro'])
		### SOLUCION TEMPORAL 10-02-2022
		### dfvs['nro']=dfvs['nro'].astype(float)
		try:
			dfvs['nro']=dfvs['nro'].astype(float)
		except ValueError:
			dfvs['nro']=dfvs['nro']
		### FIN SOLUCION TEMPORAL	
		dfvs['vendidos']=dfvs['vendidos'].astype(float)
		dfvs['porcent']=dfvs['vendidos']/dfvs['vendidos'].sum()*100
		dfvs['comprar']=(dfvs['porcent']/dfvs.query('porcent>0')['porcent'].min()).round(0)
		serie_curva_subrubro={'name':'%s'%(datax[0][3])}
		#convierto el df stock a lista y lo pongo en el dict como data
		serie_curva_subrubro['data']=dfvs[['nro','comprar']].values.tolist()
		hc_datos5=[serie_curva_subrubro]
		hc_graf5=json.dumps(hc_datos5, default=str)

		# ##FIN GRAF CURVA IDEAL SUBRUBRO

		#IMAGEN PRODUCTO
		imagen=str(get_imagen(request.args(0)))

	elif form.errors:
		response.flash = 'Error en fechas'		
	return dict (id_informe='IC0003',datos_json=datos_json, 
		cd=session.inf_con_vars['c_desde'], ch=session.inf_con_vars['c_hasta'], vd=session.inf_con_vars['v_desde'], vh=session.inf_con_vars['v_hasta'], linea=linea, csr=csr,
	 hc_graf=hc_graf, hc_graf2=hc_graf2, hc_graf3=hc_graf3, hc_graf4=hc_graf4, hc_graf5=hc_graf5, imagen=imagen,ppc=ppc,ppv=ppv, ts=ts)





### ID INFORME IC0004 ###
### modificado 12/01/2023
# @auth.requires_membership('encargados')
@auth.requires(auth.has_membership(auth.id_group('admins')) or auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('encargados_sucursal')) or auth.has_membership(auth.id_group('rrhh')))
def ventas_x_depo():
	data = data_graf = desde = hasta = sucursal=""
	form=SQLFORM.factory(
 	Field('desde', 'date', requires=IS_DATE()),
 	Field('hasta', 'date', requires=IS_DATE()),
 	Field('sucursal', requires=IS_EMPTY_OR(IS_IN_DB(db, 'sucursales.nro', '%(nombre)s'))))
 	if form.process().accepted:
 		mon_d=form.vars.desde.month 
 		day_d=form.vars.desde.day
 		mon_h=form.vars.hasta.month
 		day_h=form.vars.hasta.day
 		desde=form.vars.desde
 		hasta=form.vars.hasta
 		sucursal=form.vars.sucursal

 		#guarda los params en una var de session para usarlo en los informes colgados de este
 		session.ventas_x_depo=[mon_d,day_d,mon_h,day_h,desde,hasta,sucursal]
 	 	
 		var_depo="AND omicron_ventas1.deposito=%s "%form.vars.sucursal if form.vars.sucursal is not None else ""

 	 	#query a la db con funcion + abajo (lin 715 aprox.)
	 	# query_ventas=get_ventas_depo_histo(mon_d,day_d,mon_h,day_h,sucursal)

	 	sql_minyea = "SELECT MIN(YEAR(fecha)) as minyea FROM omicron_ventas1"

	 	minyea = db1.executesql(sql_minyea, as_dict=True)

	 	### rango de años para realizar las querys		
		rango = range(minyea[0]['minyea'], form.vars.hasta.year+1)
		
		### diferencia en entre los años de la fechas, por las dudas que sean en distintos años
		difyea = int(form.vars.hasta.year) - int(form.vars.desde.year)

		###período consultado
		percon = '%s-%s'%(form.vars.desde.year, form.vars.hasta.year)

		### datos vacíos
		data = []

		for y in rango:

			texto_sql="SELECT SUM((CASE WHEN omicron_ventas1.operacion='+' THEN omicron_ventas1.cantidad WHEN omicron_ventas1.operacion='-' THEN -omicron_ventas1.cantidad END)) as items, "\
			"SUM((CASE WHEN omicron_ventas1.operacion='+' THEN omicron_ventas1.monto_facturado END) / 1.21) AS totalvent, "\
			"SUM((CASE WHEN omicron_ventas1.operacion='-' THEN omicron_ventas1.precio END) / 1.21) AS totaldevs, "\
			"'%s-%s' AS yea , articulo.marca, marcas.descripcion "%(y, y+difyea)+\
			"FROM omicron_ventas1 "\
			"LEFT JOIN articulo ON omicron_ventas1.articulo=articulo.codigo "\
			"LEFT JOIN marcas ON articulo.marca=marcas.codigo "\
			"WHERE omicron_ventas1.codigo<>7 "\
			+ var_depo +\
			" AND omicron_ventas1.fecha>='%s-%s-%s' AND omicron_ventas1.fecha<='%s-%s-%s' "\
			"GROUP BY articulo.marca, marcas.descripcion, DATEPART(YEAR, omicron_ventas1.fecha)"%(y, form.vars.desde.month, form.vars.desde.day , y+difyea, form.vars.hasta.month, form.vars.hasta.day)

			res = db1.executesql(texto_sql)

			if len(res)>0:
			 	for x in res:
					data.append(x)

		### fin query


 	 	#armo un df
		dfv=pandas.DataFrame.from_records(data,columns=['items','ventas','devs','yea','cod_marca','marca'])

		dfv['devs'] = dfv['devs'].fillna(0)

		### calculo el monto = ventas - devoluciones
		dfv['items']=dfv['items'].astype(float)
		dfv['monto']=(dfv['ventas'].astype(float)-dfv['devs'].astype(float)).round(2)

		### borro, ya tengo el monto
		del dfv['ventas']
		del dfv['devs']

		### saco la data para el per consultado
		dfv_consultado = dfv[dfv['yea']==percon]

		### vuelco la data un JSON
		data = pandas.DataFrame(dfv_consultado.to_records()).to_json(orient='records')

		#armo la serie de datos para highcharts
		ventas={'name':'Ventas'}#creo la serie de ventas
		dfv['yea']=dfv['yea'].astype(str)
		xvl=dfv[['items','yea']].groupby(['yea'], as_index=False).sum().sort_values('yea').values.tolist()#extraigo las columnas que quiero, las agrupo por año, las ordeno y las convierto a lista
		ventas['data']=xvl#agrego los datos de la serie
		data_graf=[ventas]#armo el array
		data_graf=json.dumps(data_graf)#armo el json
	return dict(id_informe='IC0004', form=form, data=data, data_graf=data_graf ,desde=desde, hasta=hasta, sucursal=sucursal, permisos='encargados|usuarios_nivel_1|rrhh')	




























## ID INFORME IC0005 ###
@auth.requires(auth.has_membership(auth.id_group('admins')) or auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('encargados_sucursal')))
def ventas_x_depo_marca():
	if request.args(0):
		#vars para la sql query, están en session, vienen de ventas_x_depo
		mon_d,day_d,mon_h,day_h,desde,hasta,sucursal=session.ventas_x_depo
		#query a la db,es una func. mas abajo
		query_ventas=get_ventas_depo_histo_marca(mon_d,day_d,mon_h,day_h,sucursal,request.args(0))
		#armo el df de pandas
		dfv=dfvi=pandas.DataFrame.from_records(query_ventas,columns=['items','yea','csr','articulo','marca'])
		#formateo valores para evitar errores en windows
		dfv['items']=dfv['items'].astype(float)
		dfvi['items']=dfv['items'].astype(float)
		#agrego la img al df, está en models/funciones ???
		# dfvi['imagen']=''
		# dfvi['imagen']=dfvi.apply(lambda x: get_imagen_mini(0,x['cod_articulo']), axis=1)
		dfvi['imagen']=dfvi.apply(lambda x: get_imagen_mini(x['csr']), axis=1)

		#pivoteo la data para tener los años como columnas
		dfv_pi=dfv.pivot_table(index=['csr','articulo','marca','imagen'], columns='yea', values='items').fillna(0)


		##totales por producto
		dfv_pi['total']=dfv_pi.sum(axis=1)


		#desconvierto y vuelvo a convertir a df los datos pivoteados para eliminar multiindex, y los mando a un json de pandas
		dfn=pandas.DataFrame(dfv_pi.to_records()).to_json(orient='records')
		#vuelco el json de pandas a un json común para que funcione Tabulator
		data=dfn

		#armo las columnas para Tabulator porque son dinámicas, van de acuerdo a la data pivoteada
		clxs="{formatter:'rownum'},"\
		"{title:'Cod.', field:'csr', sorter:'string', headerFilter:true},"\
		"{title:'Artículo', field:'articulo', sorter:'string', headerFilter:true},"
		for x in dfv_pi.columns.sort_values(ascending=False):
			clxs+=XML("{title:'%s', field:'%s', sorter:'number', topCalc:'sum'},"%(x,x))
		clxs+="{title:'', field:'imagen', formatter:'image', align:'center', width:120},"		

		#armo la serie de datos para highcharts
		ventas={'name':'Ventas'}#creo la serie de ventas
		xvl=dfv[['items','yea']].groupby(['yea'], as_index=False).sum().sort_values('yea').values.tolist()#extraigo las columnas que quiero, las agrupo por año, las ordeno y las convierto a lista
		ventas['data']=xvl#agrego los datos de la serie
		data_graf=[ventas]#armo el array
		data_graf=json.dumps(data_graf)#armo el json

	else:
		redirect(URL('informes_consolidados','ventas_x_depo'))

	return dict(id_informe='IC0005', data=data, data_graf=data_graf, cod_marca=request.args(0), marca=dfv['marca'].iloc[0], clxs=clxs)


### ID INFORME IC0006 07/06/2021 ###
# @auth.requires_membership('encargados')
### modificado el 04/01/2023
@auth.requires(auth.has_membership(auth.id_group('admins')) or auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('encargados_sucursal')))
def compras_x_depo():
	data = data_graf = desde = hasta = sucursal= clxs = ""
	form=SQLFORM.factory(
 	Field('desde', 'date', requires=IS_DATE()),
 	Field('hasta', 'date', requires=IS_DATE()),
 	Field('sucursal', requires=IS_EMPTY_OR(IS_IN_DB(db, 'sucursales.nro', '%(nombre)s'))),
 	Field('linea', requires=IS_EMPTY_OR(IS_IN_DB(db1, 'lineas.codigo', '%(descripcion)s', multiple=True))),
	Field('marca', requires=IS_EMPTY_OR(IS_IN_DB(db1, 'marcas.codigo', '%(descripcion)s', multiple=True))),
	Field('rubro', requires=IS_EMPTY_OR(IS_IN_DB(db1, 'rubros.codigo', '%(descripcion)s', multiple=True))),
	Field('subrubro', requires=IS_EMPTY_OR(IS_IN_DB(db1, 'subrubro.codigo', '%(descripcion)s', multiple=True))),
	Field('agrupador', requires=IS_EMPTY_OR(IS_IN_DB(db_omicronvt, 'agrupador_marca', '%(nombre)s'))),
	Field('agrupador_subrubro', requires=IS_EMPTY_OR(IS_IN_DB(db_omicronvt, 'agrupador_subrubro', '%(nombre)s'))),
	Field('agrupador_rubro', requires=IS_EMPTY_OR(IS_IN_DB(db_omicronvt, 'agrupador_rubro', '%(nombre)s'))),

 	)
 	if form.process().accepted:
 		mon_d=form.vars.desde.month 
 		day_d=form.vars.desde.day
 		mon_h=form.vars.hasta.month
 		day_h=form.vars.hasta.day
 		desde=form.vars.desde
 		hasta=form.vars.hasta
 		sucursal=form.vars.sucursal
 		linea = marca = rubro = subrubro = None
 		if form.vars.linea:
 			linea = int(form.vars.linea[0]) if len(form.vars.linea)==1 else ','.join(form.vars.linea)
 		if form.vars.marca:
	 		marca = int(form.vars.marca[0]) if len(form.vars.marca)==1 else ','.join(form.vars.marca)
 		if form.vars.rubro:
 			rubro = int(form.vars.rubro[0]) if len(form.vars.rubro)==1 else ','.join(form.vars.rubro)
 		if form.vars.subrubro:
 			subrubro = int(form.vars.subrubro[0]) if len(form.vars.subrubro)==1 else ','.join(form.vars.subrubro)

 		#guarda los params en una var de session para usarlo en los informes colgados de este
 		session.compras_x_depo=[mon_d,day_d,mon_h,day_h,desde,hasta,sucursal]
 	 	
 		### query
 		var_sucursal="AND compras1.deposito=%s "%sucursal if sucursal is not None else ""
		var_linea =' AND articulo.linea IN (%s)'%linea if linea else ''		
		var_marca =' AND articulo.marca IN (%s)'%marca if marca else ''
		var_rubro =' AND articulo.rubro IN (%s)'%rubro if rubro else ''
		var_subrubro =' AND articulo.subrubro IN (%s)'%subrubro if subrubro else ''

		### agrupadores
		var_agrupador = var_agrupador_rubro = var_agrupador_subrubro = ''
		if form.vars.agrupador:
			q = db_omicronvt(db_omicronvt.agrupador_marca.id==form.vars.agrupador).select().first()
			var_agrupador = ' AND articulo.marca IN (%s)'%q.marcas_codigo
		if form.vars.agrupador_rubro:
			q = db_omicronvt(db_omicronvt.agrupador_rubro.id==form.vars.agrupador_rubro).select().first()
			var_agrupador_rubro = ' AND articulo.rubro IN (%s)'%q.rubros_codigo
		if form.vars.agrupador_subrubro:
			q = db_omicronvt(db_omicronvt.agrupador_subrubro.id==form.vars.agrupador_subrubro).select().first()
			var_agrupador_subrubro = ' AND articulo.subrubro IN (%s)'%q.subrubros_codigo

		###### OBTENER COMPRAS EN EL MISMO PERIODO PARA TODOS LOS AÑOS #############################################################################################
		###Buscar el año mas antiguo con compras
		### No lo pude resolver con una sola query, lo hago con multiples querys

		sql_minyea = "SELECT MIN(YEAR(fecha)) as minyea "\
		"FROM compras1 "\
		"LEFT JOIN articulo ON compras1.articulo=articulo.codigo "\
		"LEFT JOIN marcas ON articulo.marca=marcas.codigo "\
		"WHERE compras1.codigo NOT IN (7,36) AND articulo.marca NOT IN %s "%str(marcas_excluidas)\
		+ var_sucursal + var_linea + var_marca + var_rubro + var_subrubro + var_agrupador + var_agrupador_rubro + var_agrupador_rubro

		minyea = dbC.executesql(sql_minyea, as_dict=True)

		### rango de años para realizar las querys		
		rango = range(minyea[0]['minyea'], form.vars.hasta.year+1)
		
		### diferencia en entre los años de la fechas, por las dudas que sean en distintos años
		difyea = int(form.vars.hasta.year) - int(form.vars.desde.year)

		###período consultado
		percon = '%s-%s'%(form.vars.desde.year, form.vars.hasta.year)

		### datos vacíos
		data = []

		for y in rango:

			sql_text="SELECT SUM((CASE WHEN compras1.operacion='+' THEN compras1.cantidad WHEN compras1.operacion='-' THEN -compras1.cantidad END)) as items, "\
			"'%s-%s' as yea, articulo.marca as cod_marca, marcas.descripcion as marca "%(y, y+difyea)+\
			"FROM compras1 "\
			"LEFT JOIN articulo ON compras1.articulo=articulo.codigo "\
			"LEFT JOIN marcas ON articulo.marca=marcas.codigo "\
			"WHERE compras1.codigo NOT IN (7,36) AND articulo.marca NOT IN %s "%str(marcas_excluidas)\
			+ var_sucursal + var_linea + var_marca + var_rubro + var_subrubro + var_agrupador + var_agrupador_rubro + var_agrupador_rubro +\
			" AND compras1.fecha>='%s-%s-%s' AND compras1.fecha<='%s-%s-%s' "\
			"GROUP BY articulo.marca, marcas.descripcion"%(y, form.vars.desde.month, form.vars.desde.day , y+difyea, form.vars.hasta.month, form.vars.hasta.day)

			res = dbC.executesql(sql_text)

			if len(res)>0:
			 	for x in res:
					data.append(x)

		### fin query

 	 	#armo un df
		dfv=pandas.DataFrame.from_records(data, columns=['items','yea','cod_marca','marca'])

		dfv['items']=dfv['items'].astype(float)

		### pivoteo la data para tener los períodos como columnas
		dfv_pi=dfv.pivot_table(index=['cod_marca','marca'], columns='yea', values='items').fillna(0)
		#desconvierto y vuelvo a convertir a df los datos pivoteados para eliminar multiindex, y los mando a un json de pandas
		dfn=pandas.DataFrame(dfv_pi.to_records()).to_json(orient='records')
		#vuelco el json de pandas a un json común para que funcione Tabulator
		data=dfn

		#armo las columnas para Tabulator porque son dinámicas, van de acuerdo a la data pivoteada
		clxs="{formatter:'rownum'},"\
		"{title:'Cod.', field:'cod_marca', sorter:'string', headerFilter:true},"\
		"{title:'Marca', field:'marca', sorter:'string', headerFilter:true},"
		for x in dfv_pi.columns.sort_values(ascending=False):
			clxs+=XML("{title:'%s', field:'%s', sorter:'number'},"%(x,x))

		#armo la serie de datos para highcharts
		compras={'name':'Compras'}#creo la serie de ventas
		dfv['yea']=dfv['yea'].astype(str)
		xvl=dfv[['items','yea']].groupby(['yea'], as_index=False).sum().sort_values('yea').values.tolist()#extraigo las columnas que quiero, las agrupo por año, las ordeno y las convierto a lista
		compras['data']=xvl#agrego los datos de la serie
		data_graf=[compras]#armo el array
		data_graf=json.dumps(data_graf)#armo el json
	return dict(id_informe='IC0006', form=form, data=data, clxs=clxs, data_graf=data_graf ,desde=desde, hasta=hasta, sucursal=sucursal, mas_info='No incluye marcas : %s'%str(marcas_excluidas))

## ID INFORME IC0007 ###
@auth.requires(auth.has_membership(auth.id_group('admins')) or auth.has_membership(auth.id_group('usuarios_nivel_1')))
def compras_x_depo_marca():
	if request.args(0):
		#vars para la sql query, están en session, vienen de compras_x_depo
		mon_d,day_d,mon_h,day_h,desde,hasta,sucursal=session.compras_x_depo
		#query a la db,es una func. mas abajo
		query_compras=lx_get_compras_depo_histo_marca(mon_d,day_d,mon_h,day_h,sucursal,request.args(0))
		#armo el df de pandas
		dfv=dfvi=pandas.DataFrame.from_records(query_compras,columns=['items','yea','csr','articulo','marca'])
		#formateo valores para evitar errores en windows
		dfv['items']=dfv['items'].astype(float)
		dfvi['items']=dfv['items'].astype(float)
		#agrego la img al df, está en models/funciones ???
		# dfvi['imagen']=''
		# dfvi['imagen']=dfvi.apply(lambda x: get_imagen_mini(0,x['cod_articulo']), axis=1)
		
		dfvi['imagen']=dfvi.apply(lambda x: get_imagen_mini(x['csr']), axis=1)


		#pivoteo la data para tener los años como columnas
		dfv_pi=dfv.pivot_table(index=['csr','articulo','marca','imagen'], columns='yea', values='items').fillna(0)
		#desconvierto y vuelvo a convertir a df los datos pivoteados para eliminar multiindex, y los mando a un json de pandas
		dfn=pandas.DataFrame(dfv_pi.to_records()).to_json(orient='records')
		#vuelco el json de pandas a un json común para que funcione Tabulator
		data=dfn

		#armo las columnas para Tabulator porque son dinámicas, van de acuerdo a la data pivoteada
		clxs="{formatter:'rownum'},"\
		"{title:'Cod.', field:'csr', sorter:'string', headerFilter:true},"\
		"{title:'Artículo', field:'articulo', sorter:'string', headerFilter:true},"
		for x in dfv_pi.columns.sort_values(ascending=False):
			clxs+=XML("{title:'%s', field:'%s', sorter:'number'},"%(x,x))
		clxs+="{title:'', field:'imagen', formatter:'image', align:'center', width:120},"		

		#armo la serie de datos para highcharts
		compras={'name':'Compras'}#creo la serie de ventas
		xvl=dfv[['items','yea']].groupby(['yea'], as_index=False).sum().sort_values('yea').values.tolist()#extraigo las columnas que quiero, las agrupo por año, las ordeno y las convierto a lista
		compras['data']=xvl#agrego los datos de la serie
		data_graf=[compras]#armo el array
		data_graf=json.dumps(data_graf)#armo el json

	else:
		redirect(URL('informes_consolidados','compras_x_depo'))

	return dict(id_informe='IC0007', data=data, data_graf=data_graf, cod_marca=request.args(0), marca=dfv['marca'].iloc[0], clxs=clxs)








########################################################## FUNCIONES ############################################################################################
#################################################################################################################################################################
## 12/12/18 se comienza a usar vista(MSSQL) consolidada omicron_compras1_remitos, que tiene los remitos de compra(7) y devolución(36)
## 30/08/2024 se mueven a models/funciones_informes_consolidados porque se usan también desde: informes_encargados_sucursal


# #USA VISTA CONSOLIDADA: dbo.omicron_compras1_remitos 12/12/18
# # def get_compras_consolidado(desde,hasta,linea,marca,rubro,subrubro,agrupador, agrupador_subrubro, agrupador_rubro, sinonimo):
# def get_compras_consolidado(**kwargs):	

# 	filtros = fx_filtros_art(**kwargs)


# 	t_sql="SELECT SUM((CASE WHEN r.operacion='+' THEN r.cantidad WHEN r.operacion='-' THEN -r.cantidad END)) as items, "\
# 		"SUM((CASE WHEN r.operacion='+' THEN r.monto_facturado END)) AS totalcomp, "\
# 		"SUM((CASE WHEN r.operacion='-' THEN r.precio END)) AS totaldevs, "\
# 		"a.marca, m.descripcion FROM omicron_compras1_remitos r "\
# 		"LEFT JOIN articulo a ON r.articulo=a.codigo "\
# 		"LEFT JOIN marcas m ON a.marca=m.codigo "\
# 		"WHERE r.fecha>='%s' AND r.fecha<='%s'"%(kwargs['desde'], kwargs['hasta'])\
# 		+ filtros +\
# 		"GROUP BY a.marca, m.descripcion"

# 	# texto_sql="SELECT SUM((CASE WHEN omicron_compras1_remitos.operacion='+' THEN omicron_compras1_remitos.cantidad WHEN omicron_compras1_remitos.operacion='-' THEN -omicron_compras1_remitos.cantidad END)) as items, "\
# 	# 	"SUM((CASE WHEN omicron_compras1_remitos.operacion='+' THEN omicron_compras1_remitos.monto_facturado END)) AS totalcomp, "\
# 	# 	"SUM((CASE WHEN omicron_compras1_remitos.operacion='-' THEN omicron_compras1_remitos.precio END)) AS totaldevs, "\
# 	# 	"articulo.marca, marcas.descripcion, omicron_compras1_remitos.deposito FROM omicron_compras1_remitos "\
# 	# 	"LEFT JOIN articulo ON omicron_compras1_remitos.articulo=articulo.codigo "\
# 	# 	"LEFT JOIN marcas ON articulo.marca=marcas.codigo "\
# 	# 	"WHERE omicron_compras1_remitos.fecha>='%s' AND omicron_compras1_remitos.fecha<='%s'"\
# 	# 	%(desde,hasta)  + var_linea + var_marca + var_rubro + var_subrubro +var_agrupador + var_agrupador_subrubro+ var_agrupador_rubro+\
# 	# 	"GROUP BY articulo.marca, marcas.descripcion, omicron_compras1_remitos.deposito"


# 	data=db1.executesql(t_sql)	
# 	return data



# ### MODIFICADO 17/01/23 PARA CALCULAR RENTABILIDAD EN BASE A PRECIO DE COSTO(ESTA EN LA VENTA)
# #USA VISTA CONSOLIDADA : dbo.omicron_ventas1
# #Devuelve: Unidades vendidas, total ventas sin iva, total devoluciones sin iva,codigo de marca, descripcion de marca
# def get_ventas_consolidado(**kwargs):

# 	filtros = fx_filtros_art(**kwargs)

# 	t_sql = "SELECT SUM((CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END)) as cant, "\
# 		"SUM((case when v.operacion='+' then v.precio when v.operacion='-' then -v.precio end) / 1.21 * v.cantidad)  AS totalvent, "\
# 		"SUM(case when v.operacion='+' then v.precio_costo when v.operacion='-' then -v.precio_costo end * v.cantidad) as costovent,"\
# 		"a.marca, m.descripcion, v.deposito FROM omicron_ventas1 v "\
# 		"LEFT JOIN articulo a ON v.articulo=a.codigo "\
# 		"LEFT JOIN marcas m ON a.marca=m.codigo "\
# 		"LEFT JOIN subrubro s ON a.subrubro=s.codigo "\
# 		"WHERE v.codigo<>7 AND v.fecha>='%s' AND v.fecha<='%s'"%(kwargs['desde'], kwargs['hasta'])\
# 		+ filtros +\
# 		"GROUP BY a.marca, m.descripcion, v.deposito"

# 	data=db1.executesql(t_sql)

# 	return data


# ### 19/07/22, STOCK FILTRADO PARA rank_marcas_comp_vent
# #def get_stock_consolidado(lista_marcas, linea,rubro,subrubro, agrupador_rubro, agrupador_subrubro):
# ### 11/08/23
# ##depos_para_informes se define en models/tablas1.py
# def get_stock_consolidado(**kwargs):	

# 	filtros = fx_filtros_art(**kwargs)

# 	t_sql="SELECT SUM(ws.stock_actual), MAX(m.codigo), MAX(ws.deposito) FROM articulo a "\
# 		"LEFT JOIN web_stock ws ON ws.articulo=a.codigo "\
# 		"LEFT JOIN marcas m on m.codigo=a.marca "\
# 		"WHERE a.marca>0 AND ws.deposito in {0} ".format(depos_para_informes)\
# 		+ filtros +\
# 		"GROUP BY a.marca, ws.deposito"

# 	data = db1.executesql(t_sql)

# 	return data



# ############################################################ FUNCIONES PARA /informes_consolidados/rank_productos_xmarca #############################################################

# ## Datos para Tabulator
# #Devuelve: Unidades compradas, total compras sin iva, total devoluciones sin iva,codigo de marca, descripcion de marca
# # @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('admins')))
# #def get_compras_consolidado_xmarca(desde,hasta,linea,marca,rubro,subrubro, agrupador_subrubro, agrupador_rubro, sinonimo):
# def get_compras_consolidado_xmarca(**kwargs):	


# 	filtros = fx_filtros_art(**kwargs)
	
# 	t_sql = "SELECT SUM((CASE WHEN rc.operacion='+' THEN rc.cantidad WHEN rc.operacion='-' THEN -rc.cantidad END)) as items, "\
# 		"SUM((CASE WHEN rc.operacion='+' THEN rc.monto_facturado END)) AS totalcomp, "\
# 		"SUM((CASE WHEN rc.operacion='-' THEN rc.precio END)) AS totaldevs, "\
# 		"LEFT(a.codigo_sinonimo,10) as csr "\
# 		"FROM omicron_compras1_remitos rc "\
# 		"LEFT JOIN articulo a ON rc.articulo=a.codigo "\
# 		"LEFT JOIN marcas m ON a.marca=m.codigo "\
# 		"LEFT JOIN subrubro s ON a.subrubro=s.codigo "\
# 		"LEFT JOIN rubros r ON a.rubro=r.codigo "\
# 		"WHERE rc.fecha>='%s' AND rc.fecha<='%s' "%(kwargs['c_desde'],kwargs['c_hasta'])\
# 		+ filtros +\
# 		"GROUP BY left(a.codigo_sinonimo,10)"

# 	data=db1.executesql(t_sql)		

# 	return data	


# ### MODIFICADA 17/01/23 PARA OBTENER RENTABILIDAD DE VENTA, SE CALCULA EN LA FUNCION PRINCIPAL
# #Devuelve: Unidades vendidas, total ventas sin iva, total devoluciones sin iva,codigo de marca, descripcion de marca

# # @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('admins')))
# def get_ventas_consolidado_xmarca(**kwargs):

	
# 	filtros = fx_filtros_art(**kwargs)

# 	t_sql = "SELECT SUM((CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END)) as items, "\
# 		"SUM((case when v.operacion='+' then v.precio when v.operacion='-' then -v.precio end) / 1.21 * v.cantidad)  AS totalvent, "\
# 		"SUM(case when v.operacion='+' then v.precio_costo when v.operacion='-' then -v.precio_costo end * v.cantidad) as costovent, "\
# 		"LEFT(a.codigo_sinonimo,10) as csr "\
# 		"FROM omicron_ventas1 v "\
# 		"LEFT JOIN articulo a ON v.articulo=a.codigo "\
# 		"LEFT JOIN marcas m ON a.marca=m.codigo "\
# 		"LEFT JOIN subrubro s ON a.subrubro=s.codigo "\
# 		"LEFT JOIN rubros r ON a.rubro=r.codigo "\
# 		"WHERE v.codigo<>7 AND v.fecha>='%s' AND v.fecha<='%s' "%(kwargs['v_desde'], kwargs['v_hasta'])\
# 		+ filtros +\
# 		"GROUP BY left(a.codigo_sinonimo,10)"

# 	data=db1.executesql(t_sql)

# 	return data

# ### PID-221
# ##depos_para_informes se define en models/tablas1.py
# def get_stock_consolidado_xmarca(**kwargs):

# 	filtros = fx_filtros_art(**kwargs)

# 	t_sql="SELECT SUM(s.stock_actual), s.deposito, a.csr "\
# 		"FROM omicron_articulos a "\
# 		"LEFT JOIN web_stock s ON a.codigo=s.articulo "\
# 		"WHERE a.marca=%s AND s.deposito in %s "%(kwargs['marca'], depos_para_informes)\
# 		+ filtros +\
# 		"GROUP BY s.deposito, csr HAVING SUM(s.stock_actual)>0"

# 	data=db1.executesql(t_sql)

# 	return data


# # ##depos_para_informes se define en models/tablas1.py
# # def get_stock_consolidado_xmarca(**kwargs):

# # 	filtros = fx_filtros_art(**kwargs)

# # 	t_sql="SELECT SUM(s.stock_actual), s.deposito, left(a.codigo_sinonimo, len(a.codigo_sinonimo)-2) "\
# # 		"FROM web_articulo a "\
# # 		"LEFT JOIN web_stock s ON a.codigo=s.articulo "\
# # 		"WHERE a.marca=%s AND len(a.codigo_sinonimo)>5 AND s.deposito in %s "%(kwargs['marca'], depos_para_informes)\
# # 		+ filtros +\
# # 		"GROUP BY s.deposito, left(a.codigo_sinonimo, len(a.codigo_sinonimo)-2) HAVING SUM(s.stock_actual)>0"

# # 	data=db1.executesql(t_sql)

# # 	return data






# def get_distrib_ventas_xmarca(**kwargs):

# 	filtros = fx_filtros_art(**kwargs)

# 	t_sql = "SELECT SUM((CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END)), v.deposito, left(a.codigo_sinonimo, len(a.codigo_sinonimo)-2) "\
# 		"FROM web_articulo a "\
# 		"LEFT JOIN omicron_ventas1 v ON a.codigo=v.articulo "\
# 		"WHERE LEN(a.codigo_sinonimo)=12 AND a.marca=%s "%kwargs['marca']\
# 		+ filtros +\
# 		"GROUP BY v.deposito, left(a.codigo_sinonimo, len(a.codigo_sinonimo)-2)"

# 	data=db1.executesql(t_sql)

# 	return data


# ########## DATA PARA GRAFICOS DE : informes_consolidados/rank_productos_xmarca   ################################################################################################################################

# # @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('admins')))
# # def get_compras_consolidado_xmarca_graf_anmes(linea,marca,rubro,subrubro, agrupador_subrubro):
# def get_compras_consolidado_xmarca_graf_anmes(**kwargs):

	
# 	filtros = fx_filtros_art(**kwargs)

# 	data=db1.executesql("SELECT SUM((CASE WHEN rc.operacion='+' THEN rc.cantidad WHEN rc.operacion='-' THEN -rc.cantidad END)) as items, "\
# 		"CONCAT(DATEPART(YEAR, rc.fecha),'-',CONVERT(char(2), rc.fecha,101)) AS anmes, "\
# 		"DATEPART(YEAR, rc.fecha) AS an, DATEPART(MONTH, rc.fecha) as me "\
# 		"FROM omicron_compras1_remitos rc "\
# 		"LEFT JOIN articulo a ON rc.articulo=a.codigo "\
# 		"LEFT JOIN marcas m ON a.marca=m.codigo "\
# 		"WHERE a.codigo>1 "\
# 		+ filtros +\
# 		"GROUP BY CONCAT(DATEPART(YEAR, rc.fecha),'-',CONVERT(char(2), rc.fecha,101)), "\
# 		"DATEPART(YEAR, rc.fecha), DATEPART(MONTH, rc.fecha)")		

# 	return data	
# #Devuelve: Unidades vendidas, total ventas sin iva, total devoluciones sin iva,codigo de marca, descripcion de marca

# # @auth.requires_membership('usuarios_nivel_1')
# def get_ventas_consolidado_xmarca_graf_anmes(**kwargs):

# 	filtros = fx_filtros_art(**kwargs)

# 	data=db1.executesql("SELECT SUM((CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END)) as items, "\
# 		"CONCAT(DATEPART(YEAR, v.fecha),'-',CONVERT(char(2), v.fecha,101)) AS anmes, "\
# 		"DATEPART(YEAR, v.fecha) AS an, DATEPART(MONTH, v.fecha) as me "\
# 		"FROM omicron_ventas1 v "\
# 		"LEFT JOIN articulo a ON v.articulo=a.codigo "\
# 		"LEFT JOIN marcas m ON a.marca=m.codigo "\
# 		"WHERE v.codigo<>7 "\
# 		+ filtros +\
# 		"GROUP BY CONCAT(DATEPART(YEAR, v.fecha),'-',CONVERT(char(2), v.fecha,101)), "\
# 		"DATEPART(YEAR, v.fecha), DATEPART(MONTH, v.fecha)")
# 	return data

# # @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('admins')))
# def get_compras_consolidado_xmarca_graf_mes(**kwargs):

# 	filtros = fx_filtros_art(**kwargs)
	
# 	data=db1.executesql("SELECT SUM((CASE WHEN rc.operacion='+' THEN rc.cantidad WHEN rc.operacion='-' THEN -rc.cantidad END)) as items, "\
# 		"CONVERT(char(2), rc.fecha,101) AS mes "\
# 		"FROM omicron_compras1_remitos rc "\
# 		"LEFT JOIN articulo a ON rc.articulo=a.codigo "\
# 		"LEFT JOIN marcas m ON a.marca=m.codigo "\
# 		"WHERE a.codigo>1 "\
# 		+ filtros +\
# 		"GROUP BY CONVERT(char(2), rc.fecha,101) "\
# 		"ORDER BY 2")		
# 	return data
# #Devuelve: Unidades vendidas, total ventas sin iva, total devoluciones sin iva,codigo de marca, descripcion de marca

# # @auth.requires_membership('usuarios_nivel_1')
# def get_ventas_consolidado_xmarca_graf_mes(**kwargs):


# 	filtros = fx_filtros_art(**kwargs)
	
	
# 	# ### REEMPLAZADO POR EL DE ABAJO - PID-223 - 20240118
# 	# t_sql = "SELECT SUM((CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END)) as items, "\
# 	# 	"CONVERT(char(2), v.fecha,101) AS mes "\
# 	# 	"FROM omicron_ventas1 v "\
# 	# 	"LEFT JOIN articulo a ON v.articulo=a.codigo "\
# 	# 	"LEFT JOIN marcas m ON a.marca=m.codigo "\
# 	# 	"WHERE v.codigo<>7 "\
# 	# 	+ filtros +\
# 	# 	"GROUP BY CONVERT(char(2), v.fecha,101) "\
# 	# 	"ORDER BY 2"

# 	t_sql = "SELECT CAST(SUM(i.items) AS INT) AS items, i.mes AS mes, CAST(SUM(i.items)/COUNT(i.yeames) AS INT) as promedio FROM "\
# 		"(SELECT SUM((CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END)) as items, "\
# 		"CONCAT(YEAR(fecha),'-',MONTH(fecha)) as yeames, MAX(CONVERT(char(2), v.fecha,101)) as mes "\
# 		"FROM omicron_ventas1 v "\
# 		"LEFT JOIN articulo a ON v.articulo=a.codigo "\
# 		"LEFT JOIN marcas m ON a.marca=m.codigo "\
# 		"WHERE v.codigo<>7 "\
# 		+ filtros +\
# 		"GROUP BY CONCAT(YEAR(fecha),'-',MONTH(fecha))) i "\
# 		"GROUP BY (i.mes)"

# 	data=db1.executesql(t_sql)
# 	return data	

# #retorna las compras por curva de un producto
# # @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('admins')))
# def get_compras_curva_producto(desde,hasta,csr):
# 	data=db1.executesql("SELECT SUM((CASE WHEN omicron_compras1_remitos.operacion='+' THEN omicron_compras1_remitos.cantidad WHEN omicron_compras1_remitos.operacion='-' THEN -omicron_compras1_remitos.cantidad END)) as items, "\
# 			"SUM((CASE WHEN omicron_compras1_remitos.operacion='+' THEN omicron_compras1_remitos.monto_facturado END)) AS totalcomp, "\
# 			"SUM((CASE WHEN omicron_compras1_remitos.operacion='-' THEN omicron_compras1_remitos.precio END)) AS totaldevs, "\
# 			"articulo.codigo_sinonimo, articulo.descripcion_5, "\
# 			"omicron_compras1_remitos.fecha "\
# 			"FROM omicron_compras1_remitos "\
# 			"LEFT JOIN articulo ON omicron_compras1_remitos.articulo=articulo.codigo "\
# 			"LEFT JOIN marcas ON articulo.marca=marcas.codigo "\
# 			"WHERE omicron_compras1_remitos.fecha>='%s' AND omicron_compras1_remitos.fecha<='%s' AND articulo.codigo_sinonimo like '%s' "\
# 			"GROUP BY articulo.descripcion_5, articulo.codigo_sinonimo, omicron_compras1_remitos.fecha"%(desde,hasta,csr+'%'))
# 	return data

# #retorna las ventas por curva de un producto
# # @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('admins')))
# def get_ventas_curva_producto(desde,hasta,csr):
# 	data=db1.executesql("SELECT SUM((CASE WHEN omicron_ventas1.operacion='+' THEN omicron_ventas1.cantidad WHEN omicron_ventas1.operacion='-' THEN -omicron_ventas1.cantidad END)) as items, "\
# 			"SUM((CASE WHEN omicron_ventas1.operacion='+' THEN omicron_ventas1.monto_facturado END) / 1.21) AS totalcomp, "\
# 			"SUM((CASE WHEN omicron_ventas1.operacion='-' THEN omicron_ventas1.precio END) / 1.21) AS totaldevs, "\
# 			"articulo.codigo_sinonimo, articulo.descripcion_5, "\
# 			"omicron_ventas1.fecha "\
# 			"FROM omicron_ventas1 "\
# 			"LEFT JOIN articulo ON omicron_ventas1.articulo=articulo.codigo "\
# 			"LEFT JOIN marcas ON articulo.marca=marcas.codigo "\
# 			"WHERE omicron_ventas1.codigo<>7 AND omicron_ventas1.fecha>='%s' AND omicron_ventas1.fecha<='%s' AND articulo.codigo_sinonimo like '%s' "\
# 			"GROUP BY articulo.descripcion_5, articulo.codigo_sinonimo, omicron_ventas1.fecha"%(desde,hasta,csr+'%'))
# 	return data


# ################ DATOS PARA GRAFICO ############################################################################################################################################################################
# #retorna las compras por curva de un producto

# # @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('admins')))
# def get_compras_curva_producto_anmes(csr):
# 	data=db1.executesql("SELECT SUM((CASE WHEN omicron_compras1_remitos.operacion='+' THEN omicron_compras1_remitos.cantidad WHEN omicron_compras1_remitos.operacion='-' THEN -omicron_compras1_remitos.cantidad END)) as items, "\
# 			"CONCAT(DATEPART(YEAR, omicron_compras1_remitos.fecha),'-',CONVERT(char(2),omicron_compras1_remitos.fecha,101)) AS anmes "\
# 			"FROM omicron_compras1_remitos "\
# 			"LEFT JOIN articulo ON omicron_compras1_remitos.articulo=articulo.codigo "\
# 			"WHERE articulo.codigo_sinonimo like '%s' "\
# 			"GROUP BY CONCAT(DATEPART(YEAR, omicron_compras1_remitos.fecha),'-',CONVERT(char(2),omicron_compras1_remitos.fecha,101)) "\
# 			"ORDER BY 2"%(csr+'%'))
# 	return data

# #retorna las ventas por curva de un producto
# # @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('admins')))
# def get_ventas_curva_producto_anmes(csr):
# 	data=db1.executesql("SELECT SUM((CASE WHEN omicron_ventas1.operacion='+' THEN omicron_ventas1.cantidad WHEN omicron_ventas1.operacion='-' THEN -omicron_ventas1.cantidad END)) as items, "\
# 			"CONCAT(DATEPART(YEAR, omicron_ventas1.fecha),'-',CONVERT(char(2),omicron_ventas1.fecha,101)) AS anmes "\
# 			"FROM omicron_ventas1 "\
# 			"LEFT JOIN articulo ON omicron_ventas1.articulo=articulo.codigo "\
# 			"WHERE omicron_ventas1.codigo<>7 AND articulo.codigo_sinonimo like '%s' "\
# 			"GROUP BY CONCAT(DATEPART(YEAR, omicron_ventas1.fecha),'-',CONVERT(char(2),omicron_ventas1.fecha,101)) "\
# 			"ORDER BY 2"%(csr+'%'))
# 	return data
# #retorna las compras por curva de un producto

# # @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('admins')))
# def get_compras_curva_producto_mes(csr):
# 	data=db1.executesql("SELECT SUM((CASE WHEN omicron_compras1_remitos.operacion='+' THEN omicron_compras1_remitos.cantidad WHEN omicron_compras1_remitos.operacion='-' THEN -omicron_compras1_remitos.cantidad END)) as items, "\
# 			"CONVERT(char(2),omicron_compras1_remitos.fecha,101) AS mes "\
# 			"FROM omicron_compras1_remitos "\
# 			"LEFT JOIN articulo ON omicron_compras1_remitos.articulo=articulo.codigo "\
# 			"WHERE articulo.codigo_sinonimo like '%s' "\
# 			"GROUP BY CONVERT(char(2),omicron_compras1_remitos.fecha,101) "\
# 			"ORDER BY 2"%(csr+'%'))
# 	return data

# #retorna las ventas por curva de un producto
# # @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('admins')))
# def get_ventas_curva_producto_mes(csr):
# 	data=db1.executesql("SELECT SUM((CASE WHEN omicron_ventas1.operacion='+' THEN omicron_ventas1.cantidad WHEN omicron_ventas1.operacion='-' THEN -omicron_ventas1.cantidad END)) as items, "\
# 			"CONVERT(char(2),omicron_ventas1.fecha,101) AS mes "\
# 			"FROM omicron_ventas1 "\
# 			"LEFT JOIN articulo ON omicron_ventas1.articulo=articulo.codigo "\
# 			"WHERE omicron_ventas1.codigo<>7 AND articulo.codigo_sinonimo like '%s' "\
# 			"GROUP BY CONVERT(char(2),omicron_ventas1.fecha,101) "\
# 			"ORDER BY 2"%(csr+'%'))
# 	return data	

# #funcion para calcular temporas de ventas
# def season_calc(mes,yea,tipo):
# 	if tipo==0:
# 		if mes in (2,3,4,5,6):
# 			season='%s-INV'%yea
# 		elif mes in (7,8,9,10,11,12):
# 			season='%s-VER'%yea
# 		elif mes==1:
# 			season='%s-VER'%(yea-1)
# 	elif tipo==1:
# 		if mes in (3,4,5,6,7,8):
# 			season='%s-INV'%yea
# 		elif mes in (9,10,11,12):
# 			season='%s-VER'%yea
# 		elif mes in (1,2):
# 			season='%s-VER'%(yea-1)
# 	return season

# #retorna solo ventas de un depo determinado en un período y marca determinados y su historial para años anteriores
# # @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('encargados_sucursal')))
# def get_ventas_depo_histo_marca(mon_d,day_d,mon_h,day_h,depo,marca):
# 	var_depo="AND omicron_ventas1.deposito=%s "%depo if depo is not None else ""
# 	data=db1.executesql("SELECT SUM((CASE WHEN omicron_ventas1.operacion='+' THEN omicron_ventas1.cantidad WHEN omicron_ventas1.operacion='-' THEN -omicron_ventas1.cantidad END)) as items, "\
# 		"DATEPART(YEAR, omicron_ventas1.fecha) AS yea , LEFT(articulo.codigo_sinonimo,len(articulo.codigo_sinonimo)-2) as csr, articulo.descripcion_1, marcas.descripcion "\
# 		"FROM omicron_ventas1 "\
# 		"LEFT JOIN articulo ON omicron_ventas1.articulo=articulo.codigo "\
# 		"LEFT JOIN marcas ON articulo.marca=marcas.codigo "\
# 		"WHERE omicron_ventas1.codigo<>7 "\
# 		# " AND omicron_ventas1.deposito=0 "\
# 		+ var_depo +\
# 		"AND DATEPART(MONTH, omicron_ventas1.fecha)>=%s AND DATEPART(DAY, omicron_ventas1.fecha)>=%s "\
# 		"AND DATEPART(MONTH, omicron_ventas1.fecha)<=%s AND DATEPART(DAY, omicron_ventas1.fecha)<=%s "\
# 		"AND marcas.codigo=%s "\
# 		"GROUP BY LEFT(articulo.codigo_sinonimo,len(articulo.codigo_sinonimo)-2), articulo.descripcion_1, marcas.descripcion, DATEPART(YEAR, omicron_ventas1.fecha)"%(mon_d,day_d,mon_h,day_h,marca))
# 	return data


# #retorna solo ventas de un depo determinado en un período y marca determinados y su historial para años anteriores
# # @auth.requires(auth.has_membership(auth.id_group('usuarios_nivel_1')) or auth.has_membership(auth.id_group('encargados_sucursal')))
# def lx_get_compras_depo_histo_marca(mon_d,day_d,mon_h,day_h,depo,marca):
# 	var_depo="AND compras1.deposito=%s "%depo if depo is not None else ""
# 	data=dbC.executesql("SELECT SUM((CASE WHEN compras1.operacion='+' THEN compras1.cantidad WHEN compras1.operacion='-' THEN -compras1.cantidad END)) as items, "\
# 		"DATEPART(YEAR, compras1.fecha) AS yea , LEFT(articulo.codigo_sinonimo,len(articulo.codigo_sinonimo)-2) as csr, articulo.descripcion_1, marcas.descripcion "\
# 		"FROM compras1 "\
# 		"LEFT JOIN articulo ON compras1.articulo=articulo.codigo "\
# 		"LEFT JOIN marcas ON articulo.marca=marcas.codigo "\
# 		"WHERE compras1.codigo NOT IN (7,36) "\
# 		# " AND omicron_ventas1.deposito=0 "\
# 		+ var_depo +\
# 		"AND DATEPART(MONTH, compras1.fecha)>=%s AND DATEPART(DAY, compras1.fecha)>=%s "\
# 		"AND DATEPART(MONTH, compras1.fecha)<=%s AND DATEPART(DAY, compras1.fecha)<=%s "\
# 		"AND marcas.codigo=%s "\
# 		"GROUP BY LEFT(articulo.codigo_sinonimo,len(articulo.codigo_sinonimo)-2), articulo.descripcion_1, marcas.descripcion, DATEPART(YEAR, compras1.fecha)"%(mon_d,day_d,mon_h,day_h,marca))
# 	return data


# ################################# FIN DESARROLLANDO 07/06/2021 ###########################################################




# def get_stock_curva(csr):
# 	qstock=db1.executesql("SELECT SUM(web_stock.stock_actual) AS stock, articulo.codigo_sinonimo, articulo.descripcion_5 FROM web_stock LEFT JOIN articulo ON articulo.codigo=web_stock.articulo "\
# 			"WHERE articulo.codigo_sinonimo like '%s' AND web_stock.deposito in %s GROUP BY articulo.codigo_sinonimo, articulo.descripcion_5"%(csr+'%', depos_para_informes))
# 	return qstock

# def marca_graf_tiempo(desde,hasta,marca):
# 	data=db1.executesql("")
# 	return data


# def func_grafico_1(**kwargs):
# 	#GRAFICO 1
# 	dam=pandas.DataFrame.from_records(get_compras_consolidado_xmarca_graf_anmes(**kwargs),columns=['cantidad_c','anmes','an','me'])#datos de compras
# 	damm=dam[['anmes','cantidad_c']]#cambio orden de las columnas de compras
# 	dav=pandas.DataFrame.from_records(get_ventas_consolidado_xmarca_graf_anmes(**kwargs),columns=['cantidad_v','anmes','an','me'])#datos de ventas
# 	davm=dav[['anmes','cantidad_v']]#cambio orden de las columnas de venta
# 	dat=pandas.merge(damm,davm, on=['anmes'], how='outer')#junto los 2 dfs
# 	dat['cantidad_c']=dat['cantidad_c'].astype(float).round(2)
# 	dat['cantidad_v']=dat['cantidad_v'].astype(float).round(2)
# 	serie_compras={'name':'Compras'}#creo la serie de compras
# 	xcl=dat[['anmes','cantidad_c']].sort_values('anmes').values.tolist()#solo las compras, ordeno por anmes y convierto a lista
# 	serie_compras['data']=xcl#armo los datos de la serie
# 	hc_datos=[serie_compras]#junto nombre y datos
# 	serie_ventas={'name':'Ventas'}#creo la serie de ventas
# 	xvl=dat[['anmes','cantidad_v']].sort_values('anmes').values.tolist()#solo las ventas, ordeno por anmes y convierto a lista
# 	serie_ventas['data']=xvl#armo los datos de la serie
# 	hc_datos.append(serie_ventas)#los agrego a las compras
# 	hc_graf=json.dumps(hc_datos, default=str)#default=str para que no de error serializando datetime
# 	return hc_graf

# def func_grafico_3(**kwargs):		
# 	#GRAFICO 3
# 	#----------------- compras -----------------------------------
# 	dfc3=pandas.DataFrame.from_records(get_compras_consolidado_xmarca_graf_anmes(**kwargs),columns=['cantidad','anmes','an','me'])#datos de compras
# 	dfc3['temp']=dfc3.apply(lambda x : season_calc(x['me'],x['an'],0), axis=1)#busco las compras historicas por temporada para cada producto
# 	dfc3=dfc3[['temp','cantidad']]#cambio orden de las columnas de compras
# 	dfc3['cantidad']=dfc3['cantidad'].astype(float).round(2)#si no tira error en windows
# 	dfc3=dfc3.groupby(['temp'], as_index=False).sum()#agrupo compras por temporada
# 	serie_compras3={'name':'Compras'}#creo la serie de compras
# 	xcl=dfc3[['temp','cantidad']].sort_values('temp').values.tolist()#solo las compras, ordeno por anmes y convierto a lista
# 	serie_compras3['data']=xcl#armo los datos de la serie
# 	#----------------- ventas ------------------------------------
# 	dfv3=pandas.DataFrame.from_records(get_ventas_consolidado_xmarca_graf_anmes(**kwargs),columns=['cantidad','anmes','an','me'])#datos de ventas
# 	dfv3['temp']=dfv3.apply(lambda x : season_calc(x['me'],x['an'],1), axis=1)
# 	dfv3=dfv3[['temp','cantidad']]#cambio orden de las columnas de venta
# 	dfv3['cantidad']=dfv3['cantidad'].astype(float).round(2)#si no tira error en windows
# 	dfv3=dfv3.groupby(['temp'], as_index=False).sum()#agrupo compras por temporada
# 	serie_ventas3={'name':'Ventas'}#creo la serie de ventas
# 	xvl=dfv3[['temp','cantidad']].sort_values('temp').values.tolist()#solo las ventas, ordeno por anmes y convierto a lista
# 	serie_ventas3['data']=xvl#armo los datos de la serie	
# 	#---------- junto y convierto a json --------------------
# 	hc_datos3=[serie_compras3]#junto nombre y datos, compras
# 	hc_datos3.append(serie_ventas3)#agrego las ventas
# 	hc_graf3=json.dumps(hc_datos3, default=str)#default=str para que no de error serializando datetime
# 	return hc_graf3

# def func_grafico_2(**kwargs):
# 	#DATOS PARA GRAFICO 2
# 	dm=pandas.DataFrame.from_records(get_compras_consolidado_xmarca_graf_mes(**kwargs),columns=['cantidad_c','mes',])#traigo las compras
# 	dm=dm[['mes','cantidad_c']]#cambio el orden de las columnas de compras
# 	dv=pandas.DataFrame.from_records(get_ventas_consolidado_xmarca_graf_mes(**kwargs),columns=['cantidad_v','mes','promedio_v'])#traigo las ventas
# 	dv=dv[['mes','cantidad_v','promedio_v']]#cambio el orden de las columnas de ventas	
# 	dv['prom_gral_v'] = dv['cantidad_v'].mean()
# 	dv['prom_mensual_gral_v'] = dv['promedio_v'].mean()

# 	dt=pandas.merge(dm, dv, on=['mes'], how='outer')#junto los dos dfs
# 	dt['cantidad_c']=dt['cantidad_c'].astype(float).round(2)
# 	dt['cantidad_v']=dt['cantidad_v'].astype(float).round(2)
	
# 	serie_compras2={'name':'Compras'}#creo la serie de compras
# 	xcl=dt[['mes','cantidad_c']].sort_values('mes').values.tolist()#solo los datos de compra, los ordeno por mes y los convierto a lista.
# 	serie_compras2['data']=xcl#agrego la lista a la serie de compras
# 	serie_compras2['type']='column'
# 	hc_datos2=[serie_compras2]#junto nombre y datos

# 	serie_ventas2={'name':'Ventas'}#creo la serie con nombre
# 	xvl=dt[['mes','cantidad_v']].values.tolist()#convierto a lista
# 	serie_ventas2['data']=xvl#armo los datos de la 
# 	serie_ventas2['type']='column'
# 	hc_datos2.append(serie_ventas2)#los agrego a las compras
	
# 	serie_prom_gral2={'name':'Media Venta Total Gral'}
# 	xgl = dt[['mes','prom_gral_v']].values.tolist()#convierto a lista
# 	serie_prom_gral2['type'] = 'line'
# 	serie_prom_gral2['data'] = xgl
# 	hc_datos2.append(serie_prom_gral2)#los agrego a las compras

# 	serie_promedio2={'name':'Venta Promedio Mensual'}#creo la serie con nombre
# 	xpl = dt[['mes','promedio_v']].values.tolist()#convierto a lista
# 	serie_promedio2['type']='column'
# 	serie_promedio2['data']=xpl#armo los datos de la serie
# 	hc_datos2.append(serie_promedio2)#los agrego a las compras

# 	serie_prom_mensual_gral2={'name':'Media Venta Mensual Gral'}
# 	xml = dt[['mes','prom_mensual_gral_v']].values.tolist()#convierto a lista
# 	serie_prom_mensual_gral2['type'] = 'line'
# 	serie_prom_mensual_gral2['data'] = xml
# 	hc_datos2.append(serie_prom_mensual_gral2)#los agrego a las compras


# 	hc_graf2=json.dumps(hc_datos2, default=str)#default=str para que no de error serializando datetime
# 	return hc_graf2



# #############################################################
# ### GRAFICO 4 - PONDERADOS POR SUBRUBRO #####################
# ### Compras

# # def gr_pond_subrubro_global(vd,vh,ln,mc,rb,sr,agrupador, agrupador_subrubro, agrupador_rubro):
# def gr_pond_subrubro_global(**kwargs):

# 	filtros = fx_filtros_art(**kwargs)

# 	t_sql_compras="SELECT SUM((CASE WHEN rc.operacion='+' THEN rc.cantidad WHEN rc.operacion='-' THEN -rc.cantidad END)) as items, "\
# 		"SUM((CASE WHEN rc.operacion='+' THEN rc.monto_facturado END)) AS totalcomp, "\
# 		"SUM((CASE WHEN rc.operacion='-' THEN rc.precio END)) AS totaldevs, "\
# 		"a.subrubro, s.descripcion FROM omicron_compras1_remitos rc "\
# 		"LEFT JOIN articulo a ON rc.articulo=a.codigo "\
# 		"LEFT JOIN subrubro s ON a.subrubro=s.codigo "\
# 		"WHERE rc.fecha>='%s' AND rc.fecha<='%s'"%(kwargs['c_desde'],kwargs['c_hasta'])\
# 		+ filtros +\
# 	 	"GROUP BY a.subrubro, s.descripcion "

# 	t_sql_ventas="SELECT SUM((CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END)) as items, "\
# 		"SUM((CASE WHEN v.operacion='+' THEN v.monto_facturado END) / 1.21) AS totalvent, "\
# 		"SUM((CASE WHEN v.operacion='-' THEN v.precio END) / 1.21) AS totaldevs, "\
# 		"a.subrubro, s.descripcion, SUM(ws.stock_actual) FROM omicron_ventas1 v "\
# 		"LEFT JOIN articulo a ON v.articulo=a.codigo "\
# 		"LEFT JOIN subrubro s ON a.subrubro=s.codigo "\
# 		"LEFT JOIN web_stock ws ON a.codigo=ws.articulo "\
# 		"WHERE v.codigo<>7 AND v.fecha>='%s' AND v.fecha<='%s'"%(kwargs['v_desde'],kwargs['v_hasta'])\
# 		+  filtros +\
# 		"GROUP BY a.subrubro, s.descripcion"

# 	#busco la data por : desde,hasta,linea,marca
# 	query_compras=db1.executesql(t_sql_compras)
# 	for row in query_compras:#reemplazo valores vacíos por 0
# 		row[1]=0 if row[1]==None else row[1]
# 		row[2]=0 if row[2]==None else row[2]
# 	#armo un DF de compras
# 	dfc=pandas.DataFrame.from_records(query_compras,columns=['cantidad_c','subtotal_c','subtotal_devs_c','subrubro', 'subrubro_descrip_c'])
# 	dfc['total_c']=dfc['subtotal_c']-dfc['subtotal_devs_c']
# 	dfc['ppp_c']=dfc['total_c'].astype(float)/dfc['cantidad_c'].astype(float)	

# 	#
# 	query_ventas=db1.executesql(t_sql_ventas)
# 	for row in query_ventas:#reemplazo valores vacíos por 0
# 		row[1]=0 if row[1]==None else row[1]
# 		row[2]=0 if row[2]==None else row[2]
# 	#armo un DF de ventas
# 	dfv=pandas.DataFrame.from_records(query_ventas,columns=['cantidad_v','subtotal_v','subtotal_devs_v','subrubro', 'subrubro_descrip_v','stock_actual'])		
# 	dfv['total_v']=dfv['subtotal_v']-dfv['subtotal_devs_v']
# 	dfv['ppp_v']=dfv['total_v'].astype(float)/dfv['cantidad_v'].astype(float)

# 	#junto los 2 dfs
# 	datos = pandas.merge(dfc, dfv, on=['subrubro'], how='outer')

# 	datos['subrubro_descrip']=datos['subrubro_descrip_v'].fillna(datos['subrubro_descrip_c'])

# 	df_pond_compra=datos[['cantidad_c','subrubro','subrubro_descrip']].copy()
# 	df_pond_compra['cantidad_c']=df_pond_compra['cantidad_c'].astype(float)
# 	df_pond_compra=df_pond_compra.groupby(['subrubro_descrip']).sum().reset_index()
# 	df_pond_compra['pond'] = ((df_pond_compra['cantidad_c']/df_pond_compra['cantidad_c'].sum())*100).round(2)
# 	#serie compras
# 	serie_pond_subr_compras={'name':'Compras'}
# 	#convierto el df compras a lista y lo pongo en el dict como data
# 	serie_pond_subr_compras['data']=df_pond_compra[['subrubro_descrip','pond']].values.tolist()

# 	### Ventas
# 	df_pond_venta=datos[['cantidad_v','subrubro','subrubro_descrip']].copy()
# 	df_pond_venta['cantidad_v']=df_pond_venta['cantidad_v'].astype(float)
# 	df_pond_venta=df_pond_venta.groupby(['subrubro_descrip']).sum().reset_index()
# 	df_pond_venta['pond'] = ((df_pond_venta['cantidad_v']/df_pond_venta['cantidad_v'].sum())*100).round(2)
# 	#serie ventas
# 	serie_pond_subr_ventas={'name':'Ventas'}
# 	#convierto el df ventas a lista y lo pongo en el dict como data
# 	serie_pond_subr_ventas['data']=df_pond_venta[['subrubro_descrip','pond']].values.tolist()

# 	### Stock actual
# 	df_pond_stock=datos[['stock_actual','subrubro','subrubro_descrip']].copy()
# 	df_pond_stock['stock_actual']=df_pond_stock['stock_actual'].astype(float)
# 	df_pond_stock=df_pond_stock.groupby(['subrubro_descrip']).sum().reset_index()
# 	df_pond_stock['pond'] = ((df_pond_stock['stock_actual']/df_pond_stock['stock_actual'].sum())*100).round(2)	
# 	#serie stock
# 	serie_pond_subr_stock={'name':'Stock actual'}
# 	#convierto el df stock a lista y lo pongo en el dict como data
# 	serie_pond_subr_stock['data']=df_pond_stock[['subrubro_descrip','pond']].values.tolist()


# 	#meto la data de compras en un dict
# 	hc_datos4=[serie_pond_subr_compras]
# 	#le agrego la data de ventas
# 	hc_datos4.append(serie_pond_subr_ventas)
# 	#le agrego la data de stock actual
# 	hc_datos4.append(serie_pond_subr_stock)

# 	#tiro la data para el graf de highcharts
# 	hc_graf4=json.dumps(hc_datos4, default=str)

# 	return hc_graf4
# 	# ### FIN GRAFICO 4 ###########################################
# 	# #############################################################


# 	#############################################################
# ### GRAFICO 5 - PONDERADOS POR RUBRO #####################
# ### Compras

# # def gr_pond_subrubro_global(vd,vh,ln,mc,rb,sr,agrupador, agrupador_subrubro, agrupador_rubro):
# def gr_pond_rubro_global(**kwargs):

# 	filtros = fx_filtros_art(**kwargs)

# 	t_sql_compras="SELECT SUM((CASE WHEN rc.operacion='+' THEN rc.cantidad WHEN rc.operacion='-' THEN -rc.cantidad END)) as items, "\
# 		"SUM((CASE WHEN rc.operacion='+' THEN rc.monto_facturado END)) AS totalcomp, "\
# 		"SUM((CASE WHEN rc.operacion='-' THEN rc.precio END)) AS totaldevs, "\
# 		"a.rubro, r.descripcion FROM omicron_compras1_remitos rc "\
# 		"LEFT JOIN articulo a ON rc.articulo=a.codigo "\
# 		"LEFT JOIN rubros r ON a.rubro=r.codigo "\
# 		"WHERE rc.fecha>='%s' AND rc.fecha<='%s'"%(kwargs['c_desde'],kwargs['c_hasta'])\
# 		+ filtros +\
# 	 	"GROUP BY a.rubro, r.descripcion "

# 	t_sql_ventas="SELECT SUM((CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END)) as items, "\
# 		"SUM((CASE WHEN v.operacion='+' THEN v.monto_facturado END) / 1.21) AS totalvent, "\
# 		"SUM((CASE WHEN v.operacion='-' THEN v.precio END) / 1.21) AS totaldevs, "\
# 		"a.rubro, r.descripcion, SUM(ws.stock_actual) FROM omicron_ventas1 v "\
# 		"LEFT JOIN articulo a ON v.articulo=a.codigo "\
# 		"LEFT JOIN rubros r ON a.rubro=r.codigo "\
# 		"LEFT JOIN web_stock ws ON a.codigo=ws.articulo "\
# 		"WHERE v.codigo<>7 AND v.fecha>='%s' AND v.fecha<='%s'"%(kwargs['v_desde'],kwargs['v_hasta'])\
# 		+ filtros +\
# 		"GROUP BY a.rubro, r.descripcion"

# 	#busco la data por : desde,hasta,linea,marca
# 	query_compras=db1.executesql(t_sql_compras)
# 	for row in query_compras:#reemplazo valores vacíos por 0
# 		row[1]=0 if row[1]==None else row[1]
# 		row[2]=0 if row[2]==None else row[2]
# 	#armo un DF de compras
# 	dfc=pandas.DataFrame.from_records(query_compras,columns=['cantidad_c','subtotal_c','subtotal_devs_c','subrubro', 'subrubro_descrip_c'])
# 	dfc['total_c']=dfc['subtotal_c']-dfc['subtotal_devs_c']
# 	dfc['ppp_c']=dfc['total_c'].astype(float)/dfc['cantidad_c'].astype(float)	

# 	#
# 	query_ventas=db1.executesql(t_sql_ventas)
# 	for row in query_ventas:#reemplazo valores vacíos por 0
# 		row[1]=0 if row[1]==None else row[1]
# 		row[2]=0 if row[2]==None else row[2]
# 	#armo un DF de ventas
# 	dfv=pandas.DataFrame.from_records(query_ventas,columns=['cantidad_v','subtotal_v','subtotal_devs_v','subrubro', 'subrubro_descrip_v','stock_actual'])		
# 	dfv['total_v']=dfv['subtotal_v']-dfv['subtotal_devs_v']
# 	dfv['ppp_v']=dfv['total_v'].astype(float)/dfv['cantidad_v'].astype(float)

# 	#junto los 2 dfs
# 	datos = pandas.merge(dfc, dfv, on=['subrubro'], how='outer')

# 	datos['subrubro_descrip']=datos['subrubro_descrip_v'].fillna(datos['subrubro_descrip_c'])

# 	df_pond_compra=datos[['cantidad_c','subrubro','subrubro_descrip']].copy()
# 	df_pond_compra['cantidad_c']=df_pond_compra['cantidad_c'].astype(float)
# 	df_pond_compra=df_pond_compra.groupby(['subrubro_descrip']).sum().reset_index()
# 	df_pond_compra['pond'] = ((df_pond_compra['cantidad_c']/df_pond_compra['cantidad_c'].sum())*100).round(2)
# 	#serie compras
# 	serie_pond_subr_compras={'name':'Compras'}
# 	#convierto el df compras a lista y lo pongo en el dict como data
# 	serie_pond_subr_compras['data']=df_pond_compra[['subrubro_descrip','pond']].values.tolist()

# 	### Ventas
# 	df_pond_venta=datos[['cantidad_v','subrubro','subrubro_descrip']].copy()
# 	df_pond_venta['cantidad_v']=df_pond_venta['cantidad_v'].astype(float)
# 	df_pond_venta=df_pond_venta.groupby(['subrubro_descrip']).sum().reset_index()
# 	df_pond_venta['pond'] = ((df_pond_venta['cantidad_v']/df_pond_venta['cantidad_v'].sum())*100).round(2)
# 	#serie ventas
# 	serie_pond_subr_ventas={'name':'Ventas'}
# 	#convierto el df ventas a lista y lo pongo en el dict como data
# 	serie_pond_subr_ventas['data']=df_pond_venta[['subrubro_descrip','pond']].values.tolist()

# 	### Stock actual
# 	df_pond_stock=datos[['stock_actual','subrubro','subrubro_descrip']].copy()
# 	df_pond_stock['stock_actual']=df_pond_stock['stock_actual'].astype(float)
# 	df_pond_stock=df_pond_stock.groupby(['subrubro_descrip']).sum().reset_index()
# 	df_pond_stock['pond'] = ((df_pond_stock['stock_actual']/df_pond_stock['stock_actual'].sum())*100).round(2)	
# 	#serie stock
# 	serie_pond_subr_stock={'name':'Stock actual'}
# 	#convierto el df stock a lista y lo pongo en el dict como data
# 	serie_pond_subr_stock['data']=df_pond_stock[['subrubro_descrip','pond']].values.tolist()


# 	#meto la data de compras en un dict
# 	hc_datos5=[serie_pond_subr_compras]
# 	#le agrego la data de ventas
# 	hc_datos5.append(serie_pond_subr_ventas)
# 	#le agrego la data de stock actual
# 	hc_datos5.append(serie_pond_subr_stock)

# 	#tiro la data para el graf de highcharts
# 	hc_graf5=json.dumps(hc_datos5, default=str)

# 	return hc_graf5
# 	# ### FIN GRAFICO 5 ###########################################
# 	# #############################################################