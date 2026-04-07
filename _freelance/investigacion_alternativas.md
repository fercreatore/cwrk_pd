# Investigacion: Alternativas al Modelo Vendedor Freelance
## Calzalindo / H4 SRL -- 15 sucursales, Venado Tuerto
> Fecha: 3 de abril de 2026

---

## Contexto

Calzalindo evalua el modelo vendedor freelance para reducir la carga social (~43% sobre sueldo bruto). Pero antes de implementarlo, conviene analizar si existen alternativas mejores o complementarias que logren el mismo objetivo (reducir costo laboral por venta) con menor riesgo legal y operativo.

**Situacion actual estimada por vendedor (empleado de comercio):**
- Sueldo bruto: ~$800.000/mes (vendedor junior, CCT comercio)
- Carga social total: ~$344.000/mes (43%)
- Costo empleador total: ~$1.144.000/mes
- Venta promedio por vendedor: variable segun sucursal

---

## 1. AUTOMATIZACION EN TIENDA (Self-Checkout, Kioscos, IA)

### Que es
Reemplazar funciones del vendedor con tecnologia: self-checkout, pantallas interactivas para consultar talle/stock, chatbots en local, camaras con IA para analytics de trafico.

### Costo vs modelos
- **Inversion inicial alta**: kiosco interactivo USD 3.000-8.000 por unidad; self-checkout USD 15.000-30.000 por caja
- **Ahorro operativo**: retailers en EEUU reportan 15-20% de reduccion en costos laborales con scheduling inteligente; self-checkout puede eliminar 1-2 cajeros por turno
- **vs Freelance**: la automatizacion ataca funciones de caja y consulta, no la venta asistida. Son complementarios, no sustitutos

### Complejidad de implementacion
ALTA. Requiere inversion de capital, integracion con ERP (MS Gestion no tiene APIs modernas), mantenimiento tecnico, y capacitacion. El mercado argentino tiene restricciones de importacion que encarecen hardware.

### Riesgo legal/operativo
BAJO en lo legal (no hay relacion laboral que defender). MEDIO en operativo: si falla el sistema, no hay vendedor backup.

### Escalabilidad
BUENA una vez implementado -- se replica en las 15 sucursales. Pero la inversion inicial escala linealmente.

### Puede Calzalindo hacerlo hoy?
PARCIALMENTE. El POS actual (MS Gestion) no tiene integracion con kioscos ni self-checkout. Se podria empezar con algo basico: tablet con catalogo + stock en tiempo real (consultando la base SQL). Pero el self-checkout completo es inviable a corto plazo.

### Veredicto: COMPLEMENTARIO, no sustituto. Empezar con tablet catalogo.

---

## 2. TIENDA AUTOSERVICIO (Modelo DSW/Macy's)

### Que es
Pasar de venta asistida (vendedor trae el par del deposito) a autoservicio: todo el stock en piso, el cliente se prueba solo, y solo hay personal en caja y reposicion.

### Costo vs modelos
- **Ahorro**: reduce la necesidad de vendedores especializados. En vez de 3 vendedores por turno, 1 repositor + 1 cajero
- **Inversion**: rediseno del layout de local (estanterias accesibles, senaletica de talles, seguridad antihurto). Estimacion: $2-5M por local para mobiliario + antihurto
- **vs Freelance**: mas agresivo en reduccion de personal pero cambia completamente la experiencia de compra

### Complejidad de implementacion
MEDIA-ALTA. Requiere:
- Rediseno fisico de los 15 locales (o empezar con 1-2 piloto)
- Sistema antihurto robusto (etiquetas + arcos, ~USD 5.000-10.000 por local)
- Mas espacio de piso (sacar el deposito atras, poner todo adelante)
- Cambio cultural: el cliente de calzado argentino esta acostumbrado al vendedor que trae el par

### Riesgo legal/operativo
- **Legal**: BAJO (se reduce personal legitimamente)
- **Operativo**: ALTO. El calzado tiene una tasa de merma (hurto) mas alta que indumentaria por ser facil de ocultar. Sin vendedor controlando, la perdida puede superar el ahorro salarial
- **Comercial**: el ticket promedio tiende a bajar sin venta sugestiva del vendedor

### Escalabilidad
MEDIA. Depende del tamano de los locales. Locales chicos no pueden exhibir todo el stock.

### Puede Calzalindo hacerlo hoy?
DIFICIL. Los locales de Calzalindo son tipicos de ciudad chica: espacios reducidos, deposito en la trastienda. Habria que evaluar local por local. Ademas, el perfil de cliente de Venado Tuerto valora la atencion personalizada.

### Veredicto: RIESGOSO para el perfil de Calzalindo. Solo viable en locales grandes tipo outlet.

---

## 3. OPTIMIZACION DE DOTACION (Workforce Scheduling)

### Que es
En vez de cambiar el modelo de contratacion, optimizar CUANTOS vendedores hay en cada turno usando datos de trafico y ventas. Poner mas gente cuando hay mas clientes, menos cuando no.

### Costo vs modelos
- **Inversion**: baja. Software de scheduling $50-200 USD/mes (o desarrollo propio con los datos de ventas que ya tienen en SQL)
- **Ahorro**: 12-20% de reduccion en costo laboral segun estudios (NRF, EEUU)
- **vs Freelance**: no cambia el modelo laboral, solo lo hace mas eficiente. El ahorro es menor (12-20% vs 43% de carga social) pero con CERO riesgo legal

### Complejidad de implementacion
BAJA. Calzalindo ya tiene datos de ventas por hora/dia/sucursal en SQL. Se puede construir un modelo de demanda y generar grillas de turnos optimas. Compatible con empleados actuales.

### Riesgo legal/operativo
MINIMO. Los empleados siguen siendo empleados. Se ajustan horarios dentro del CCT (horas extras, jornada parcial, francos rotativos).

### Escalabilidad
EXCELENTE. El modelo se aplica a las 15 sucursales con el mismo software/datos.

### Puede Calzalindo hacerlo hoy?
SI, INMEDIATAMENTE. Ya tienen ventas por hora en la base SQL. Se puede hacer un analisis de trafico vs dotacion actual y encontrar ineficiencias. Probablemente haya sucursales con exceso de personal en horarios muertos.

### Veredicto: PRIMERA ACCION A TOMAR. Ahorro rapido, riesgo cero, compatible con cualquier otro modelo.

---

## 4. OMNICANALIDAD (E-commerce + Tienda como Centro de Fulfillment)

### Que es
Potenciar la venta online (TiendaNube ya existe) y usar las sucursales como centros de fulfillment y puntos de retiro, reduciendo la necesidad de vendedores puros y reconvirtiendolos en operadores logisticos.

### Costo vs modelos
- **Inversion**: moderada. Ya existe TiendaNube. Falta: picking en sucursal, integracion stock real-time (parcialmente hecha), shipping desde sucursal
- **Ahorro en personal**: no elimina vendedores pero cambia el mix. Un operador de fulfillment puede ser menos calificado (y mas barato) que un vendedor
- **Costo de envio**: enviar desde sucursal es 16% mas barato que desde deposito central (dato Walmart/US)
- **vs Freelance**: es una estrategia de crecimiento, no de recorte. El ahorro viene de vender MAS con la misma estructura

### Complejidad de implementacion
MEDIA. Calzalindo ya tiene TiendaNube y sincronizacion de stock parcial (proyecto multicanal en desarrollo). Falta:
- Stock real-time confiable por sucursal (hoy solo total)
- Proceso de picking en sucursal
- Integracion con correo/logistica desde sucursal

### Riesgo legal/operativo
BAJO. No hay cambio en el modelo laboral. El riesgo es operativo: errores en stock, demoras en preparacion.

### Escalabilidad
ALTA. Cada sucursal se convierte en un mini-deposito. A mas sucursales, mejor cobertura geografica.

### Puede Calzalindo hacerlo hoy?
PARCIALMENTE. TiendaNube existe pero el stock sync no es confiable aun. El facturador TN esta en desarrollo. Se puede empezar con "retira en sucursal" que requiere menos integracion.

### Veredicto: ESTRATEGIA A MEDIANO PLAZO. No reemplaza al freelance como ahorro de costos pero agrega un canal de venta con menor costo por transaccion.

---

## 5. SUELDO BASICO + COMISION VARIABLE AGRESIVA

### Que es
En vez de freelancear, mantener a los vendedores como empleados pero con estructura: basico bajo (minimo CCT comercio) + comision alta por venta. Alinea incentivos sin cambiar el vinculo laboral.

### Costo vs modelos
- **Basico CCT comercio calzado**: ~$500.000-600.000/mes (minimo garantizado)
- **Comision**: 2-5% sobre venta, variable. Un vendedor que vende $5M/mes ganaria $100.000-250.000 extra
- **Carga social**: sigue siendo 43% pero sobre un basico mas bajo. El variable tambien lleva cargas pero solo cuando se vende
- **Ahorro estimado**: 10-25% vs sueldo fijo alto, dependiendo del mix fijo/variable
- **vs Freelance**: ahorro menor (10-25% vs ~43%) pero sin ningun riesgo legal

### Complejidad de implementacion
BAJA-MEDIA. Requiere:
- Negociar con empleados actuales (o implementar para nuevos)
- Sistema de liquidacion de comisiones (trackeo individual de ventas -- ya existe en MS Gestion por viajante)
- Respetar minimo CCT como garantia (Art. 104 LCT: la comision no puede ser menor que el minimo de convenio)

### Riesgo legal/operativo
BAJO si se respeta el piso de convenio. La ley argentina permite remuneracion mixta (fijo + comision) siempre que el total no baje del minimo CCT. Las comisiones son remunerativas (llevan aportes y contribuciones).

### Escalabilidad
EXCELENTE. Aplica a todas las sucursales por igual.

### Puede Calzalindo hacerlo hoy?
SI. MS Gestion ya trackea ventas por vendedor (campo viajante en ventas1). Se puede calcular comisiones automaticamente. El mayor desafio es el cambio cultural: vendedores acostumbrados a sueldo fijo pueden resistirse.

### Veredicto: ALTERNATIVA SOLIDA al freelance. Menor ahorro pero cero riesgo legal. Ideal como primer paso.

---

## 6. FRANQUICIAR SUCURSALES

### Que es
Convertir sucursales propias en franquicias. El franquiciado pone el capital, paga un canon, maneja sus propios empleados. Calzalindo provee marca, producto, know-how y sistemas.

### Costo vs modelos
- **Ahorro**: TOTAL en costos laborales de esa sucursal (pasan al franquiciado)
- **Ingreso**: canon inicial + regalias (tipicamente 3-8% de ventas)
- **Perdida**: margen de venta minorista de esa sucursal (solo se gana como mayorista + royalty)
- **vs Freelance**: el freelance ahorra costos laborales manteniendo el margen minorista. La franquicia cede el margen minorista

### Complejidad de implementacion
ALTA. Requiere:
- Manual de operaciones completo
- Contrato de franquicia (abogado especializado)
- Sistema de abastecimiento franquiciado
- Control de calidad y estandares
- En Argentina, cumplir Ley 26.032 (no existe ley especifica de franquicias, se rige por codigo civil y comercial)

### Riesgo legal/operativo
- **Legal**: MEDIO. Sin ley especifica, los conflictos franquiciante/franquiciado se resuelven judicialmente con incertidumbre
- **Operativo**: MEDIO-ALTO. Perdida de control sobre la experiencia del cliente, stock, precios
- **Estrategico**: se pierden las mejores sucursales (las rentables son las que atraen franquiciados)

### Escalabilidad
ALTA para expansion territorial (nuevas plazas donde Calzalindo no tiene presencia). BAJA como conversion de sucursales existentes.

### Puede Calzalindo hacerlo hoy?
NO RECOMENDADO para sucursales existentes. El margen minorista de calzado deportivo es la principal fuente de rentabilidad. Cederlo a un franquiciado solo tiene sentido para plazas nuevas donde el costo de abrir sucursal propia es prohibitivo.

### Veredicto: SOLO PARA EXPANSION a nuevas plazas, no para reducir costos en sucursales existentes.

---

## 7. POP-UP STORES / TIENDAS TEMPORALES

### Que es
Locales temporales (1-4 semanas) en ubicaciones de alto trafico para liquidar stock, probar mercados nuevos, o vender en temporada alta. Personal temporal con contrato eventual.

### Costo vs modelos
- **Alquiler**: corto plazo (30-60% mas caro por m2 que alquiler anual, pero solo se paga cuando se usa)
- **Personal**: contrato eventual (Art. 99 LCT) o agencia de empleo temporal. Carga social existe pero por periodo corto
- **vs Freelance**: no aplica al modelo de sucursal permanente. Es un modelo para stock excedente o prueba de nuevos mercados

### Complejidad de implementacion
MEDIA. Requiere:
- Encontrar locales temporales (shoppings suelen tener espacios para pop-ups)
- Logistica de armado/desarmado rapido
- Personal ad-hoc (freelance o eventual)
- POS portatil (tablet + lector)

### Riesgo legal/operativo
BAJO. El contrato eventual esta regulado por LCT. Si se excede el plazo, se convierte en permanente (pero eso es controlable).

### Escalabilidad
MEDIA. Cada pop-up es un proyecto independiente. No escala como modelo de sucursal permanente.

### Puede Calzalindo hacerlo hoy?
SI, PARA LIQUIDACION. Es ideal para mover el stock muerto que se identifico en el analisis de anomalias (informe del 1-abr). Pop-up en shopping de Rosario o Santa Fe para liquidar excedentes de OI con descuento agresivo.

### Veredicto: COMPLEMENTARIO. No reemplaza el modelo de sucursal pero es excelente para liquidar stock y testear plazas nuevas.

---

## 8. PROGRAMA DE AFILIADOS ONLINE

### Que es
Crear un programa donde influencers, clientes satisfechos, o micro-emprendedores ganen comision (5-12%) por referir ventas a la tienda online (TiendaNube).

### Costo vs modelos
- **Inversion**: minima. Software de tracking de afiliados ($50-200 USD/mes) o plugin para TiendaNube
- **Costo por venta**: solo se paga comision cuando se concreta la venta (5-12%)
- **vs Freelance**: el afiliado opera 100% online, no reemplaza al vendedor presencial. Es un canal adicional, no sustituto
- **Comparacion con vendedor**: un vendedor cuesta ~$1.144.000/mes fijo. Un afiliado cuesta solo cuando vende. Si la comision es 8% sobre ticket promedio de $80.000 = $6.400 por venta. El vendedor necesita hacer ~178 ventas/mes para justificar su costo

### Complejidad de implementacion
BAJA. TiendaNube tiene apps de programas de afiliados/referidos. Se configura en dias. El desafio es reclutar y activar afiliados.

### Riesgo legal/operativo
BAJO. El afiliado no es empleado (es un contrato comercial de comision). Riesgo de fraude (autocompras para cobrar comision) se mitiga con reglas del programa.

### Escalabilidad
ALTA. No tiene limite de afiliados. Cada afiliado es un "vendedor" sin costo fijo.

### Puede Calzalindo hacerlo hoy?
SI, PARA EL CANAL ONLINE. TiendaNube ya existe. Se puede activar un programa de referidos en semanas. Funciona especialmente bien con micro-influencers locales de Venado Tuerto y zona.

### Veredicto: ACTIVAR YA para canal online. Bajo costo, bajo riesgo, complementa al vendedor freelance presencial.

---

## MATRIZ COMPARATIVA

| Alternativa | Ahorro estimado | Complejidad | Riesgo legal | Riesgo operativo | Plazo | Calzalindo hoy? |
|---|---|---|---|---|---|---|
| 1. Automatizacion tienda | 15-20% laboral | ALTA | BAJO | MEDIO | 12+ meses | Parcial (tablet) |
| 2. Autoservicio | 30-50% laboral | ALTA | BAJO | ALTO (hurto) | 6-12 meses | Dificil |
| 3. Optimizacion dotacion | 12-20% laboral | BAJA | MINIMO | MINIMO | 1-2 meses | SI |
| 4. Omnicanalidad | Indirecto (+ venta) | MEDIA | BAJO | MEDIO | 6+ meses | Parcial |
| 5. Basico + comision | 10-25% laboral | BAJA | BAJO | BAJO | 2-3 meses | SI |
| 6. Franquiciar | 100% (cede margen) | ALTA | MEDIO | ALTO | 12+ meses | Solo expansion |
| 7. Pop-up stores | Variable | MEDIA | BAJO | BAJO | 1-2 meses | SI (liquidacion) |
| 8. Afiliados online | Solo comision x venta | BAJA | BAJO | BAJO | 1 mes | SI |
| **Freelance (referencia)** | **~43% carga social** | **MEDIA** | **ALTO** | **MEDIO** | **3-6 meses** | **En evaluacion** |

---

## RECOMENDACION: PLAN DE ACCION ESCALONADO

En vez de apostar todo al modelo freelance (que tiene riesgo legal significativo en Argentina por la presuncion de relacion de dependencia, Art. 23 LCT), se recomienda un enfoque gradual:

### Fase 1 -- Inmediato (abril-mayo 2026)
1. **Optimizar dotacion** con datos de ventas por hora/sucursal que ya estan en SQL. Identificar horas muertas y reducir turnos. Ahorro: 12-20%.
2. **Activar programa de afiliados** en TiendaNube. Costo minimo, canal adicional de ventas.
3. **Evaluar pop-up** en Rosario/Santa Fe para liquidar stock muerto identificado.

### Fase 2 -- Corto plazo (junio-agosto 2026)
4. **Migrar a basico + comision variable** para nuevas contrataciones. Respetar piso CCT. Ahorro adicional: 10-15%.
5. **Tablet con catalogo** en sucursales (consulta de stock/talle sin vendedor). Reduce necesidad de vendedores "informadores".

### Fase 3 -- Mediano plazo (septiembre+ 2026)
6. **Omnicanalidad completa**: stock real-time por sucursal, retira en sucursal, envio desde sucursal.
7. **Vendedor freelance** solo si los pasos anteriores no logran el ahorro necesario, y CON asesoramiento legal para estructurar como comisionista independiente con monotributo (no como relacion de dependencia encubierta).

### Ahorro acumulado estimado
- Fase 1: 12-20% costo laboral + canal adicional online
- Fase 1+2: 20-35% costo laboral
- Fase 1+2+3: 30-45% costo laboral (comparable al freelance pero con riesgo legal significativamente menor)

---

## CONCLUSION

El modelo freelance NO es la unica ni necesariamente la mejor opcion para reducir costos laborales. Una combinacion de optimizacion de dotacion + comision variable + omnicanalidad puede lograr ahorros comparables (30-45%) con una fraccion del riesgo legal.

El freelance puro en Argentina tiene un riesgo especifico: si el vendedor trabaja en horario fijo, en local de la empresa, con herramientas de la empresa, y cobra principalmente de un solo comitente, cualquier juez laboral lo va a considerar empleado en relacion de dependencia (Art. 23 LCT, presuncion de laboralidad). El costo de un juicio laboral (2-3 anos de sueldo + intereses + honorarios) puede superar ampliamente el ahorro de varios anos de no pagar cargas sociales.

**La recomendacion es: implementar las alternativas de bajo riesgo primero, y solo recurrir al freelance como ultimo recurso, con estructura legal robusta.**
