# -*- coding: utf-8 -*-
"""
DEFAULT CONTROLLER - Hub principal de Calzalindo Informes
=========================================================
Pagina de inicio con accesos directos a todos los informes.
"""

def index():
    """Hub principal con tarjetas de acceso a cada modulo."""
    if not auth.user:
        redirect(URL('default', 'user', args='login'))
    return dict(
        es_admin=_es_admin(),
        puede_ver=_puede_ver,
        roles=_roles_usuario(),
    )

def user():
    """Login, logout, register, etc. Delegado a web2py Auth."""
    return dict(form=auth())
