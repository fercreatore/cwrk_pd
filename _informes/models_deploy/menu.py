# -*- coding: utf-8 -*-
"""
Menú para calzalindo_informes
"""
response.title = 'Calzalindo Informes'

response.menu = [
    ('Productividad', False, URL(), [
        ('Dashboard RRHH', False, URL('informes_productividad', 'dashboard')),
        ('Estacionalidad', False, URL('informes_productividad', 'estacionalidad')),
        ('Simulador Incentivos', False, URL('informes_productividad', 'incentivos')),
    ]),
]
