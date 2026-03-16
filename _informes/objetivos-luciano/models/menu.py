# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations
# ----------------------------------------------------------------------------------------------------------------------
# Customize your APP title, subtitle and menus here
# ----------------------------------------------------------------------------------------------------------------------
response.logo = A(B('web', SPAN(2), 'py'), XML('&trade;&nbsp;'),
                  _class="navbar-brand", _href="http://www.web2py.com/",
                  _id="web2py-logo")
response.title = request.application.replace('_', ' ').title()
response.subtitle = ''
# ----------------------------------------------------------------------------------------------------------------------
# read more at http://dev.w3.org/html5/markup/meta.name.html
# ----------------------------------------------------------------------------------------------------------------------
response.meta.author = myconf.get('app.author')
response.meta.description = myconf.get('app.description')
response.meta.keywords = myconf.get('app.keywords')
response.meta.generator = myconf.get('app.generator')
# ----------------------------------------------------------------------------------------------------------------------
# your http://google.com/analytics id
# ----------------------------------------------------------------------------------------------------------------------
response.google_analytics_id = None
# ----------------------------------------------------------------------------------------------------------------------
# this is the main application menu add/remove items as required
# ----------------------------------------------------------------------------------------------------------------------
response.menu=[
    ('Objetivos', False, URL(),[
    ('Central', False, URL('objetivos','sucursal', args=0)),
    ('Glam', False, URL('objetivos','sucursal', args=1)),
    ('Marroquinería', False, URL('objetivos','sucursal', args=4)),
    ('Norte', False, URL('objetivos','sucursal', args=2)),
    ('Cuore', False, URL('objetivos','sucursal', args=6)),
    ('Eva Perón', False, URL('objetivos','sucursal', args=7)),
    ('Junín', False, URL('objetivos','sucursal', args=8)),
    ('Tokyo Express', False, URL('objetivos','sucursal', args=9)),
    ('Junín GO', False, URL('objetivos','sucursal', args=15)),
    ('Avanzado x mes', False, URL('objetivos','vendedores_adv_xmes')),
    ('Mayorista', False, URL('objetivos','mayorista')),
    ('Web', False, URL('objetivos','web')),
    ('Vendedor individual', False, URL('objetivos_vendedor','index')),
     ])
]
response.menu+=[('Ranking', False, URL(), [
    ('Día / Mes', False, URL('informes','ranking_vendedores')),
    ('Anual', False, URL('informes','ranking_vendedores_anual')),
    ('Dia / Mes (Ofertas)', False, URL('informes','ranking_vendedores_ofertas')),
    ('Entre fechas', False, URL('informes','ranking_vendedores_dh'))])
]
response.menu+=[
    ('Gestion', False, URL(),[
    ('Informes', False, URL('informes','index')),
    ('Formularios', False, URL('formularios','index')),
    ('--- Informes Financieros ---', False, '#'),
    ('Rentabilidad Potencial', False, URL('rentabilidad','dashboard')),
    ('Recupero Inversión', False, URL('reportes','recupero')),
    ('---', False, '#'),
    ('Utilidades - Celus Whatsapp', False, URL('utilidades','celus_whatsapp')),
    ('Utilidades - Celus Whatsapp - Depurar', False, URL('utilidades','celus_depurar')),
    ('Encargados', False, URL('encargados','index')),
    ('Compras', False, URL('compras','index')),
     ])
]
response.menu+=[
    ('CLZ VENTAS', False, 'https://192.168.2.111:8000/clz_ventas',[])
]
response.menu+=[
    ('Consulta Precios', False, URL(),[
        ('Consulta Precios', False, URL('consultas','precios3_form')),
        ('Tokyo Express - Precio público', False, URL('tokyo','consulta_precios')),
        ('Lista Precios Vendedores', False, 'http://192.168.2.111:8000/clz_lpa')
        ])
]
response.menu+=[
    ('Utilidades', False, URL(),[
        ('Forzar actualiz. CER', False, (URL('utilidades','force_cer_update'))),
        ('Contactos', False, URL('utils','contactos')),
        ('Comandas Central', False, URL('comandas','index')),
        ('Comandas WEB', False, URL('comandas_web','index')),
        ('Planilla de entregas', False, URL('entregas','index')),
        ('Test envío email', False, URL('utilidades','test_email')),
        ('Demo/Prueba AUTOGEN INFORMES', False, URL('informes_autogen','index'))
        ])
]
response.menu+=[
    ('Tutoriales', False, URL('tutoriales','index'),[])
]
response.menu+=[
    ('Config', False, URL('admin','index'),[
        ('Configuración', False, URL('admin','index')),
        ('Agrupadores Industria', False, URL('agrupadores','index')),
        ])
]
response.menu+=[
    ('Ayuda', False, URL('ayuda','index'),[])
]
DEVELOPMENT_MENU = False
# ----------------------------------------------------------------------------------------------------------------------
# provide shortcuts for development. remove in production
# ----------------------------------------------------------------------------------------------------------------------
def _():
    # ------------------------------------------------------------------------------------------------------------------
    # shortcuts
    # ------------------------------------------------------------------------------------------------------------------
    app = request.application
    ctr = request.controller
    # ------------------------------------------------------------------------------------------------------------------
    # useful links to internal and external resources
    # ------------------------------------------------------------------------------------------------------------------
    response.menu += [
        (T('My Sites'), False, URL('admin', 'default', 'site')),
        (T('This App'), False, '#', [
            (T('Design'), False, URL('admin', 'default', 'design/%s' % app)),
            LI(_class="divider"),
            (T('Controller'), False,
             URL(
                 'admin', 'default', 'edit/%s/controllers/%s.py' % (app, ctr))),
            (T('View'), False,
             URL(
                 'admin', 'default', 'edit/%s/views/%s' % (app, response.view))),
            (T('DB Model'), False,
             URL(
                 'admin', 'default', 'edit/%s/models/db.py' % app)),
            (T('Menu Model'), False,
             URL(
                 'admin', 'default', 'edit/%s/models/menu.py' % app)),
            (T('Config.ini'), False,
             URL(
                 'admin', 'default', 'edit/%s/private/appconfig.ini' % app)),
            (T('Layout'), False,
             URL(
                 'admin', 'default', 'edit/%s/views/layout.html' % app)),
            (T('Stylesheet'), False,
             URL(
                 'admin', 'default', 'edit/%s/static/css/web2py-bootstrap3.css' % app)),
            (T('Database'), False, URL(app, 'appadmin', 'index')),
            (T('Errors'), False, URL(
                'admin', 'default', 'errors/' + app)),
            (T('About'), False, URL(
                'admin', 'default', 'about/' + app)),
        ]),
        ('web2py.com', False, '#', [
            (T('Download'), False,
             'http://www.web2py.com/examples/default/download'),
            (T('Support'), False,
             'http://www.web2py.com/examples/default/support'),
            (T('Demo'), False, 'http://web2py.com/demo_admin'),
            (T('Quick Examples'), False,
             'http://web2py.com/examples/default/examples'),
            (T('FAQ'), False, 'http://web2py.com/AlterEgo'),
            (T('Videos'), False,
             'http://www.web2py.com/examples/default/videos/'),
            (T('Free Applications'),
             False, 'http://web2py.com/appliances'),
            (T('Plugins'), False, 'http://web2py.com/plugins'),
            (T('Recipes'), False, 'http://web2pyslices.com/'),
        ]),
        (T('Documentation'), False, '#', [
            (T('Online book'), False, 'http://www.web2py.com/book'),
            LI(_class="divider"),
            (T('Preface'), False,
             'http://www.web2py.com/book/default/chapter/00'),
            (T('Introduction'), False,
             'http://www.web2py.com/book/default/chapter/01'),
            (T('Python'), False,
             'http://www.web2py.com/book/default/chapter/02'),
            (T('Overview'), False,
             'http://www.web2py.com/book/default/chapter/03'),
            (T('The Core'), False,
             'http://www.web2py.com/book/default/chapter/04'),
            (T('The Views'), False,
             'http://www.web2py.com/book/default/chapter/05'),
            (T('Database'), False,
             'http://www.web2py.com/book/default/chapter/06'),
            (T('Forms and Validators'), False,
             'http://www.web2py.com/book/default/chapter/07'),
            (T('Email and SMS'), False,
             'http://www.web2py.com/book/default/chapter/08'),
            (T('Access Control'), False,
             'http://www.web2py.com/book/default/chapter/09'),
            (T('Services'), False,
             'http://www.web2py.com/book/default/chapter/10'),
            (T('Ajax Recipes'), False,
             'http://www.web2py.com/book/default/chapter/11'),
            (T('Components and Plugins'), False,
             'http://www.web2py.com/book/default/chapter/12'),
            (T('Deployment Recipes'), False,
             'http://www.web2py.com/book/default/chapter/13'),
            (T('Other Recipes'), False,
             'http://www.web2py.com/book/default/chapter/14'),
            (T('Helping web2py'), False,
             'http://www.web2py.com/book/default/chapter/15'),
            (T("Buy web2py's book"), False,
             'http://stores.lulu.com/web2py'),
        ]),
        (T('Community'), False, None, [
            (T('Groups'), False,
             'http://www.web2py.com/examples/default/usergroups'),
            (T('Twitter'), False, 'http://twitter.com/web2py'),
            (T('Live Chat'), False,
             'http://webchat.freenode.net/?channels=web2py'),
        ]),
    ]
if DEVELOPMENT_MENU:
    _()
if "auth" in locals():
    auth.wikimenu()
