# -*- coding: utf-8 -*-
### PASAR A UN MODULO CUANDO FUNCIONE OK

import pandas as pd

def fx_stock_actual_cs(cs):
	t_sql = "SELECT TOP 1 SUM(s.stock_actual) AS stock FROM web_stock s "\
		"LEFT JOIN articulo a ON a.codigo=s.articulo "\
		"WHERE a.codigo_sinonimo='{0}' AND s.deposito IN {1}".format(cs, depos_para_informes)

	data = db1.executesql(t_sql, as_dict=True)[0]['stock']

	return data


def fx_dias_quebrado(cs, desde, hasta):

	### Movimientos del producto agrupados por día. DB Consolidada.
	def movimientos(cs, desde):
		t_sql = "SELECT SUM(CASE WHEN movi_stock.operacion='+' THEN movi_stock.cantidad WHEN movi_stock.operacion='-' THEN -movi_stock.cantidad END) as items, "\
		"CAST(movi_stock.fecha AS DATE) as fecha, 'movi_stock' AS origen, articulo.codigo_sinonimo AS sinonimo "\
		"FROM movi_stock "\
		"LEFT JOIN articulo ON articulo.codigo=movi_stock.articulo "\
		"WHERE movi_stock.fecha>='{0}' AND articulo.codigo_sinonimo='{1}' "\
		"GROUP BY CAST(movi_stock.fecha AS DATE), articulo.codigo_sinonimo".format(desde ,cs)

		data = dbC.executesql(t_sql, as_dict=True)

		return data

	stock       = fx_stock_actual_cs(cs)
	
	movimientos = movimientos(cs, desde)

	df = pd.DataFrame.from_dict(movimientos)

	df = df.sort_values(by='fecha', ascending=False)

	# Create the 'stock' column
	df['stock_inicio_dia'] = stock - df['items'].cumsum()
	df['stock_fin_dia'] = df['stock_inicio_dia'] + df['items']

	# Convert fecha column to datetime format
	df['fecha'] = pd.to_datetime(df['fecha'])

	## Selecciono hasta la fecha deseada
	fecha_hasta = pd.to_datetime(hasta)
	df = df[df['fecha'] <= fecha_hasta]


	# Calculate the difference in days from one row to the preceding row
	df['days_diff'] = (df['fecha'].diff().dt.days)

	df['dias_quebrado'] = df.apply(lambda row: -(row['days_diff'] + 1) if row['stock_fin_dia'] < 1 else 0, axis=1)

	# Sum of dias_quebrado column
	dias_quebrado = df['dias_quebrado'].sum()

	veces_quebrado = df[df['dias_quebrado'] != 0].shape[0]

	stock_inicial = df.iloc[-1]['stock_fin_dia']

	# PID-382
	#return (veces_quebrado, dias_quebrado, stock_inicial, stock)
	return (veces_quebrado, dias_quebrado, stock_inicial)








