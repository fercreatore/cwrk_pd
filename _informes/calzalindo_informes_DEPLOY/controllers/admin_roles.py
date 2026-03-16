# -*- coding: utf-8 -*-
"""
ADMIN DE ROLES - calzalindo_informes
=====================================
Permite al admin ver usuarios, asignar y quitar roles.
Solo accesible por usuarios con rol 'informes_admin'.
"""

def index():
    """Panel principal de admin: lista usuarios y sus roles."""
    _requiere_acceso()

    # Buscar usuario (filtro)
    buscar = request.vars.buscar or ''

    # Todos los usuarios de auth_user
    if buscar:
        buscar_safe = buscar.replace("'", "''")
        usuarios = db_autenticacion(
            (db_autenticacion.auth_user.first_name.contains(buscar_safe)) |
            (db_autenticacion.auth_user.last_name.contains(buscar_safe)) |
            (db_autenticacion.auth_user.email.contains(buscar_safe))
        ).select(db_autenticacion.auth_user.ALL, orderby=db_autenticacion.auth_user.first_name)
    else:
        usuarios = db_autenticacion(db_autenticacion.auth_user).select(
            orderby=db_autenticacion.auth_user.first_name)

    # Roles de cada usuario
    memberships = db_autenticacion(
        (db_autenticacion.auth_membership.group_id == db_autenticacion.auth_group.id) &
        (db_autenticacion.auth_group.role.startswith('informes_'))
    ).select(
        db_autenticacion.auth_membership.user_id,
        db_autenticacion.auth_group.role
    )

    roles_por_usuario = {}
    for m in memberships:
        uid = m.auth_membership.user_id
        if uid not in roles_por_usuario:
            roles_por_usuario[uid] = []
        roles_por_usuario[uid].append(m.auth_group.role)

    # Roles disponibles
    roles_disponibles = db_autenticacion(
        db_autenticacion.auth_group.role.startswith('informes_')
    ).select(db_autenticacion.auth_group.ALL, orderby=db_autenticacion.auth_group.role)

    return dict(
        usuarios=usuarios,
        roles_por_usuario=roles_por_usuario,
        roles_disponibles=roles_disponibles,
        buscar=buscar,
    )


def asignar_rol():
    """POST: asigna un rol a un usuario."""
    _requiere_acceso()

    user_id = request.vars.user_id
    group_id = request.vars.group_id

    if user_id and group_id:
        user_id = int(user_id)
        group_id = int(group_id)
        # Verificar que no exista ya
        existe = db_autenticacion(
            (db_autenticacion.auth_membership.user_id == user_id) &
            (db_autenticacion.auth_membership.group_id == group_id)
        ).count()
        if not existe:
            db_autenticacion.auth_membership.insert(user_id=user_id, group_id=group_id)
            db_autenticacion.commit()
            session.flash = 'Rol asignado correctamente'
        else:
            session.flash = 'El usuario ya tiene ese rol'
    else:
        session.flash = 'Faltan datos'

    redirect(URL('admin_roles', 'index', vars=dict(buscar=request.vars.buscar or '')))


def quitar_rol():
    """GET: quita un rol de un usuario."""
    _requiere_acceso()

    user_id = request.args(0)
    group_id = request.args(1)

    if user_id and group_id:
        user_id = int(user_id)
        group_id = int(group_id)
        db_autenticacion(
            (db_autenticacion.auth_membership.user_id == user_id) &
            (db_autenticacion.auth_membership.group_id == group_id)
        ).delete()
        db_autenticacion.commit()
        session.flash = 'Rol quitado'

    redirect(URL('admin_roles', 'index', vars=dict(buscar=request.vars.buscar or '')))
