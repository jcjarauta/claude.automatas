# Expediente del escribiente

Qué es el producto, cómo se fabrica y qué falta para terminarlo.

Este documento es **la puerta de entrada**. Está escrito para que alguien que
no conozca el proyecto pueda entenderlo entero y seguir trabajando, y para
que quien sí lo conoce sepa en qué punto está sin leer treinta commits.

Fecha de este estado: **2026-09-30**.

| Si buscas | Ve a |
| --- | --- |
| Los principios y la visión de la herramienta entera | `docs/baseline.md` |
| Las cotas que no se tocan, y por qué | `docs/contratos.md` y `docs/contratos.json` |
| Qué se compra, a quién y cuánto cuesta | `docs/ficha-producto.md` |
| Cómo se diseña, se prueba y se documenta | `docs/metodologia.md` |
| Una pieza comercial concreta | `docs/piezas/<nombre>.json` |
| Cómo está montado el código | `CLAUDE.md` |
| Qué se cerró en cada etapa | `docs/etapas/` |

---

# Parte 1 · El producto

## En una frase

Un autómata de sobremesa que **escribe la letra de una persona concreta**: se
gira una manivela y un lápiz reproduce sobre el papel la frase que esa
persona escribió a mano.

## Cómo funciona, de la mano al papel

La cadena entera, que conviene tener en la cabeza porque todo el proyecto
cuelga de ella:

```
  el cliente escribe en una pantalla
            |
            v  se captura SOLO la geometría: nunca tiempo, presión ni velocidad
  una lista de trazos
            |
            v  se reparametriza por longitud de arco y se reparte en grados de θ
  tres pistas indexadas por θ, el ángulo del árbol maestro
            |            (punta.x, punta.y, levantamiento)
            v  cinemática inversa del varillaje
  tres ángulos de seguidor para cada θ
            |
            v  síntesis de leva: curva de paso, offset por el rodillo
  TRES PERFILES DE LEVA
            |
            v  se fresan en POM y se enhebran en el árbol con su pasador
  EL CARTUCHO
            |
            v  la máquina, girando
  el lápiz sobre el papel
```

**Todo es función de θ, nunca del tiempo.** Se gire deprisa o despacio, sale
la misma letra: lo único que cambia es lo bien que se lee mientras se
escribe. Es el principio que hace que la máquina sea un reproductor y no una
grabación.

## Plataforma y cartucho

La decisión que sostiene el negocio:

| | **La plataforma** | **El cartucho** |
| --- | --- | --- |
| Qué es | La máquina: bastidor, brazos, manivela, volante | Tres levas y dos separadores |
| Cambia entre pedidos | No | **Sí, es la frase del cliente** |
| Se fabrica | A stock | Por pedido |
| Se cambia | — | En un minuto, a mano |
| Cuesta | 81,09 € de material y compras | 38,08 € |

La plataforma es **fija** y el cartucho varía dentro de una envolvente. Es
tentador pensar lo contrario —que la máquina se adapta al tamaño de la leva—
pero sería el final del producto: si la plataforma cambiara con cada cliente
no se podría tener en stock y esto dejaría de ser un producto para ser un
encargo.

Lo que decide si una frase cabe es el **hueco entre la leva mayor y el poste
del seguidor de al lado**. Con la caja de escritura por defecto son 9,7 mm
con «hola» y 8,9 con un barrido de toda la caja; por debajo de 3 el
compilador avisa y por debajo de 0 lo rechaza. Ese número no lo ve ninguna
envolvente que juzgue una leva sola: es un límite de conjunto.

## Por qué no es un kit de hobby

Existe [Lanky Doodler](https://www.contraptioncart.com/shop/lankydoodler/),
el mismo mecanismo con app de generación de levas, a 28 €, en kit o montado,
con planos para marquetería. **No competimos en precio y no deberíamos
intentarlo.**

Lo que vendemos es otra cosa: un objeto de nogal y latón, con **la letra de
alguien**, fabricado por personas en proceso de inserción en el taller
ocupacional de Arrels Fundació. Si el producto acaba pareciendo un kit de
hobby caro, hemos perdido.

---

# Parte 2 · Cómo está hecho

## Los números que lo definen

Con el pedido de ejemplo «hola» y la geometría de hoy:

| | |
| --- | --- |
| Diámetro de leva | 107,7 mm |
| Ángulo de presión máximo | 8,3° — el límite está en 30° |
| Hueco al poste | 9,73 mm |
| Pila del cartucho | 19 mm (3 levas de 5 + 2 separadores de 2) |
| Masa del cartucho | 178 g |
| Inercia respecto del árbol | 2,44 × 10⁻⁴ kg·m² |
| Trabajo por vuelta | 133 mJ |
| Error del **modelo** | 0,108 mm |
| Error esperado en la punta | **2,79 mm peor caso, 1,64 mm cuadrático** |
| Tiempo de fresado de las tres levas | 7,5 min |
| Levas por plancha de 1 × 1 m | 81, o sea 27 cartuchos |
| Material y compras por máquina | 119,17 € con IVA |

## El despiece, en tres categorías

Cada pieza pertenece a una y solo una, y eso decide quién la produce y dónde
viven sus cotas.

**1 · Lo que genera el compilador** — las tres levas. Geometría distinta en
cada pedido, determinista: mismo input, mismo DXF byte a byte. Nunca la
dibuja nadie a mano.

**2 · Lo que se compra hecho** — 49 piezas por máquina, en 14 referencias.
Cada una tiene su ficha en `docs/piezas/` con sus **cotas de interfaz** —las
que otra pieza toca— su proveedor, su enlace y su fecha.

**3 · Lo que se hace en el taller** — base de nogal, bastidor de
contrachapado, brazos, seguidores, manivela y volante.

## Los cuatro contratos

Un contrato congelado es lo que hace que un cartucho fabricado hoy encaje en
una máquina construida dentro de tres años. Los números viven en
`docs/contratos.json`; el porqué, en `docs/contratos.md`.

| Contrato | Estado | Qué fija |
| --- | --- | --- |
| **Eje** | Congelado | Ø10 h7, giro horario, pila de 19 mm |
| **Fase** | Congelado | Pasador Ø3 × 24 a 18 mm sobre +X, igual en las tres levas |
| **Calaje** | Congelado | El ángulo del brazo con la punta en el centro de la caja |
| **Bastidor** | **Pendiente** | Postes a 71,06 mm y 120°, caja de escritura, reductor |

El de bastidor espera a E4. Se puede dibujar contra él; no se puede prometer.

### El contrato de fase, que es el que evita el fallo más caro

Cada leva lleva **dos** taladros: el del eje, que centra, y un pasador de
índice, que orienta. El pasador está en el mismo ángulo en las tres, así que
enhebradas quedan caladas entre sí. **El error de fase deja de ser posible en
vez de ser improbable.** Un cartucho montado desfasado escribe basura y no se
nota hasta que se gira la manivela.

El pasador va **deslizante en el POM y apretado solo en el plato de arrastre
metálico**: el m6 de la norma aprieta en acero, pero el POM fluye en frío y
la interferencia se relajaría en semanas, perdiendo el calaje después de la
venta y en silencio.

### El contrato de calaje, que es el que hace del brazo pieza de stock

El calaje —a qué ángulo se cala cada brazo sobre el eje de su seguidor— se
calculaba como la media de los ángulos a lo largo del ciclo. Eso da la leva
más pequeña posible, pero la media depende de por dónde escriba el cliente:
se movía 3,3° entre frases, y sobre 90 mm de brazo proximal son 5 mm de trazo
desplazado.

Ahora es el ángulo del brazo con la punta en el **centro de la caja**:
−3,749°, −176,251° y +2,149°, iguales en todos los pedidos. Cuesta unas
décimas de milímetro de leva y devuelve el brazo al catálogo.

## Las decisiones de fabricación que ya están tomadas

| Decisión | Por qué |
| --- | --- |
| Las levas van en **POM-C**, no en metacrilato | Dos agujeros y curvatura mínima son concentradores de tensión; el PMMA entallado pierde un factor once en impacto. No se desgasta, se agrieta desde un agujero |
| Se **fresan**, no se cortan a láser | Cortar POM a láser libera formaldehído. En un taller ocupacional eso basta. Y el láser deja conicidad en el canto, que es *la* superficie funcional |
| Rodillo **MR63ZZ**, con las dos letras | El abierto mide 2,0 de ancho y dejaría 0,5 mm de juego axial; un 2RS con Ø3 de agujero arrastra tanto como el rozamiento que lo hace rodar |
| Postes de **Ø8**, no Ø16 | Lo que la leva ve no es el poste: es la valona de su casquillo. Con Ø16 y valona de bronce Ø28 el hueco caía a 3 mm |
| Muelle de **compresión** | El de tracción rompe por el gancho, se desengancha y tintinea. En un objeto cuyo argumento es que suena bien, eso lo descalifica |
| El lápiz **no** va sobre guía deslizante | Con 3 mm de carrera la holgura radial se come el presupuesto de error entero, y el *stick-slip* es justo el ruido que no queremos. Paralelogramo o flexura |
| Manivela y volante se **hacen en el taller** | Ninguna manivela de catálogo está a la altura del objeto, y el volante es donde más barato se compra aspecto |
| El corte del cartucho se **externaliza** | Precio cerrado por bloque. No se compra máquina mientras E4 no diga si el modelo predice la realidad |

---

# Parte 3 · El sistema que lo produce

## Un pedido, un comando

```bash
uv run python -m compile.cli pedido.json --out build/
```

Y sale:

| Archivo | Para quién |
| --- | --- |
| `informe.md` | Quien vende y quien fabrica: veredicto, calajes, coste, presupuesto de error |
| `plantillas.pdf` | El carpintero, sobre el tablero. 1:1 exacto |
| `patron.pdf` | Quien verifica: el trazo esperado a 1:1 |
| `leva_*.dxf` | El taller de corte |
| `programa.json` | El archivo del pedido: las tres pistas θ |
| `cartucho.step` | Onshape, con `--step` |

El código de salida es 1 si el veredicto es negativo, para que un script sepa
que ese pedido no se fabrica sin leer el informe. **Los archivos se escriben
igualmente**: un pedido que no cabe también hay que poder mirarlo.

## Dónde vive cada número

Es la regla que más errores evita, y se aprendió pagándola: la valona del
casquillo se anotó como Ø12, acabó copiada en tres documentos y en el cálculo
del hueco, y el fabricante dice Ø15.

```
  docs/contratos.json        docs/piezas/*.json        bench/precios.json
   las cotas congeladas       las piezas que se          los precios, con
   con su estado              compran, con su fuente     fecha y enlace
         |                            |                         |
         +------------+---------------+-------------------------+
                      |
                      v
            el compilador las lee
                      |
         +------------+------------------+
         |                               |
         v                               v
   el cartucho, generado        scripts/exportar_variables.py
   (DXF, STEP, plantillas)                |
                                          v
                                 Variable Studio de Onshape
                                          |
                                          v
                                 la plataforma, paramétrica
```

**El flujo es de un solo sentido.** Se toca el dato, se regenera, se pega. Lo
que se edite dentro de Onshape se pierde en la siguiente regeneración y deja
de coincidir con lo que calcula el compilador sin que nadie se entere.

Y hay tests que lo atan: `tests/compile/test_piezas_reales.py` comprueba que
el número del compilador y la cota del proveedor son el mismo;
`tests/compile/test_contratos.py`, que el contrato y el código no se han
separado.

## Las tres capas del código

**Núcleo → Compilador → Emisores**, en ese orden de dependencia.

- **`core/`** es puro. Sin red, sin disco, sin CAD. Entra dato, sale dato.
  Ahí viven la geometría de levas, la cinemática, la energía y la cadena de
  tolerancias.
- **`compile/`** orquesta y decide. Lee ficheros, monta la máquina concreta,
  valida y llama a los emisores.
- **`emit/`** solo traduce a formato. No calcula nada que no sea maquetación.

---

# Parte 4 · Lo que sabemos y lo que no

Esta parte es la más importante del documento y la que más se olvida escribir.

## El presupuesto de error, sin adornos

| De dónde | Magnitud | Amplificación | En la punta |
| --- | --- | --- | --- |
| Perfil de la leva, seguidor 0 | 0,050 mm | × 23,2 | **1,159 mm** |
| Perfil de la leva, seguidor 1 | 0,050 mm | × 22,4 | **1,119 mm** |
| Holgura del pivote 0 | 0,200 mm | × 1,04 | 0,208 mm |
| Holgura del pivote 1 | 0,200 mm | × 1,00 | 0,200 mm |
| Muestreo del modelo | 0,108 mm | × 1,00 | 0,108 mm |
| | | **Peor caso** | **2,79 mm** |
| | | **Cuadrático** | **1,64 mm** |

Tres cosas que esta tabla dice y que no se veían antes de montarla:

**El error del modelo es la décima parte del problema.** Los 0,108 mm que se
estaban leyendo como la precisión de la máquina son la precisión del
compilador. Perseguir décimas ahí no sirve de nada mientras el canto venga a
±0,05.

**La precisión la decide quien corta.** Los ±0,05 mm que se le piden al
taller son 1,16 mm en el papel. Es la conversación más rentable que hay
pendiente.

**El varillaje amplifica 23 veces, no 12.** La cuenta corta —relación ×
proximal / brazo del seguidor— da 12 y sirve para hablar con el taller. Pero
el cinco barras mueve la punta con una palanca efectiva mayor que el brazo
proximal, y el jacobiano lo dice. Para prometer, la cuenta corta es optimista.

## Qué está medido y qué no

| | Estado |
| --- | --- |
| Geometría de la leva, ángulo de presión, curvatura | **Calculado y con tests.** Dos caminos independientes en masa e inercia, que coinciden al 0,02 % |
| Error del modelo | **Calculado**, y contrastado apoyando el rodillo en el perfil ya cortado |
| Par, energía, volante | **Calculado** sobre cargas de seguidor **no medidas** |
| Kerf del corte | **Sin medir.** `bench/kerf.json` está a cero |
| Escalado de impresora | **Sin medir.** Sin perfil, factores 1,0 y aviso |
| Juego de los pivotes | **Sin medir.** Estimación de catálogo. Es lo que impide subir la relación del varillaje |
| Tolerancia real del taller | **Sin pedir.** Es la tolerancia que se pide, no la que se da |
| Desgaste de la leva | **Sin medir** |
| Que la máquina escriba | **Sin comprobar.** No existe ninguna máquina |

**Todo lo de abajo es E4, y E4 no ha empezado.** Hasta entonces, los números
de este expediente sirven para decidir arquitectura y no para prometerle una
cota a un cliente.

## Las decisiones abiertas

**1 · La relación del varillaje: CERRADA EN «NO, POR AHORA» (2026-09-30).**

Se subió a 6:1 para que la leva fuera pequeña, y el docstring avisaba de que
C4 diría hasta dónde se puede subir. Al enchufarlo pareció que había que
bajarla. **No hay que bajarla, y la razón es que existe una palanca mejor.**

| | Tolerancia de corte | Peor caso | RSS |
| --- | --- | --- | --- |
| 6:1, hoy | ±0,05 mm | 2,79 mm | 1,64 |
| **6:1, pidiendo ±0,03** | ±0,03 mm | **1,88 mm** | 1,01 |
| 4:1 base 65 | ±0,05 mm | 1,91 mm | 1,10 |
| 6:1, pidiendo ±0,02 | ±0,02 mm | **1,43 mm** | 0,71 |

**Apretar la tolerancia de ±0,05 a ±0,03 da más precisión que rediseñar a
4:1, y no cuesta un milímetro de geometría.** Y los ±0,05 no son un dato: son
una suposición nuestra. Un CNC de tres ejes decente sostiene ±0,02 en POM.
Está en la lista de llamadas y es la más rentable del proyecto.

Hay una segunda palanca igual de gratis: **pedir tolerancia de cuerda de
0,01 mm en el CAM del taller**. Es un ajuste de software, no una capacidad de
máquina, y el DXF que le damos ya tiene una sagita de 0,0005 mm: si su CAM lo
aproxima a 0,05, tira por la borda la precisión que le damos.

### Y el presupuesto probablemente exagera

El peor caso trata los ±0,05 como si fueran ruido punto a punto. **El error
de un CNC es casi todo sistemático** —desviación de herramienta, offset de
radio, temperatura— y un error radial constante no hace temblar el trazo: lo
desplaza, lo escala o lo sesga entero. Sobre un papel que nadie registra a
micras, eso es invisible.

Lo que se ve es el temblor, y el componente aleatorio es el acabado
superficial, unos 2 µm, que a 23× son **0,05 mm en la punta**. Así que el
número que decide si se lee como su letra está probablemente un orden de
magnitud por debajo de 2,79 mm. No lo sabemos, y por eso la respuesta no es
rediseñar: es medirlo.

### Lo que habría costado el cambio

En dinero, nada: +1,77 € por cartucho, de 119,17 a 120,93 €.

| | 6:1 hoy | 4:1 base 65 |
| --- | --- | --- |
| **Hueco al poste, «hola»** | 9,73 mm | **6,81** |
| **Hueco con un barrido de toda la caja** | 8,85 mm | **5,50** |
| Envolvente del cartucho | 250 mm | 288 mm |
| Masa del cartucho | 178 g | 254 g |
| Cartuchos por plancha | 27 | 16 |

Lo caro es el hueco: se come el 40 % del margen sobre la cota que decide qué
frases caben, y sobre un mínimo de 3 mm. Se pagaría capacidad de producto por
precisión que una llamada da más barata. Y la esperanza de que la leva grande
regalara volante no se cumple: la inercia del cartucho sube de 2,44 a 4,93 ×
10⁻⁴ pero la necesaria sube de 5,53 a 8,29, porque hay más trabajo que
amortiguar.

### Cuándo se reabre

**Si E4 mide que el juego domina.** La holgura de los pivotes aporta hoy
0,41 mm sobre una estimación de catálogo que nadie ha medido. Si el juego
real fuera tres o cuatro veces mayor pasaría a dominar el presupuesto, y el
juego **no se arregla apretando al taller**: no es un problema de corte. Ahí
la relación del varillaje sería lo único que lo divide.

Orden correcto: llamar al taller, medir el juego con las excéntricas, y
entonces decidir. Cambiar la geometría ahora sería optimizar contra un número
que todavía no conocemos.

**2 · Cuánto texto cabe, que resultó no ser una cuestión de tamaño.**

La intuición razonable es que una frase larga pide una máquina mayor. **Es
medio verdad, y la mitad que falla es la que decide el producto.**

Lo que limita no es la amplitud del trazo: es su **frecuencia**. Una leva de
disco guarda todo el programa en una vuelta, así que más texto en la misma
caja de escritura no significa un recorrido mayor, significa el mismo
recorrido con muchas más idas y venidas. El radio de la leva casi no cambia;
lo que se desploma es el radio de curvatura del perfil.

Barrido con escritura sintética, misma caja, sólo crece la longitud de arco:

| Arco | mm/muestra | Error de trazo | Ángulo de presión | Ø leva | Veredicto |
| --- | --- | --- | --- | --- | --- |
| 82 mm | 0,11 | 0,076 mm | 8,3° | 107,2 | limpio |
| 166 | 0,23 | 0,104 | 9,5° | 109,0 | `curvatura_justa` |
| 335 | 0,47 | 0,360 | 12,4° | 109,0 | **`perfil_autointersecado`** |
| 673 | 0,94 | 0,930 | 22,7° | 109,0 | socavado y trazo infiel |
| 1.348 | 1,87 | 3,021 | 49,4° | 109,5 | **ángulo de presión excedido** |
| 5.395 | 7,49 | 2,353 | 70,4° | 110,9 | todo roto |

**El diámetro de la leva pasa de 107 a 111 mm mientras el arco se multiplica
por 65.** Agrandar la máquina no es la palanca que parece.

### Lo que sí compra el tamaño, y dónde se acaba

Sobre el caso de 335 mm, que hoy ya socava:

| Radio base | Ø leva | Presión | Veredicto |
| --- | --- | --- | --- |
| 55 mm | 109 | 12,4° | socavado |
| **80 mm** | **159** | **9,4°** | **limpio** |
| 110 mm | 219 | 7,7° | `poco_hueco_al_poste` |
| 150 mm | 299 | 6,5° | **la leva choca con el poste** |

Crecer sí rescata el doble de texto. Pero **la arquitectura se cierra sola**:
la leva crece con el radio base y los postes sólo con
`hypot(radio_base, 45)`, así que convergen. Pasado Ø160 la leva se come al
poste vecino y no hay talla que lo arregle.

Subir las muestras por vuelta arregla el error (0,360 → 0,078 mm con 2.880)
pero **no toca el socavado**, que es geometría.

### La conclusión, y es de producto

| Lo que se quiere escribir | Arco | Se puede |
| --- | --- | --- |
| Una firma, una palabra | ~80-170 mm | **Sí, con la máquina de hoy** |
| Dos palabras, una frase corta | ~350 mm | Sí, con radio base 80 y leva de Ø160 |
| Una frase larga | ~1.000 mm | No con leva de disco |
| Un párrafo | ~3.000 mm y más | No, ni de lejos |

**El escribiente es una máquina de firmas, no de textos.** Y eso no es una
limitación que haya que vencer: es lo que hace que el producto valga. Lo que
se vende es *la letra de alguien*, y una firma es exactamente donde esa letra
significa algo. Una máquina que escribiera párrafos sería un plóter.

### Y si aun así hay que escribir párrafos

Hace falta **otra clase de memoria**, y la ontología del baseline casi la
tiene: distingue valor continuo de evento discreto, pero le falta el tercer
eje, que es la **longitud del programa**.

- **Leva de disco**: alta resolución, pocos canales, **una vuelta de
  programa**. Es lo que hay.
- **Tambor con hélice**: la misma resolución y los mismos canales, pero el
  programa avanza a lo largo del eje. Un tambor de Ø60 × 80 con paso de 1 mm
  son ochenta vueltas: quince metros de programa.

Es exactamente por lo que las cajas de música son de cilindro y no de disco,
y por lo que los discos de polifón tocan melodías cortas. **La máquina 2 del
plan ya es una caja de música**, o sea un cilindro: la arquitectura para
párrafos ya está en la hoja de ruta, sólo que nadie la había conectado con
este límite.

Alternativa sin diseño nuevo, por si hiciera falta antes: **un párrafo son
varios cartuchos**, uno por línea, cambiados a mano. El cartucho ya está
pensado para cambiarse en un minuto. Es feo y es lento, pero cuesta cero en
ingeniería.

**Esta decisión va antes del CAD paramétrico**, no después: si la respuesta
fuera «frases cortas», el radio base sube a 80 y la plataforma entera cambia
de cotas.

**3 · Transmisión por engranajes o por correa.** Los dos engranajes de latón
son 25,64 € de los 119 totales. Un juego de poleas GT2 con correa ronda los
10 €. Pero la rueda de latón **se ve**, y es parte de por qué el objeto vale
lo que vale. Decisión de diseño, no de precio.

**4 · El precio de venta.** Sobre 150-400 €, el material es del 30 al 79 %.
En el extremo bajo no queda margen para pagar horas de taller, que es de lo
que se trata. **A 150 € este producto no se sostiene**; su sitio está en
300-400.

---

# Parte 5 · El paso a paso para terminarlo

Diez pasos. Los seis primeros no necesitan ni CAD ni proveedor.

## Hecho

| | Paso | Qué dejó |
| --- | --- | --- |
| ✅ | **1 · Fijar el calaje** | Constante de máquina, congelada. El brazo vuelve a ser pieza de stock |
| ✅ | **2 · Enchufar C4** | Cada pedido sale con su presupuesto de error. Destapó la amplificación de 23× |
| ✅ | **3 · Fichas de piezas comerciales** | 14 fichas con cotas de interfaz y fuente. Encontró que el pasador de 16 mm no atravesaba la pila de 19 |
| ✅ | **4 · `contratos.json` + variables** | Los números salen de un sitio y llegan a Onshape sin teclearlos |
| ✅ | **6 · Emisor de trazo patrón** | `patron.pdf` en cada pedido: verificación visual sin instrumentos |

## Pendiente

### 5 · Pedir las piezas — **te toca a ti, y va en paralelo con todo**

Unos 120 €. Es lo que desbloquea E4 y tiene plazo de entrega, mientras que el
CAD no. Serializar «primero dibujo, luego pido» cuesta dos semanas gratis.

- Compra **repuestos de lo barato**: un MR63ZZ cuesta 1,19 €, y que falte uno
  para el año que viene.
- Mete el **Lanky Doodler de 28 €** en la misma tanda: es la referencia de
  banco más barata que existe.
- Lleva al taller de corte las tres preguntas que valen dinero: precio
  cerrado por bloque, que **las tres levas salgan de un amarre** —es la
  diferencia entre 21 € y 49 €— y cuál es el mínimo de facturación.

**Hecho cuando:** las piezas están en una caja en el taller.

### 7 · Plataforma paramétrica en Onshape, talla M

Ya se puede: los parámetros están fijos y salen de `contratos.json`.

1. Pegar la salida de `scripts/exportar_variables.py` en un Variable Studio.
2. Modelar la plataforma en Part Studios que referencien esas variables.
3. Importar los STEP de igus y Mädler para comprobar que nada choca.
4. Arrastrar el `cartucho.step` de un pedido y montar el conjunto.

**Hecho cuando:** el conjunto cierra sin interferencias y cambiar una
variable regenera la plataforma entera.

### 8 · Cartucho de calibración en DM → **E4 empieza**

Tres discos **excéntricos** en DM de 5 mm, no las levas reales. Un círculo es
la única forma que se fabrica con precisión a mano: se recorta basto, se
monta en un pivote sobre la lijadora y se gira. Sale redondo por
construcción, no por pulso. Y un excéntrico tiene solución cerrada, así que
das entrada conocida y mides salida.

Eso da **el juego**, que es lo que C4 no modela y lo que impide subir la
relación del varillaje. Amplificado 23×, se ve a simple vista.

**Hecho cuando:** `bench/` tiene el juego, el par y la amplificación reales
medidos, con fecha.

### 9 · `emit/dossier.py`

El hueco grande. Está en la estructura y vacío. Necesita el 3-D del paso 7.

Vistas ortográficas e isométrica, explosionado **por subconjunto**,
secuencia numerada con qué comprobar antes de seguir, las cotas de puesta a
punto —calaje, precarga del muelle, juego axial— y la fase cero con foto.

**Hecho cuando:** alguien que no ha visto la máquina la monta siguiéndolo.

### 10 · Hoja de taller y galgas

Lo que le falta al dossier para servir en un taller ocupacional: orden de
operaciones con tiempos, qué operación es de qué nivel, y **galgas pasa /
no-pasa en vez de cotas**. En lugar de «comprueba que quedan 9,7 mm», una
galga cortada en el mismo DM que entra o no entra. Verificación binaria, sin
instrumento y sin interpretación. Se cortan con las mismas plantillas.

**Hecho cuando:** los puntos de control son todos binarios.

## Y después

| | |
| --- | --- |
| **El cartucho mudo** | Perfiles reales recortados a mano, para montar la máquina entera y ver que escribe algo |
| **El cartucho real** | La única pregunta que queda: si el trazo sale a las décimas prometidas |
| **E3b** | Imprimir las plantillas en dos copisterías, medir el cuadro y calibrar |
| **La talla L** | Cuando haya demanda de frases que no caben |
| **La máquina 2** | Caja de música o telar. Y entonces, y solo entonces, se refactoriza a marco genérico |

---

## Cómo saber que algo está mal

Tres comprobaciones que valen para cualquiera que retome esto:

```bash
uv run python scripts/check.py     # lint, tipos y 640 tests
uv run python -m compile.cli demo/hola.json --out build/
```

Si el segundo comando dice `APTO` y el primero dice `VERDE`, el proyecto está
donde este documento dice que está. Si no, algo se ha movido desde el
2026-09-30 y esta página ya no es de fiar.
