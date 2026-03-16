# -*- coding: utf-8 -*-
"""
Control de acceso por roles - calzalindo_informes
==================================================
Roles:
  informes_admin    -> Todo + gestionar usuarios/roles
  informes_gerencia -> Calce Financiero, Negociacion, Recupero Hist, Recupero Live, Pedidos, Productividad
  informes_compras  -> Pedidos, Recupero Live, Agrupadores
  informes_rrhh     -> Productividad e Incentivos

Depende de: models/db.py (debe cargar antes, web2py carga por orden alfabetico)
"""

# ============================================================================
# CREAR GRUPOS SI NO EXISTEN (se ejecuta al iniciar la app)
# ============================================================================
_ROLES = ['informes_admin', 'informes_gerencia', 'informes_compras', 'informes_rrhh']
for _r in _ROLES:
    if not db_autenticacion(db_autenticacion.auth_group.role == _r).select().first():
        db_autenticacion.auth_group.insert(role=_r, description=_r)
db_autenticacion.commit()

# ============================================================================
# MAPA DE PERMISOS: controller.function -> roles permitidos
# ============================================================================
_PERMISOS = {
    # Calce Financiero - solo gerencia y admin
    'calce_financiero.dashboard':           ['informes_admin', 'informes_gerencia'],
    'calce_financiero.detalle_industria':    ['informes_admin', 'informes_gerencia'],
    'calce_financiero.exportar_csv':         ['informes_admin', 'informes_gerencia'],
    'calce_financiero.ajax_calce_por_industria': ['informes_admin', 'informes_gerencia'],
    'calce_financiero.diagnostico':             ['informes_admin', 'informes_gerencia'],

    # Negociacion - solo gerencia y admin
    'reportes.negociacion_plazos':          ['informes_admin', 'informes_gerencia'],
    'reportes.negociacion_csv':             ['informes_admin', 'informes_gerencia'],

    # Recupero Historico - solo gerencia y admin
    'reportes.recupero_inversion':          ['informes_admin', 'informes_gerencia'],
    'reportes.recupero_inversion_detalle':  ['informes_admin', 'informes_gerencia'],
    'reportes.recupero_inversion_movimientos': ['informes_admin', 'informes_gerencia'],

    # Recupero Live - gerencia, compras y admin
    'reportes.recupero':                    ['informes_admin', 'informes_gerencia', 'informes_compras'],
    'reportes.recupero_detalle':            ['informes_admin', 'informes_gerencia', 'informes_compras'],
    'reportes.recupero_csv':                ['informes_admin', 'informes_gerencia', 'informes_compras'],

    # Pedidos - gerencia, compras y admin
    'reportes.sync_pedidos':                ['informes_admin', 'informes_gerencia', 'informes_compras'],
    'reportes.pedidos':                     ['informes_admin', 'informes_gerencia', 'informes_compras'],
    'reportes.pedidos_detalle':             ['informes_admin', 'informes_gerencia', 'informes_compras'],

    # Remitos de compra - compras y admin
    'reportes.remito_datos_proveedor':      ['informes_admin', 'informes_compras'],
    'reportes.remito_ultimo_numero':        ['informes_admin', 'informes_compras'],
    'reportes.remito_crear':                ['informes_admin', 'informes_compras'],
    'reportes.remito_eliminar':             ['informes_admin', 'informes_compras'],

    # Agrupadores - compras y admin
    'agrupadores.index':                    ['informes_admin', 'informes_compras'],
    'agrupadores.crear_agrupador':          ['informes_admin', 'informes_compras'],
    'agrupadores.editar_agrupador':         ['informes_admin', 'informes_compras'],
    'agrupadores.agregar_item':             ['informes_admin', 'informes_compras'],
    'agrupadores.quitar_item':              ['informes_admin', 'informes_compras'],
    'agrupadores.detalle_agrupador':        ['informes_admin', 'informes_compras'],
    'agrupadores.eliminar_agrupador':       ['informes_admin', 'informes_compras'],

    # Ranking Consolidado - gerencia, compras y admin
    'ranking_consolidado.rank_marcas':      ['informes_admin', 'informes_gerencia', 'informes_compras'],
    'ranking_consolidado.rank_productos':   ['informes_admin', 'informes_gerencia', 'informes_compras'],
    'ranking_consolidado.producto_curva':   ['informes_admin', 'informes_gerencia', 'informes_compras'],
    'ranking_consolidado.producto_pedido':  ['informes_admin', 'informes_gerencia', 'informes_compras'],
    'ranking_consolidado.marca_pedido':     ['informes_admin', 'informes_gerencia', 'informes_compras'],
    'ranking_consolidado.api_quiebre':      ['informes_admin', 'informes_gerencia', 'informes_compras'],

    # Productividad e Incentivos - gerencia, rrhh y admin
    'informes_productividad.dashboard':     ['informes_admin', 'informes_gerencia', 'informes_rrhh'],
    'informes_productividad.vendedor':      ['informes_admin', 'informes_gerencia', 'informes_rrhh'],
    'informes_productividad.incentivos':    ['informes_admin', 'informes_gerencia', 'informes_rrhh'],
    'informes_productividad.estacionalidad':['informes_admin', 'informes_gerencia', 'informes_rrhh'],
    'informes_productividad.ticket_historico':['informes_admin', 'informes_gerencia'],

    # Admin - solo admin
    'admin_roles.index':                    ['informes_admin'],
    'admin_roles.asignar_rol':              ['informes_admin'],
    'admin_roles.quitar_rol':               ['informes_admin'],
}

# ============================================================================
# ROLES DEL SISTEMA VIEJO QUE EQUIVALEN A ROLES DE INFORMES
# Si el usuario ya tiene alguno de estos roles, se le suma el equivalente
# Asi no dependemos de INSERT manuales en la BD
# ============================================================================
_ROLES_EQUIVALENTES = {
    'admins':      'informes_admin',
    'ges_admin':   'informes_admin',
    'finanzas':    'informes_gerencia',
    'gestion':     'informes_gerencia',
    'ges_pagos':   'informes_compras',   # pagos@ y cualquiera con ges_pagos -> ve pedidos
}

def _obtener_roles_usuario(user_id=None):
    """
    Retorna los roles efectivos del usuario, combinando:
    1. Roles de informes asignados directamente (informes_admin, etc.)
    2. Roles heredados del sistema viejo via _ROLES_EQUIVALENTES
    """
    uid = user_id or (auth.user.id if auth.user else 0)
    if not uid:
        return []
    rows = db_autenticacion(
        (db_autenticacion.auth_membership.user_id == uid) &
        (db_autenticacion.auth_membership.group_id == db_autenticacion.auth_group.id)
    ).select(db_autenticacion.auth_group.role)
    roles_bd = [r.role for r in rows]
    # Agregar roles equivalentes
    roles_efectivos = set(roles_bd)
    for rol_viejo, rol_informes in _ROLES_EQUIVALENTES.items():
        if rol_viejo in roles_bd:
            roles_efectivos.add(rol_informes)
    return list(roles_efectivos)

# ============================================================================
# HELPER: verificar acceso del usuario actual
# ============================================================================
def _tiene_acceso(controller_function=None):
    """
    Verifica si el usuario logueado tiene acceso a controller.function.
    Si no se pasa argumento, usa request.controller.request.function actual.
    Retorna True/False.
    """
    if not auth.user:
        return False
    cf = controller_function or '%s.%s' % (request.controller, request.function)
    roles_permitidos = _PERMISOS.get(cf)
    if roles_permitidos is None:
        # Si no esta en el mapa, acceso libre (ej: default/index, user/login)
        return True
    # Verificar roles efectivos (directos + heredados del sistema viejo)
    user_roles = _obtener_roles_usuario()
    return any(r in user_roles for r in roles_permitidos)

def _requiere_acceso():
    """
    Decorator-style check. Llamar al inicio de cada controller function.
    Si no tiene acceso, redirige con mensaje.
    """
    if not auth.user:
        redirect(URL('default', 'user', args='login', vars=dict(_next=URL())))
    if not _tiene_acceso():
        session.flash = 'No tenes permiso para acceder a esta seccion'
        redirect(URL('default', 'index'))

def _es_admin():
    """Retorna True si el usuario actual es informes_admin (directo o heredado)."""
    if not auth.user:
        return False
    return 'informes_admin' in _obtener_roles_usuario()

def _roles_usuario(user_id=None):
    """Retorna lista de roles efectivos del usuario (directos + heredados)."""
    return _obtener_roles_usuario(user_id)

# ============================================================================
# MENU: filtrar items del navbar segun permisos
# ============================================================================
def _puede_ver(controller_function):
    """Para usar en el layout.html: mostrar/ocultar links del menu."""
    if not auth.user:
        return False
    return _tiene_acceso(controller_function)
