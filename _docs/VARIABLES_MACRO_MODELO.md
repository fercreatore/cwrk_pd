# Variables Macroeconómicas para Predicción de Ventas
> Generado: 26 de marzo 2026
> Objetivo: correlacionar con ventas de calzado H4/CALZALINDO

## TOP 5 VARIABLES (priorizadas)

| # | Variable | r² estimado | Lead time | API |
|---|----------|-------------|-----------|-----|
| 1 | Salario real (RIPTE/IPC) | 0.70 | Coincidente | datos.gob.ar |
| 2 | ICC Confianza consumidor | Alto | LIDERA 1-3m | UTDT (manual) |
| 3 | Tasa BCRA | Medio-alto | LIDERA 2-4m | BCRA API |
| 4 | IPC calzado / IPC general | Medio | Coincidente | INDEC CSV |
| 5 | Aguinaldo + calendario | Perfecto | Conocido | Hardcoded |

## SERIES IDs - datos.gob.ar

```python
SERIES_MACRO = {
    'ipc_general': '148.3_INIVELNAL_DICI_M_26',
    'ipc_indumentaria': '101.1_I2I_2016_M_21',
    'ripte': '158.1_REPTE_0_0_5',
    'base_monetaria': '331.1_SALDO_BASERIA__15',
    'm2': '90.1_AMTM2_0_0_31',
    'm3': '90.1_AMTM3_0_0_31',
    'tc_oficial': '168.1_T_CAMBIOR_D_0_0_26',
    'vtas_shopping_indum': '458.1_INDUMENTARRIA_ABRI_M_34_29',
    'vtas_super_indum': '455.1_INDUMENTARGAR_0_M_35_24',
}
```

## BCRA API (sin auth)

```
Base: https://api.bcra.gob.ar/estadisticas/v3.0/monetarias/{id}?desde=YYYY-MM-DD&hasta=YYYY-MM-DD
id=6: Tasa politica monetaria
id=27: Inflacion mensual
id=4: TC minorista
id=15: Base monetaria
```

## Dolar Blue (sin auth)

```
https://dolarapi.com/v1/dolares/blue
```

## Ejemplo pull múltiple

```python
import requests
ids = ','.join(SERIES_MACRO.values())
url = f"https://apis.datos.gob.ar/series/api/series/?ids={ids}&collapse=month&limit=120&format=json"
r = requests.get(url).json()
```
