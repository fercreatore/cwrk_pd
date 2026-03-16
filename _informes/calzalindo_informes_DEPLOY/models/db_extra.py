# -*- coding: utf-8 -*-
"""
Conexiones adicionales para módulo de Productividad.
Agrega: dbC (msgestionC), db5 (MySQL turnos)
Si alguna conexión falla, queda en None y el controller maneja el error.
"""

# ============================================================================
# CONEXIÓN MSSQL - msgestionC (vistas consolidadas: ventas1, viajantes)
# ============================================================================
try:
    dbC = DAL('mssql4://am:dl@192.168.2.111:1433/msgestionC',
              pool_size=20, migrate_enabled=False)
except Exception:
    dbC = None

# ============================================================================
# CONEXIÓN MSSQL - omicronvt en REPLICA (112) para tablas analiticas CFO
# Tablas: t_flujo_caja_semanal, t_roi_proveedor, t_capital_trabajo_mensual,
#         t_enriquecedores_calce (creadas por crear_calce_avanzado.sql)
# ============================================================================
try:
    db_analitica = DAL('mssql4://am:dl@192.168.2.112:1433/omicronvt',
                       pool_size=10, migrate_enabled=False)
except Exception:
    db_analitica = None

# ============================================================================
# CONEXIÓN MySQL - turnos_todos (turnero unificado)
# ============================================================================
try:
    db5 = DAL('mysql://objetivos:Calzalindo01@192.168.2.108/turnos_todos',
              migrate_enabled=False)
except Exception:
    db5 = None
