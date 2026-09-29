# Baseline · máquinas programables

Sep 29, 2026 · @Juan Carlos

Todas las máquinas del proyecto —autómata escribiente, caja de música, telar, bicimáquina y estación de trabajo humana— comparten una arquitectura: un programa que es función del ángulo del eje maestro, leído por módulos que declaran lo que piden y lo que dan. Lo único que cambia con la escala es qué restricción decide la viabilidad.

## Principios invariantes

Seis reglas de las que se deduce el resto del proyecto. No deberían cambiar.

**P1 · Todo se indexa por ángulo, nunca por tiempo.** El estado de la máquina es función de θ, el ángulo del eje maestro. La velocidad del operador pasa a ser irrelevante, los módulos se sincronizan solos al compartir eje, y la memoria física puede almacenar el programa.

**P2 · Máquina y programa se separan siempre.** La máquina es lo repetido; el programa es la pieza física personalizada. Un cilindro de caja de música, un juego de levas y una tarjeta Jacquard son todos «el programa». Que el modelo plataforma + cartucho encaje es consecuencia, no imposición comercial.

**P3 · La amplificación va de la memoria gruesa al resultado fino.** Leva grande, escritura pequeña. El pantógrafo divide los errores de fabricación en lugar de multiplicarlos.

**P4 · Toda viabilidad es una envolvente calculable.** Nada se acepta a ojo: siempre un número contra un límite, comprobado en cada grado del ciclo.

**P5 · La energía se puede desacoplar en el tiempo.** Quién aporta la energía y cuándo se usa no tienen por qué coincidir. Un acumulador entre la fuente y el eje convierte potencia baja durante mucho rato en potencia alta durante poco. Es lo que hace posible que una persona accione una prensa.

**P6 · La resistencia que siente la persona es una variable de diseño.** En una máquina impulsada por humanos, la fuerza percibida no es una consecuencia del mecanismo: se moldea a propósito, con una leva, para ajustarse a la curva de fuerza del cuerpo o al estímulo de entrenamiento buscado.

## Ontología de la máquina

Cualquier máquina del proyecto se describe con estas capas. La capa de fuente se ha desdoblado en tres al incorporar las máquinas impulsadas por personas.

| Capa | Qué hace | Escribiente | Estación de trabajo humana |
| --- | --- | --- | --- |
| 0a · Interfaz humana | Convierte esfuerzo corporal en movimiento mecánico | Manivela | Pedal, palanca, jalón, remo, prensa de piernas |
| 0b · Acumulador | Desacopla cuándo entra la energía de cuándo se usa | No lleva | Volante, muelle, peso elevado |
| 0c · Base de tiempo | Genera θ y distribuye el par | El propio eje | Árbol de transmisión con embragues |
| 1 · Memoria | Almacena el programa | 3 levas apiladas | Levas de ciclo, tambor de pasadores |
| 2 · Transmisión | Lee la memoria | Seguidores de rodillo oscilantes | Seguidores + limitador de par |
| 3 · Actuador | Convierte en acción útil | Brazo + pantógrafo + portalápiz | Sierra, lijadora, taladro, prensa |
| 4 · Estructura | Sostiene y referencia | Bastidor y cojinetes | Bancada, anclajes, protecciones |

### Las dos clases de memoria

Es la distinción que decide si una máquina cabe en el sistema actual o exige ampliarlo.

- **Valor continuo (leva).** Una función f(θ) que devuelve un número. Alta resolución, pocos canales: uno por leva apilada.
- **Evento discreto (púa, pasador, tarjeta, eslabón).** Un conjunto de sucesos (θ, canal, sí/no). Baja resolución, muchos canales.

Escribiente: continuo. Caja de música: evento. Telar Jacquard: evento llevado al extremo. Un autómata rico usa las dos.

### Los dos dominios de tiempo

Con acumulador aparecen dos ciclos que no coinciden y que el compilador debe tratar por separado: el **ciclo de carga** (humano, lento, irregular, dura minutos) y el **ciclo de trabajo** (máquina, rápido, indexado por θ, dura segundos). El acumulador es el embrague entre ambos.

## Núcleo de ingeniería transversal

Diez cálculos que se escriben una vez y sirven a todas las escalas. Son el activo real del proyecto: cambian los números, no las fórmulas.

| # | Núcleo | Entrada | Salida | Primera máquina que lo pide |
| --- | --- | --- | --- | --- |
| C1 | Cinemática inversa | Movimiento deseado del actuador | ψ(θ), ángulo del seguidor | Escribiente |
| C2 | Síntesis de perfil | ψ(θ) + geometría del seguidor | Curva de paso y perfil real | Escribiente |
| C3 | Envolvente geométrica | Perfil + radio de rodillo | Ángulo de presión, curvatura, veredicto | Escribiente |
| C4 | Cadena de tolerancias | Holguras + relaciones de amplificación | Error previsto en el efector | Escribiente |
| C5 | Diagrama de tiempos | Eventos por canal | Arcos de θ, solapes, conflictos | Caja de música |
| C6 | Presupuesto de par y energía | Fichas de todos los módulos | Par de pico, energía por ciclo, fuente necesaria | Bicimáquina |
| C7 | Inercia y volante | Curva de par + irregularidad admisible | Momento de inercia necesario | Bicimáquina |
| C8 | Curva de carga del proceso | Material, avance, herramienta | Par demandado a lo largo del corte | Estación de trabajo |
| C9 | Curva de fuerza humana | Articulación, recorrido, postura, duración | Fuerza disponible en cada punto | Estación de trabajo |
| C10 | Balance de acumulación | Energía por ciclo + potencia humana | Tiempo de carga, duración de descarga, tamaño del acumulador | Estación de trabajo |

### La forma común

C3, C6 y C8 son el mismo patrón de cálculo con distinta física: una magnitud evaluada en cada grado del ciclo, comparada con un límite. El ángulo de presión es al escribiente lo que la energía de impacto es a la bicimáquina y lo que el par disponible frente al demandado es a la sierra. Un solo motor de comprobación, tres límites distintos.

### C9 cierra el círculo

La fuerza que una persona puede ejercer depende del ángulo de la articulación: es una curva, no un número. Ajustar la resistencia de la máquina a esa curva es exactamente un problema de diseño de levas, y está resuelto desde 1970: Arthur Jones introdujo en Nautilus una leva elíptica en lugar de la polea precisamente para dar resistencia variable a lo largo del recorrido y ajustarla a las curvas de fuerza del músculo.

Dicho de otro modo: **la misma matemática que dibuja una letra da forma a la sensación de un ejercicio.** C1 a C3 sirven para las dos cosas sin cambiar una línea.

### Qué escribir ya

C1–C4 los necesita el escribiente. C6, C7 y C10 son baratos de escribir ahora y abren toda la familia de máquinas impulsadas por personas. C5 y C8 pueden esperar a su primera máquina.

## Envolventes por clase de máquina

La arquitectura es constante; lo que cambia con la escala es qué restricción hace saltar la alarma. De aquí sale la decisión de arquitectura más importante de la app.

| Clase | Ejemplo | Envolvente que manda | Núcleos que la calculan |
| --- | --- | --- | --- |
| Precisión | Escribiente | Ángulo de presión, curvatura, error en el papel | C1–C4 |
| Sincronía | Caja de música, autómata | Diagrama de tiempos, capacidad de canal | C5 |
| Fuerza | Telar | Tensión, par, rigidez | C6 |
| Energía | Instalación con bicicletas | Potencia disponible, irregularidad | C6, C7 |
| Trabajo útil | Sierra, lijadora, prensa | Par disponible frente a par demandado, a lo largo del corte | C6, C8, C9, C10 |
| Seguridad | Máquina con obstáculos | Energía de impacto, modo de fallo | C6 + límites de contacto |

**Consecuencia:** núcleo único más un módulo de envolvente enchufable por clase. No se construye un validador que lo sepa todo; se construye un motor cinemático y se le conecta el juez que corresponda.

### La envolvente de trabajo útil, en detalle

Es la nueva y la que gobierna las máquinas impulsadas por personas. Tiene tres comprobaciones encadenadas:

1. **¿Hay energía suficiente?** Energía por ciclo de la tarea frente a energía que una persona puede aportar en un tiempo razonable. Decide si la tarea es posible.
2. **¿Hay potencia suficiente?** Par demandado en el instante peor frente a par disponible en el eje. Decide si hace falta acumulador o basta accionamiento directo.
3. **¿Es sostenible para el cuerpo?** Fuerza pedida en cada punto del recorrido frente a curva de fuerza humana, y duración frente a fatiga. Decide la ergonomía y, con ella, la leva de resistencia.

Si (1) falla, la tarea no es para esta máquina. Si falla solo (2), el acumulador lo resuelve. Si falla (3), se rehace la transmisión o la leva de resistencia.

## Arquitectura de la herramienta

La app es un compilador de diseño: recoge una intención, la comprueba contra la envolvente y devuelve geometría fabricable.

1. **Captura.** La intención del cliente o del diseñador: una escritura, una melodía, una curva de movimiento, una tarea a realizar, un patrón de entrenamiento. Solo geometría, sin dinámica temporal.
2. **Front-end.** Normaliza, ordena, reparametriza por longitud de arco, reparte grados de θ y comprueba la capacidad del cartucho.
3. **Núcleo.** Ejecuta los cálculos C1–C10 según la clase de máquina. Si algo no cabe, devuelve qué falla y qué cambiar.
4. **Back-end.** Añade compensación de kerf, marca de fase, grabado de identificación; genera DXF, SVG y la simulación de lo que hará la máquina.
5. **Salida.** Cola de fabricación y gemelo paramétrico en Onshape para planos y documentación.

### Reparto de papeles

| Pieza | Papel | Por qué |
| --- | --- | --- |
| Motor Python | Fuente de verdad. Determinista y reproducible | La geometría de cada pedido no puede depender de un servicio externo ni de un modelo generativo |
| Onshape | Gemelo paramétrico, planos, ensamblajes, documentación | Una sola llamada por pedido: la API tiene cuota anual |
| Claude | Escribe y prueba el motor, las FeatureScripts y la interfaz | En el bucle de desarrollo, no en el de producción |

Stack propuesto: Python con scipy para splines y optimización, build123d o CadQuery para geometría, ezdxf para la salida a láser. Las tres tienen licencia permisiva.

### Regla de desarrollo

**Concreto ahora, framework en la máquina 2.** El escribiente se escribe en concreto, pero nombrando las cosas con el vocabulario general: base de tiempo, canal, memoria, actuador, envolvente. El refactor a marco llega cuando exista un segundo caso real. Un punto no define una recta.

## Sistema de módulos y acoplamiento

Un módulo se acopla en tres planos a la vez —mecánico, energético y de software— y el trabajo de la app es mantener los tres coherentes. Para eso todo módulo declara lo mismo.

### La ficha de módulo

Es la pieza central de la metodología. El brazo del escribiente y una prensa de piernas tienen la misma ficha; solo cambian las magnitudes.

| Campo | Contenido |
| --- | --- |
| Identidad | Nombre, familia, versión, contrato que cumple |
| Interfaz mecánica | Bahía, eje, anclaje, volumen ocupado |
| Interfaz de fase | Cero respecto al maestro, arco de θ que ocupa |
| Canales | Cuántos, tipo continuo o evento, rango de cada uno |
| Cinemática inversa | La función: acción deseada → ángulo de seguidor |
| Demanda o aporte energético | Par de pico, par medio, energía por ciclo, signo |
| Inercia aportada | Para el dimensionado del volante |
| Envolvente propia | Recorrido, velocidad y fuerza máximos |
| Modo de fallo | Para en seco, cede blando o se libera |
| Ergonomía | Solo estaciones humanas: postura, recorrido, fuerza por punto, ciclo de trabajo |
| Fabricación | Material, proceso, número de piezas, coste, tiempo de montaje |

El campo de signo en la demanda energética es lo que permite que una estación humana y una herramienta convivan en la misma suma: unas aportan, otras consumen.

### Los tres contratos que hay que congelar

Son los que hacen que un módulo de hoy encaje en una máquina de dentro de tres años.

- **Contrato de eje.** Diámetro, sentido de giro, paso entre posiciones de montaje, sistema de chaveta o pasador, altura o longitud útil.
- **Contrato de bastidor.** Cotas de referencia, patrón de anclaje, volumen máximo por módulo, posición de los postes de pivote.
- **Contrato de fase.** Dónde está el cero lógico, cómo se marca físicamente, cómo se verifica al montar. El más fácil de olvidar y el que más proyectos hunde.

### Reglas de acoplamiento

Seis comprobaciones que la app hace antes de dar por válida una máquina compuesta.

1. **Un solo maestro.** Todos los módulos comparten θ; lo que los distingue es el desfase.
2. **Reserva de arco.** Cada módulo de evento ocupa un arco de θ. Dos módulos que compiten por el mismo espacio físico no pueden solapar arcos.
3. **Suma energética.** La suma de aportes menos la de demandas debe ser positiva con margen, instante a instante y no solo de media.
4. **Balance de acumulación.** Si hay acumulador, el tiempo de carga y la duración de descarga deben ser aceptables para una persona.
5. **Compatibilidad de contrato.** Un módulo solo encaja en una bahía cuyo contrato cumpla. Lo comprueba la app, no el montador.
6. **Fallo coherente.** Si un módulo para en seco y otro cede blando, el conjunto necesita una política declarada.

### La arquitectura física que da la modularidad

Un **árbol de transmisión** con acoplamientos en posiciones de paso fijo. Escala en todo el rango del proyecto: eje vertical corto con tres levas en el escribiente; el mismo eje más largo con levas y cilindro en el autómata musical; árbol horizontal con embrague por bahía en el taller humano o la instalación.

Es lo que da gratis el «acoplable según presupuesto»: añadir un módulo es añadir un acoplamiento. Es además la solución histórica de los talleres del XIX, donde un solo motor movía tornos, sierras y taladros desde un único árbol.

## Catálogo de módulos

Cinco familias. Una máquina es una combinación válida de módulos de estas familias sobre un mismo árbol.

### Familia A · Estaciones humanas

Convierten esfuerzo corporal en giro de eje. Es aquí donde los estándares de máquina de gimnasio entran como **biblioteca de diseño**: cotas, recorridos, posturas y curvas de fuerza ya estudiados.

| Estación | Músculos | Carácter | Buena para |
| --- | --- | --- | --- |
| Pedal | Piernas, cíclico | Potencia continua, 60–90 rpm | Sierra, torno, lijadora, generación |
| Manivela de mano | Brazo, cíclico | Potencia baja, control fino | Autómatas, memoria de levas |
| Palanca o prensa | Piernas o pecho, alterno | Fuerza alta, recorrido corto | Carga de acumulador, prensa |
| Jalón o remo | Espalda y brazos, alterno | Fuerza media, recorrido largo | Carga de acumulador, elevación |
| Escalón o peso corporal | Piernas, alterno | Fuerza muy alta, recorrido corto | Carga lenta de acumulador |

Cada estación declara además su **leva de resistencia**: la que ajusta la fuerza percibida a la curva de fuerza del cuerpo o al perfil de entrenamiento buscado.

### Familia B · Acumuladores

Desacoplan la entrada de energía de su uso. La elección no es estética: las densidades de energía son muy distintas.

| Tipo | Densidad orientativa | Uso adecuado | Aviso |
| --- | --- | --- | --- |
| Volante | Alta para este rango | Suavizar irregularidad y dar golpes cortos | Es la opción por defecto |
| Muelle | Baja, del orden de 100 J por kg reales | Retornos, disparos, autómatas pequeños | Almacenar decenas de kJ exigiría cientos de kg de acero |
| Peso elevado | Muy baja | Demostración, didáctica, fuerza constante | 100 kg a 2 m son unos 2 kJ |

**Regla de decisión derivada:**

- **Tarea continua de potencia moderada** —serrar, lijar, taladrar, amolar, tornear, moler, bombear— se resuelve con **accionamiento directo más volante de suavizado**. Históricamente probado: desde 1870 se accionaban a pedal tornos, sierras, amoladoras, afiladoras y máquinas de taladrar y cortar.
- **Tarea de golpe: fuerza alta, energía pequeña** —punzonar, cizallar, remachar, prensar, estampar— es donde el acumulador tiene sentido de verdad. También aquí hay precedente: las prensas de punzonar y las remachadoras estaban entre las máquinas accionadas a pedal.

### Familia C · Memorias

Leva de disco, leva cilíndrica, leva de ranura, levas conjugadas, tambor de púas, disco perforado, cadena de tarjetas. Declaran número de canales, resolución y capacidad en eventos o en grados.

### Familia D · Transmisiones

Seguidor de rodillo oscilante o de traslación, cierre por muelle o gravedad, pantógrafo, tren de engranajes, embrague, **limitador de par**. Este último pasa a ser módulo obligatorio en cuanto la fuente es humana: siempre puede aparecer alguien que empuje más fuerte de lo previsto.

### Familia E · Actuadores y herramientas

Brazo escribiente, peine y púa, lizo, palanca basculante, sierra de cinta, lijadora de banda, taladro, prensa, bomba. Cada uno declara su curva de carga (C8) y su cinemática inversa (C1).

## Validación física

Sin esto, todo lo anterior es teoría. Es además el único activo del proyecto que nadie puede copiar, porque depende de esta láser, estos materiales y este taller.

**Banco de ensayo.** Un eje, una leva, un seguidor y un medidor. Compara el movimiento real con el predicho por el núcleo. Se construye en paralelo al motor de cálculo, no después: se alimentan mutuamente.

Tres medidas que hay que obtener y que después heredan todas las máquinas:

| Medida | Qué responde | Cómo |
| --- | --- | --- |
| Coeficiente de fidelidad | Cuánto error real produce cada décima de error geométrico | Por material y espesor, con perfiles patrón |
| Curva de desgaste | Cuántos ciclos aguanta cada material antes de degradar el trazo | Ensayo de 10.000 ciclos por candidato |
| Kerf efectivo | Cuánto hay que compensar en el perfil | Por material, espesor y potencia de corte |

Materiales candidatos para levas seguidas por rodillo, a contrastar en ese ensayo: contrachapado de abedul, metacrilato, POM y aluminio. El DM queda descartado de entrada en superficies de leva por desgaste de canto y sensibilidad a la humedad.

Para las máquinas impulsadas por personas hay que añadir dos ensayos más: **potencia real medida** en las estaciones construidas, con personas de distinta condición, y **curva de carga real** de cada herramienta sobre cada material. Los dos alimentan C6, C8 y C9, que sin datos propios solo dan órdenes de magnitud.

## Familias de máquina y secuencia

Cada máquina se elige por lo que añade al núcleo, no por su atractivo. El orden importa: cada una debe apoyarse en la anterior sin cambiar de clase de fuerza de golpe.

| Orden | Máquina | Qué añade al núcleo | Clase de fuerza |
| --- | --- | --- | --- |
| 1 | Escribiente | C1–C4: memoria continua y precisión geométrica | Gramos |
| 2 | Módulo musical en el mismo árbol | C5: memoria de evento y multicanal | Gramos |
| 3 | Estación de trabajo humana simple | C6–C10: energía, volante, ergonomía, carga | Decenas de kg |
| 4 | Telar de cintas con selección reducida | Ciclo de máquina y selección de muchos canales | Decenas de kg |
| 5 | Escribiente monumental movido por bicicletas | Escala, estructura, árbol largo | Cientos de kg |
| 6 | Instalación con obstáculos | Seguridad de contacto, régimen de instalación | Condicional |

### El cambio respecto al plan anterior

La estación de trabajo humana **se adelanta al puesto 3**, antes del telar. Tres razones:

- Aporta más núcleo nuevo que ninguna otra: cuatro de los diez cálculos.
- Es la más vendible después del escribiente, y en mercados distintos.
- Es el escalón de fuerza que faltaba entre los gramos y los cientos de kilos. Saltarlo era el riesgo que ya se había detectado.

### La máquina mínima demostrable de la familia humana

Una **bancada con una estación de pedal, un volante y una toma de fuerza normalizada**, sobre la que se acoplan primero una lijadora de banda y después un taladro. Sin acumulador, sin programa, sin levas. Valida C6, C7, el contrato de árbol y la ficha de módulo, con el mínimo de piezas.

A partir de ahí las ampliaciones son módulos, no máquinas nuevas: añadir una estación de palanca, añadir un acumulador, añadir una leva de resistencia, añadir una herramienta, añadir un ciclo programado de levas que mueva el avance de la pieza.

## Líneas de negocio

El mismo núcleo alimenta dos negocios distintos: objetos personalizados y máquinas de trabajo. Comparten ingeniería, no operación.

| Línea | Producto | Cliente | Ticket | Madurez |
| --- | --- | --- | --- | --- |
| Regalo personalizado | Escribiente + cartucho | B2C | 150–450 € | Primera |
| Cartuchos adicionales | Nuevas frases | Recurrente | Bajo, margen alto | Primera |
| Autómata musical | Escritura + música | B2C premium | Superior | Segunda |
| Máquina de taller humana | Bancada + módulos | Makerspaces, escuelas, cooperación | Medio-alto | Tercera |
| Terapia y rehabilitación | Máquina con resistencia prescrita | Centros de día, rehabilitación, programas ocupacionales | Medio-alto | Tercera |
| Educación y divulgación | Kit y taller | Escuelas, museos | Medio | Cuarta |
| Instalación y evento | Pieza monumental | Museos, ferias, marcas, administración | Alto | Quinta |

### La línea terapéutica es la más diferenciada

Es la que mejor encaja con el contexto del proyecto y la que menos competencia tiene. Tres razones:

- **La actividad con propósito vale más que el ejercicio simulado.** Mover una palanca contra un peso es ejercicio; mover esa palanca y que salga una pieza lijada es trabajo. La diferencia es sustancial en un contexto ocupacional.
- **La resistencia es prescribible.** La leva permite fijar un perfil de fuerza concreto a lo largo del recorrido. Eso convierte «una máquina» en «esta máquina, para este grupo», que es otra vez el modelo plataforma + cartucho: bancada estándar, leva de resistencia personalizada.
- **El resultado es visible.** Una pieza terminada al final de la sesión es una forma de medir el esfuerzo que no necesita pantalla ni sensor.

### El error que hay que evitar

No vender **generación de electricidad**. Es donde mueren casi todos los proyectos de gimnasio productivo: la energía eléctrica que produce una persona vale céntimos, y en cuanto alguien hace el cálculo el relato se cae.

Lo que sí se sostiene es **producir un objeto**: una tabla lijada, una pieza cortada, un agujero hecho, grano molido, agua bombeada. El valor percibido de un objeto terminado no se compara con el precio del kWh, y el gesto es comprensible sin explicación.

### Posicionamiento

Entre los kits de madera de consumo (30–150 €) y el objeto mecánico de lujo, no hay competidor identificado en autómata personalizado con la letra del cliente. En bicimáquinas existe un referente consolidado, Maya Pedal, pero sus máquinas son artesanales y sin sistema de acople normalizado entre ellas: el hueco es precisamente la **interfaz estándar y el diseño a medida por software**, que es lo que aporta esta herramienta.

## Hitos

Marcados con **\[G\]** los que son puerta: no se pasa sin cumplirlos.

### H0 · Fundación

- [ ] H0.1 Vocabulario y modelo de datos escritos y acordados
- [ ] H0.2 Plantilla de ficha de módulo definida
- [ ] H0.3 Stack montado: Python, scipy, build123d, ezdxf, repo con tests, MCP de Onshape conectado

### H1 · Núcleo de cálculo

- [ ] H1.1 C1: cinemática inversa del brazo del escribiente
- [ ] H1.2 C2: síntesis de perfil con offset de rodillo
- [ ] H1.3 C3: comprobador de envolvente geométrica
- [ ] H1.4 C4: cadena de tolerancias
- [ ] H1.5 Exportación DXF con kerf y marca de fase
- [ ] H1.6 Suite de tests: cierre periódico, continuidad, casos límite
- [ ] H1.7 C6, C7 y C10 escritos aunque el escribiente no los use

### H2 · Calibración física

- [ ] H2.1 Banco de ensayo construido
- [ ] H2.2 Coeficiente de fidelidad medido en tres materiales
- [ ] H2.3 Ensayo de desgaste de 10.000 ciclos
- [ ] H2.4 **\[G\]** El núcleo predice el movimiento real dentro de tolerancia

### H3 · Primera máquina completa

- [ ] H3.1 Protocolo de captura solo geometría
- [ ] H3.2 Compilador extremo a extremo: escritura a tres DXF
- [ ] H3.3 Simulación inversa y mapa de error
- [ ] H3.4 **\[G\]** Prototipo físico escribe una palabra legible
- [ ] H3.5 **\[G\]** Contrato mecánico del cartucho congelado, antes de cualquier stock
- [ ] H3.6 Plantilla paramétrica en Onshape y planos

### H4 · Piloto comercial

- [ ] H4.1 App cliente: captura, vista previa con aprobación, pedido
- [ ] H4.2 Flujo de taller documentado con tiempos reales
- [ ] H4.3 Diez pedidos reales entregados con muestra de control
- [ ] H4.4 Estructura productiva decidida

### H5 · Segunda clase de memoria

- [ ] H5.1 Modelo de datos extendido a pistas de evento
- [ ] H5.2 C5: diagrama de tiempos
- [ ] H5.3 Compilador de eventos: MIDI a cilindro o disco
- [ ] H5.4 **\[G\]** Módulo musical acoplado al escribiente en el mismo árbol
- [ ] H5.5 Refactor del núcleo a marco, ya con dos casos reales

### H6 · Primera máquina de trabajo humana

- [ ] H6.1 Contrato de árbol y bahía de la familia humana congelado
- [ ] H6.2 Bancada con estación de pedal y volante, funcionando
- [ ] H6.3 Medición de potencia real con personas de distinta condición
- [ ] H6.4 Curva de carga medida de una herramienta sobre un material
- [ ] H6.5 **\[G\]** Una lijadora y un taladro acoplados a la misma bancada, con la misma ficha de módulo
- [ ] H6.6 Limitador de par como módulo estándar del catálogo
- [ ] H6.7 Primera leva de resistencia diseñada con C9 y validada por sensación
- [ ] H6.8 Acumulador: primer módulo de volante de carga y descarga

### H7 · Ciclo de máquina y multicanal

- [ ] H7.1 Selección multicanal, de 16 a 32 canales
- [ ] H7.2 Telar de cintas funcionando

### H8 · Escala

- [ ] H8.1 Socio de cálculo estructural incorporado
- [ ] H8.2 Escribiente monumental movido por bicicletas, sin contacto con el público

**Los cuatro hitos que prueban que esto es una metodología y no un producto suelto:** H2.4 (el modelo predice la realidad), H3.4 (la primera máquina funciona), H5.4 (una segunda clase de memoria se acopla sin rehacer nada) y H6.5 (dos herramientas distintas comparten ficha y bancada).

**Camino crítico mínimo hasta algo vendible:** H0, H1, H2, H3, H4.3.

## Decisiones tomadas

| Decisión | Estado |
| --- | --- |
| Indexar por ángulo, no por tiempo | Cerrada |
| Plataforma más cartucho como arquitectura y como negocio | Cerrada |
| Eje vertical con levas apiladas y manivela superior en el escribiente | Cerrada |
| Motor Python como fuente de verdad; Onshape como gemelo | Cerrada |
| Escribiente como primera máquina | Cerrada |
| Volante como acumulador por defecto; muelle solo para retornos y disparos | Cerrada en esta revisión |
| Estándares de gimnasio como biblioteca de diseño, no como requisito | Cerrada en esta revisión |
| Estación de trabajo humana adelantada al tercer puesto | Cerrada en esta revisión |

## Cuestiones abiertas

- Diámetro máximo de leva del escribiente. Fija la capacidad del cartucho y condiciona toda la app.
- Material definitivo del cartucho. Depende de H2.3.
- Contrato de árbol de la familia humana: diámetro, paso entre bahías, tipo de embrague.
- Si la estación humana y el escribiente comparten algún contrato o son dos sistemas con la misma ficha pero distinta interfaz física.
- Qué herramienta concreta abre la familia humana: lijadora de banda es la candidata por carga suave y constante.

## Aparcado

Por decisión expresa, el bloque normativo y de propiedad industrial queda fuera de esta revisión. Se retoma antes de la primera venta y antes de cualquier instalación con público. Los cuatro puntos a recuperar: análisis de libertad de operación sobre la patente de autómata escribiente de tres levas, tratamiento de la escritura capturada, régimen de producto o instalación según la familia, y estructura productiva.

Lo que **no** se aparca, porque es ingeniería y no permiso: energía de contacto, limitador de par, modo de fallo declarado y resguardo de la energía acumulada.

## Fuentes

- [Arthur Jones · leva elíptica y resistencia variable en Nautilus](<https://en.wikipedia.org/wiki/Arthur_Jones_(inventor)>)
- [Low-tech Magazine · breve historia de las máquinas a pedal](https://solar.lowtechmagazine.com/2011/05/the-short-history-of-early-pedal-powered-machines/)
- [Wikipedia · Bicycle performance, potencia humana sostenida](https://en.wikipedia.org/wiki/Bicycle_performance)
- [Maya Pedal · catálogo de bicimáquinas](http://mayapedal.org/machines.en)
- [Mortise & Tenon · la sierra de cinta impulsada por humanos](https://www.mortiseandtenonmag.com/blogs/blog/the-human-powered-bandsaw)
- [Norton · Cam Design and Manufacturing Handbook, extracto sobre ángulo de presión](http://www.designofmachinery.com/CDH/documents/Chap07pp160-162.pdf)
- [PDA-0 · autómata dibujante programable basado en levas, IROS 2018](https://ieeexplore.ieee.org/document/8594443/)
- [Onshape · límites de la API](https://onshape-public.github.io/docs/auth/limits/)
