# VEREDICTO FINAL: Modelo Vendedor Freelance para H4/Calzalindo
> Fecha: 3 de abril de 2026
> Analisis basado en: arquitectura del sistema, codigo implementado, datos reales del ERP (2023-2026 Q1), contexto macroeconomico argentino

---

## 1. RESUMEN EJECUTIVO

**Veredicto: DEPENDE. El modelo tiene merito conceptual pero la ejecucion actual esta desconectada de la realidad del negocio.**

La tesis central es atractiva: reemplazar costos fijos laborales (43% de cargas sociales sobre bruto) por una red de vendedores independientes que cobran comision (5-8%) directamente al cliente. En papel, H4 elimina el costo laboral y gana vendedores motivados por comision pura. En la practica, Calzalindo opera en Venado Tuerto (poblacion ~80.000), vende calzado a traves de 15+ sucursales fisicas, y enfrenta una contraccion real del negocio: Q1 2026 muestra -17% en unidades, clientes unicos cayeron 39% en dos anos, y el ticket real baja. Este no es el momento de lanzar un modelo experimental que requiere masa critica de vendedores, tecnologia de atribucion, y un mercado en expansion.

Fernando deberia pausar el desarrollo del sistema freelance, conservar el codigo ya construido (que tiene valor reutilizable), y redirigir el esfuerzo hacia los problemas urgentes del negocio: la hemorragia de clientes, las sucursales que operan a perdida, y la optimizacion del canal digital que ya existe.

---

## 2. EVIDENCIA A FAVOR (Top 5)

**2.1. El ahorro teorico en cargas sociales es real**
El costo laboral argentino con CCT 130/75 (Comercio) incluye contribuciones patronales del 26.5%, SAC, vacaciones, y costos indirectos. Un vendedor que cobra $500K brutos le cuesta a la empresa ~$695K. En el modelo freelance, ese costo se traslada al cliente. El ahorro de H4 es neto.
Fuente: calculo en gerencial.py (CONTRIBUCIONES=0.265, SAC=0.0833, VACACIONES=0.04)

**2.2. El codigo construido es solido y funcional**
Se implementaron 8 modulos completos en FastAPI: auth, vendedor, catalogo, atribucion, liquidacion, gerencial, con templates mobile-first. El sistema incluye proyeccion de monotributo, ranking gamificado, CRM basico, y comparacion ahorro vs empleado. No es un prototipo: es una aplicacion funcional.
Fuente: _freelance/src/ (13 archivos Python, 3 templates HTML, DDL para 7 tablas)

**2.3. Los datos de la infraestructura existente son completos**
El ERP ya tiene ventas por vendedor (viajante), stock en tiempo real, catalogo de articulos con precios, y sueldos reales en moviempl1. No hay que construir integraciones de datos desde cero; la capa freelance es un overlay sobre datos existentes.
Fuente: ARQUITECTURA_SISTEMA_VENDEDOR_FREELANCE.md seccion 1.3

**2.4. El modelo de atribucion por codigo es simple y viable**
El esquema V569 (codigo unico por vendedor en links) es lo suficientemente simple para implementar sin tecnologia compleja. Funciona para WhatsApp (el vendedor manda un link), Instagram (link en bio/stories), y presencial (el vendedor registra su codigo).
Fuente: venta_atribucion (tabla), vendedor.py endpoints

**2.5. La tendencia global del gig economy en retail existe**
Uber invirtio USD 500M en Argentina (abril 2026). Plataformas como Amway, Avon, y modelos de social selling operan en la region. La infraestructura regulatoria (monotributo) existe y permite facturacion como servicio.
Fuente: ARQUITECTURA seccion 10 (bitacora senales de mercado)

---

## 3. EVIDENCIA EN CONTRA (Top 5)

**3.1. El negocio esta en contraccion, no en expansion**
Q1 2026: -17% en unidades vs Q1 2025. Clientes unicos mensuales: 5,188 promedio en 2023 a 3,160 en Q1 2026 (-39%). La proyeccion base para 2026 es 162K pares (-7% vs 2025). Lanzar un modelo nuevo que requiere crecimiento en un mercado que se achica es contraciclico de alto riesgo.
Fuente: radiografia_negocio_20260401.md (seccion 1, 3, 7)

**3.2. Venado Tuerto no tiene escala para una red de micro-emprendedores**
Con ~80.000 habitantes y ~3.000 clientes unicos por mes en toda la cadena, el mercado potencial es limitado. Si se lanzan 9 vendedores freelance (como proyecta la arquitectura), cada uno competiria por ~333 clientes en una ciudad chica donde la mayoria ya conoce los locales. El social selling funciona en mercados grandes y fragmentados, no en mercados chicos y concentrados.
Fuente: analisis_clientes_20260401.md (2,597 clientes en marzo 2026)

**3.3. El modelo asume que el cliente acepta pagar una factura extra**
El esquema propone que el cliente paga dos facturas: una a H4 por el producto y otra al vendedor por "servicio de asesoramiento". En la practica, un cliente que compra zapatillas en un local fisico no va a entender ni aceptar pagar un 5-8% adicional por un "servicio" que percibe como parte de la atencion del local. La doble facturacion es un obstaculo real en retail fisico masivo.
Fuente: ARQUITECTURA seccion M5 (facturacion dual)

**3.4. No hay un solo vendedor freelance activo ni una sola venta atribuida**
Las tablas estan definidas pero no deployadas en produccion. No hay vendedores registrados, no hay ventas atribuidas, no hay liquidaciones. El sistema es 100% teorico. Sin datos de piloto, toda la proyeccion de ahorro y escala es especulativa.
Fuente: CLAUDE.md estado del proyecto (Fase 1-2 implementada, tablas "ya deployadas" pero sin datos)

**3.5. El costo de oportunidad es altisimo**
Cada hora dedicada al sistema freelance es una hora no dedicada a: recuperar los 2,400 clientes perdidos, cerrar o reestructurar las sucursales que operan a perdida (D7, D9, D10 con margenes del 31-33%), optimizar compras OI26 en un mercado que se achica, o potenciar el canal digital (TiendaNube/ML) que podria capturar parte de los clientes "perdidos".
Fuente: radiografia_negocio_20260401.md (secciones 3, 4, 8)

---

## 4. RIESGOS CRITICOS QUE PODRIAN MATAR EL MODELO

**R1. Riesgo laboral: reclamo de relacion de dependencia encubierta**
Si los vendedores "freelance" trabajan horarios fijos, en el local de H4, con herramientas de H4, y su ingreso depende mayoritariamente de H4, un juez laboral podria declararlos empleados encubiertos. Esto generaria retroactivos de cargas sociales, multas, y demandas. El antecedente de Rappi/Pedidos Ya en Argentina (2023-2024) mostro que la justicia laboral es agresiva con el encuadramiento de gig workers.

**R2. Riesgo de ingresos: vendedores que no venden lo suficiente para vivir**
Con un fee del 5% sobre ventas de $500K/mes (un vendedor medio), el ingreso bruto seria $25K/mes. Con monotributo ($72K) y canon, el neto es negativo. Para que un vendedor gane el equivalente a un salario minimo ($350K en 2026), necesita generar ~$8M/mes en ventas de producto. Solo los top 3-4 vendedores de la cadena superan ese volumen.

**R3. Riesgo operativo: complejidad desproporcionada al tamano del negocio**
El sistema tiene 8 modulos, 7 tablas nuevas, FastAPI, MySQL, SQL Server, templates, APIs de redes sociales, generacion de contenido con Pillow. Todo esto para una cadena que factura $5,700M/ano en una ciudad de 80K habitantes. La relacion complejidad/beneficio no cierra.

**R4. Riesgo cultural: los vendedores actuales no quieren ser freelance**
No hay evidencia de que los vendedores actuales de H4 quieran abandonar su relacion de dependencia (obra social, vacaciones, aguinaldo, indemnizacion) por un esquema variable. La transicion forzada podria generar conflicto gremial (FAECYS/Sindicato de Comercio).

**R5. Riesgo de canibalismo: los freelance roban clientes del local, no traen nuevos**
Si el vendedor freelance simplemente atiende a los clientes que ya entran al local (pero ahora con codigo de atribucion), no hay generacion de demanda nueva. H4 estaria pagando comision por ventas que ya tenia. El unico valor real es si el freelance TRAE clientes nuevos que no hubieran comprado.

---

## 5. ALTERNATIVAS QUE PODRIAN FUNCIONAR MEJOR

**A1. Programa de comisiones variable para empleados existentes**
En lugar de crear un sistema paralelo, implementar comisiones escalonadas dentro del esquema actual de empleados. Usar la infraestructura de tracking (viajante, atribucion) para medir desempeno y pagar bonos. Menor riesgo legal, menor complejidad, aprovecha el equipo actual.

**A2. Micro-influencers locales como afiliados (sin exclusividad)**
Pagar comision por referido a 10-20 personas con presencia en redes en Venado Tuerto (profesores de gimnasia, influencers locales, clubes deportivos). Sin relacion laboral, sin horario, sin local. Solo link + comision. Escala limitada pero costo casi cero.

**A3. Potenciar el canal digital con los recursos actuales**
TiendaNube y MercadoLibre ya existen. Redirigir el esfuerzo de desarrollo a: stock sync automatico, publicacion masiva, SEO, y captura de clientes digitales. El canal digital puede capturar demanda fuera de Venado Tuerto sin necesidad de vendedores fisicos.

**A4. Programa de reactivacion de clientes perdidos**
Con 2,400 clientes perdidos (la diferencia entre dic-2023 y dic-2025), una campana de WhatsApp con ofertas personalizadas podria recuperar 5-10% de la base. Costo: casi cero (ya tienen los datos). Retorno potencial: $80-160M de facturacion anual.

**A5. Reestructurar sucursales deficitarias**
Cerrar o reconvertir D9/S30 ($80M venta, 31.7% margen, probablemente a perdida) y revisar D7/S7 y D10/S10. Liberar recursos para invertir en los puntos que funcionan (D0/S0, D0/S26, mayorista).

---

## 6. RECOMENDACION CONCRETA

**Pausar el desarrollo del sistema freelance. No pivotar, no abandonar, sino congelar.**

El sistema construido tiene valor, pero el timing es incorrecto. El negocio necesita frenar la hemorragia de clientes y estabilizar la operacion antes de experimentar con modelos nuevos.

### Plan de accion recomendado:

**Mes 1-2 (abril-mayo 2026): Apagar incendios**
- Implementar programa de reactivacion de clientes (WhatsApp batch con ofertas a los 2,400 clientes perdidos). Costo: 0. Esfuerzo de desarrollo: 1-2 dias.
- Auditar sucursales deficitarias (D7, D9, D10). Decidir cierre o reconversion.
- Ajustar compras OI26 al escenario conservador (155-165K pares).

**Mes 3-4 (junio-julio 2026): Potenciar lo que funciona**
- Stock sync automatico TiendaNube + ML.
- Implementar comisiones variables para los vendedores actuales usando la infraestructura de viajante que ya existe.
- Proteger el canal mayorista (161 clientes que generan $694M con 64% de margen).

**Mes 5-6 (agosto-septiembre 2026): Evaluar piloto minimo**
- SI los clientes se estabilizaron y el negocio dejo de contraerse, lanzar un micro-piloto freelance con 2 personas (no 9).
- No vendedores del local: buscar 2 micro-influencers locales como afiliados.
- Canal: solo Instagram + WhatsApp. Sin local, sin horario, sin facturacion dual.
- Metrica de exito: que cada afiliado traiga al menos 5 clientes NUEVOS por mes (que no compraban antes).

### Presupuesto: $0 en software adicional
El codigo ya esta construido. Solo necesita datos reales cuando llegue el momento del piloto.

---

## 7. SI LA RESPUESTA ES "SEGUIR" (EVENTUALMENTE)

### Que cambiar del diseno actual:

1. **Eliminar la facturacion dual al cliente.** El cliente no va a aceptar dos facturas. El vendedor freelance deberia facturar a H4 por el servicio, no al cliente. Si, esto reduce el ahorro, pero es la unica forma viable de implementarlo sin friccion.

2. **Reducir de 8 modulos a 3.** Solo necesitas: (a) alta de vendedor + codigo de atribucion, (b) tracking de ventas atribuidas por codigo, (c) liquidacion mensual. Los otros 5 modulos (catalogo comercial, generador de contenido, CRM, franjas horarias, proyeccion monotributo) son over-engineering para un piloto.

3. **No usar FastAPI/nuevo stack.** Para 2-3 vendedores, un controller web2py con 3 funciones alcanza. El sistema ya tiene auth, templates, y conexion a SQL Server. Agregar un stack nuevo (FastAPI + MySQL + Jinja2 + Uvicorn) para esto es desproporcionado.

4. **Enfocarse en clientes NUEVOS, no en atribucion de existentes.** La metrica de exito no es "cuantas ventas atribuyo el freelance" sino "cuantos clientes que NO compraban antes ahora compran gracias al freelance". Sin esta distincion, el modelo solo redistribuye ventas existentes.

### Parametros del piloto:

- **Cuantos vendedores**: 2 (no 9). Uno para redes sociales (Instagram/WhatsApp), uno para canal fisico externo (ferias, eventos, clubes).
- **Donde**: No en sucursal. El freelance opera fuera del local, trayendo clientes al local o cerrando ventas por WhatsApp con retiro en sucursal.
- **Comision**: 5% sobre ventas de clientes nuevos atribuidos. 0% sobre clientes existentes.
- **Duracion del piloto**: 3 meses. Si en 3 meses ninguno de los 2 trae al menos 15 clientes nuevos por mes, cerrar.
- **Inversion**: $0 en software. Alta manual en tabla viajantes + planilla Excel para tracking. Si funciona, automatizar despues.

---

## 8. SI LA RESPUESTA ES "NO SEGUIR"

### Que hacer con el codigo ya construido:

1. **Reutilizar el modulo de ranking y dashboard de vendedor** para los empleados actuales. La gamificacion (ranking, fee estimado, KPIs personales) es valiosa para motivar empleados existentes. Adaptarlo como un modulo web2py de "Productividad por Vendedor" integrado a calzalindo_informes.

2. **Reutilizar el modulo de catalogo comercial** para alimentar las publicaciones de TiendaNube y MercadoLibre. El esquema de SKU base + fotos + descripcion para redes es exactamente lo que necesita el canal digital.

3. **Reutilizar la tabla venta_atribucion** para medir la efectividad de campanas de marketing (WhatsApp, redes sociales propias de H4) sin necesidad de vendedores freelance.

4. **Archivar el resto** (_freelance/src/) sin borrar. Si las condiciones cambian (el negocio crece, se abre a otra ciudad, aparece demanda), el codigo esta listo para retomarse.

### Donde poner el esfuerzo de desarrollo:

1. **Reactivacion de clientes** (impacto inmediato, costo cero)
2. **Stock sync TiendaNube/ML** (ya esta parcialmente construido en multicanal/)
3. **Dashboard de alertas tempranas** (5 KPIs criticos mensuales, detectar problemas antes de que se conviertan en crisis)
4. **Optimizacion de compras** (el pipeline de pedidos ya funciona; usarlo para ajustar OI26 al escenario conservador)

---

## 9. TABLA RESUMEN DE DECISION

| Pregunta | Respuesta |
|----------|-----------|
| ¿El modelo freelance tiene merito conceptual? | Si |
| ¿Es el momento correcto para implementarlo? | No |
| ¿El mercado de Venado Tuerto lo soporta? | Probablemente no a escala de 9 vendedores |
| ¿El codigo construido tiene valor? | Si, reutilizable |
| ¿Deberia Fernando seguir invirtiendo tiempo en esto? | No ahora |
| ¿Que deberia hacer en cambio? | Frenar la caida de clientes, cerrar sucursales deficitarias, potenciar digital |
| ¿Cuando retomar el tema freelance? | Cuando los clientes dejen de caer y el negocio se estabilice |
| ¿Con que escala retomar? | Micro-piloto con 2 afiliados, no 9 vendedores |

---

> Este veredicto fue escrito sin sesgo de confirmacion. Los datos dicen que el negocio se esta contrayendo y que el esfuerzo de desarrollo tiene mejor retorno en otros frentes. El modelo freelance no esta muerto, pero no es la prioridad.
