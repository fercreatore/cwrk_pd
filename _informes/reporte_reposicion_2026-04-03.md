# Reporte de Reposicion — H4 SRL / CALZALINDO
**Fecha:** 2026-04-03 | **Estado: FALLIDO — Sin conexion a base de datos**

---

## Problema

El agente de reposicion automatica no pudo conectarse al servidor SQL Server 192.168.2.111 (DELL-SVR produccion). Se intentaron tres vias de conexion, todas fallidas:

1. **MCP sql-replica** (`@bytebase/dbhub`): timeout tras 15 segundos
2. **pymssql directo**: "Network is unreachable (101)" — el servidor no es alcanzable desde la red actual
3. **pyodbc directo**: libreria ODBC no disponible en el entorno sandbox

**Causa probable:** La VPN L2TP hacia la red 192.168.2.x no esta activa en la Mac, o el entorno sandbox de Cowork no tiene acceso a la red privada. El agente corre en un sandbox aislado que no hereda la VPN del host.

---

## Accion requerida

Para que el proximo reporte se genere correctamente:

1. **Verificar VPN**: `tail -f /tmp/vpn-reconectar.log` — confirmar que la VPN L2TP esta conectada
2. **Verificar MCP**: El conector `sql-replica` debe poder alcanzar 192.168.2.111:1433
3. **Alternativa**: Ejecutar el agente desde Claude Code en el servidor 112 (DATASVRW), que tiene acceso directo via pyodbc

---

## Referencia: Ultimo reporte exitoso (2026-03-22)

El ultimo reporte de reposicion generado con datos reales fue el **22 de marzo de 2026** (12 dias atras). Hallazgos principales de aquel reporte:

### Criticos (< 15 dias de stock al 22-mar)
- **SARANG TONGSANG SRL (515)**: 10 modelos criticos, dominados por medias soquete deportivo/liso hombre y kids. Quiebre historico 75-96%.
- Modelo estrella: **102D C/S SOQUETE DEPORTIVO HOMBRE** — vel real 253/mes vs aparente 54/mes (96% quiebre). Con 132 pares = 11 dias.

### Urgentes (15-30 dias)
- **SARANG TONGSANG SRL**: 404 MEDIA 1/3 ESTAMPA T.3 (399 pares, vel ajustada 735/mes = 16 dias)
- **FLOYD MEDIAS (641)**: 61 SURTIDOS SOQUETE CORTO (42 pares, 29 dias)
- **GO by CZL (17)**: SDL4026 OXFORD MOCHILA (33 pares, 27 dias)

### Resumen ejecutivo (al 22-mar)
| Proveedor | Criticos | Urgentes | Reponer total |
|-----------|:--------:|:--------:|:-------------:|
| 515 SARANG TONGSANG SRL | 10 | 4 | ~3,040 pares |
| 641 FLOYD MEDIAS | 0 | 1 | ~46 pares |
| 17 GO by CZL | 0 | 1 | ~43 pares |

### Proyeccion al dia de hoy (3-abr, +12 dias)
Dado que han pasado 12 dias sin reporte actualizado, y asumiendo que no hubo reposicion:
- Los 10 modelos **criticos** de SARANG probablemente estan en **quiebre total** (stock 0)
- Los 6 modelos **urgentes** pasaron a **criticos** o en quiebre
- Los 5 modelos en **atencion** pasaron a **urgentes**
- **Estamos entrando en temporada invernal (abril)** — la demanda de medias sube. Factor estacional > 1 para soquetes y medias 1/3.

---

## Recomendacion inmediata

**LLAMAR A SARANG TONGSANG SRL (515) HOY.** Si no se repuso desde el 22-mar, los 10 modelos criticos ya estan en quiebre. Estimar pedido de ~3,500 pares (3,040 del reporte + 12 dias adicionales de demanda).

---

*Reporte generado por Agente Cowork. Ejecucion fallida por falta de conexion a BD. Proximo intento: verificar VPN y reconectar.*
