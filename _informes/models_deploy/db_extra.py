# -*- coding: utf-8 -*-
"""
Conexiones adicionales para módulo de Productividad.
Agrega: dbC (msgestionC), db5 (MySQL turnos)
"""

# ============================================================================
# CONEXIÓN MSSQL - msgestionC (vistas consolidadas: ventas1, viajantes)
# ============================================================================
dbC = DAL('mssql4://am:dl@192.168.2.111:1433/msgestionC',
          pool_size=20, migrate_enabled=False)

# ============================================================================
# CONEXIÓN MySQL - turnos_todos (turnero unificado)
# ============================================================================
db5 = DAL('mysql://objetivos:Calzalindo01@192.168.2.108/turnos_todos',
          migrate_enabled=False)
