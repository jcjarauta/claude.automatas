# Metodología de diseño y fabricación

Cómo se diseña un escribiente, cómo se prueba antes de gastar dinero, y qué
sale por la puerta con cada pedido.

- La **ficha de producto** (`docs/ficha-producto.md`) dice *qué* se compra y
  cuánto cuesta.
- Este documento dice *cómo* se diseña, se prueba y se documenta.
- Los **contratos** (`docs/contratos.md`) dicen qué cotas no se tocan.

---

## 1. Qué manda sobre qué

Hay una intuición razonable y equivocada: que el bloque de levas es la pieza
que manda y el resto del conjunto se adapta a su tamaño. Conviene deshacerla
antes de montar ningún sistema encima, porque de ella depende que la
plataforma se pueda fabricar a stock o no.

**La cadena causal real va al revés:**

```
caja de escritura (80 × 30 mm)   <- se elige. Es LA decisión de producto
        |
        v
barrido del brazo de cinco barras
        |
        v  ÷ relación 6:1
barrido del seguidor
        |
        v  + radio base 55 mm
radio máximo de la leva  ------> hueco al poste  ------> ¿cabe esta frase?
        ^
        |
radio base y brazo del seguidor  <- se eligen por ángulo de presión,
                                    curvatura y rodillo disponible
```

Y de ahí sale la cota de conjunto:

```
posición de los postes = hypot(radio_base, brazo_seguidor) = hypot(55, 45) = 71,1 mm
```

**Los postes no dependen de la frase.** Dependen del radio base y del brazo
del seguidor, que son decisiones de diseño. Lo único que cambia con la frase
es el **radio máximo** de la leva, es decir cuánto ondula: entre 53,3 y
54,5 mm en las frases probadas. El hueco al poste se mueve entre 9,1 y
10,3 mm, y por debajo de 3 mm el compilador avisa.

Es decir: **la plataforma es fija y el cartucho varía dentro de una
envolvente.** Eso no es una limitación, es el modelo de negocio. Si la
plataforma tuviera que adaptarse a cada cliente no se podría fabricar a
stock, y el escribiente pasaría de ser un producto a ser un encargo.

### Paramétrico ¿para qué, entonces?

Para **generaciones de producto**, no para clientes.

El diseño tiene que ser paramétrico para que el día que E4 diga «sube el
radio base a 60» o «la relación tiene que ser 5:1», todo lo demás siga solo:
postes, bastidor, planos, dossier. Eso pasará, y pasará varias veces.

Y para una **línea de tallas**, que es la respuesta elegante a «¿y si la
frase no cabe?»:

| Talla | Caja de escritura | Para qué |
| --- | --- | --- |
| **M** | 80 × 30 mm | La actual. Una palabra o dos, una firma |
| **L** | ~120 × 40 mm | Una frase corta. Levas mayores, bastidor mayor |
| **S** | ~50 × 20 mm | Una inicial, un monograma. Objeto pequeño y barato |

Tres plataformas congeladas, un solo motor paramétrico, y el compilador
eligiendo la menor en la que la frase entra. El cliente no configura una
máquina: elige un tamaño, como quien elige la talla de un marco.

### El hallazgo que hay que arreglar antes de dibujar nada

**Hoy el calaje del brazo depende de la frase, y no debería.**

El calaje es el ángulo al que cada brazo se cala sobre el eje de su
seguidor. `compile/escribiente.py` lo calcula como la media de los ángulos
del brazo a lo largo del ciclo, que es lo que minimiza el barrido de la leva.
Pero esa media depende de por dónde escriba el cliente:

| Frase | Calaje izq. | Calaje der. |
| --- | --- | --- |
| «hola» | -5,41° | -174,34° |
| Un trazo vertical | -3,81° | -176,18° |
| Barrido de toda la caja | -2,10° | -177,90° |

Un rango de **3,3°**. Sobre un brazo proximal de 90 mm eso son 5 mm de
desplazamiento del trazo si el brazo se monta al calaje de otra frase.

La consecuencia es que **el brazo deja de ser pieza de stock**: no se puede
premontar la plataforma y enchufar el cartucho, porque el brazo hay que
calarlo para ese pedido. Eso rompe justo lo que el modelo de negocio
necesita.

**La solución es barata.** Fijar el calaje a una constante de la máquina —el
centro de la caja de escritura— en vez de a la media de la frase. La leva
absorbe la diferencia: crece, como mucho, **0,22 mm de radio**, y el hueco al
poste baja de 9,5 a unos 9,3 mm. A cambio, el brazo se cala una vez, en el
diseño, y se monta igual en todas las máquinas.

Es una cota de contrato y hay que congelarla. **Debería hacerse antes de
dibujar la plataforma**, porque si no se dibuja sobre una referencia que se
mueve.

### Y una consecuencia que reordena el presupuesto de error

El varillaje amplifica. Un error radial en el canto de la leva llega a la
punta del lápiz multiplicado por

```
relación × brazo proximal / brazo del seguidor = 6 × 90 / 45 = 12×
```

| Error de corte en el canto | Lo que se ve en el papel |
| --- | --- |
| 0,05 mm — la tolerancia que pedimos al taller | **0,60 mm** |
| 0,10 mm | 1,20 mm |
| 0,30 mm — a mano, con cuidado | 3,60 mm |
| 0,50 mm — a mano, primera vez | 6,00 mm |

**El error de trazo simulado es 0,108 mm y la tolerancia de fabricación
permite 0,60.** O sea que el modelo es seis veces más fino que la pieza: la
precisión de la máquina no la decide el compilador, la decide el taller que
corta. Dejar de perseguir décimas en el modelo y empezar a perseguirlas en la
tolerancia del canto es, probablemente, el cambio de foco más rentable que
hay ahora mismo.

`core/tolerance.py` implementa C4 —la cadena de tolerancias, con la
corrección por ángulo de presión que aquí se ha omitido— y **no está
enchufado a nada**. Enchufarlo al compilador para que cada pedido salga con
su presupuesto de error es trabajo de un rato y convierte los 0,60 mm en un
número defendible en vez de una estimación de servilleta.

---

## 2. El sistema de diseño

Cuatro fuentes de verdad, y **una sola dirección de flujo**. La regla es que
ningún número se teclea dos veces.

```
        docs/contratos.json            <- LOS PARÁMETROS. Aquí y en ningún otro sitio
       /         |          \
      /          |           \
 Python      Onshape      docs/piezas/*.json
compilador   Variable       fichas de piezas
             Studio         comerciales
      |          |                |
      v          v                v
  cartucho   plataforma      envolventes
 (generado)  (FeatureScript)  (cotas de interfaz)
      \          |                /
       \         |               /
        v        v              v
         conjunto en Onshape
                 |
                 v
        dossier + plantillas + DXF
```

### 2a. Los parámetros, que hoy son prosa y deberían ser dato

`docs/contratos.md` está escrito para leerlo, y eso está bien. Pero los
números que contiene —Ø10 h7, pasador a 18 mm, postes a 71,1 mm, pila de
19 mm— los necesita el compilador en Python **y** los necesita Onshape, y hoy
se copian a mano en los dos sitios. Copiar a mano es exactamente cómo la
valona del casquillo acabó siendo Ø12 en tres documentos cuando el fabricante
dice Ø15.

Propuesta: **`docs/contratos.json`**, validado contra un esquema como el
resto del catálogo, con `docs/contratos.md` generado a partir de él o
citándolo. Y un `scripts/exportar_variables.py` que escupa la tabla de
variables de Onshape. Se pega una vez en el **Variable Studio** y todas las
Part Studios de la plataforma la referencian.

Cuando un contrato cambia: se toca el JSON, se regenera, se pega. Un sitio,
una dirección.

### 2b. Las piezas comerciales: la ficha manda, el STEP decora

La regla 6 del repositorio dice que ningún módulo entra sin ficha. Las piezas
comerciales son el tercer tipo de módulo y todavía no la tienen.

Una ficha por referencia en `docs/piezas/`, con **las cotas de interfaz**:
las que otra pieza toca. Del casquillo igus interesan el agujero, el exterior,
el diámetro de valona y su espesor; no interesa el chaflán. Del engranaje
interesan módulo, dientes, ancho, agujero y diámetro exterior.

Y con su **fuente**: proveedor, referencia, URL y fecha, igual que los
precios.

El STEP del fabricante se importa **después**, y solo para dos cosas: que el
render se vea bien y comprobar que nada choca. **No es la fuente de la cota.**
Si el STEP y la ficha discrepan, es un bug que hay que investigar, no una cota
que se acepta. Más adelante eso puede ser un test: importar el STEP, medir su
caja envolvente y su agujero, y comprobar que coinciden con la ficha. Así un
proveedor que cambia una pieza en silencio se caza solo.

De dónde salen los archivos, por si sirve: igus y Mädler publican CAD por
referencia; tornillería DIN y pasadores están en la biblioteca de contenido
estándar de Onshape; el 6800 lo publica SKF; y el eje, los postes, los
separadores y el MR63ZZ son cilindros que se dibujan antes de encontrarlos.
El portaminas hay que medirlo y dibujarlo, y de todos modos había que medirlo.

### 2c. El reparto con Onshape, que ya estaba decidido y ahora se completa

| | Quién lo hace | Cómo llega |
| --- | --- | --- |
| **Cartucho** | Lo genera el compilador | DXF y STEP, se arrastra el archivo |
| **Plataforma** | FeatureScript a mano, una vez | Se escribe dentro de Onshape |
| **Comercial** | Ficha + STEP del fabricante | Import o contenido estándar |
| **Parámetros** | `docs/contratos.json` | Variable Studio, generado |

El camino por pedido —que es el que se repite cientos de veces— no toca la
API de Onshape nunca. Solo la toca el desarrollo de la plataforma, que ocurre
unas pocas veces al año.

**Configurations de Onshape** para las tallas S/M/L: una sola plataforma
paramétrica con tres configuraciones congeladas, en vez de tres documentos
que se desincronizan.

---

## 3. Cómo se prueba antes de pedir las piezas

Aquí está la pregunta del corte en madera, y la respuesta es que **sí, pero
hacen falta dos cartuchos distintos y prueban cosas distintas.** La
infraestructura ya existe: `emit/template.py` emite plantillas 1:1 con cuadro
de calibración, que es exactamente para esto. El cuadro importa más que
nunca: un 1 % de escalado de impresora sobre una leva de Ø108 es **1 mm**, y
a 12× son 12 mm en el papel.

### 3a. El cartucho mudo — ¿esto se monta y se mueve?

Tres levas con el perfil real, recortadas a mano sobre la plantilla pegada.

**Material: HDF o DM de 5 mm, no contrachapado.** El contrachapado tiene
huecos y capas de dureza distinta, y el rodillo rodaría sobre un canto
irregular. El DM es uniforme, no tiene veta y se lija a la línea. El canto es
blando y se desgastará, pero para unos cientos de ciclos sobra.

Precisión realista: **±0,3 mm** con sierra de marquetería y lijadora de
disco, pegando la plantilla con adhesivo en espray y lijando hasta la línea.
±0,5 mm la primera vez.

**Eso son 3,6 a 6 mm en la punta.** Así que este cartucho **no prueba la
fidelidad del trazo** y no hay que pedirle que lo haga. Lo que sí prueba, y
es mucho:

- Que el conjunto **se monta**: pila, huecos, postes, interferencias.
- Que el **varillaje no se atasca** ni cambia de rama. Es la trampa conocida
  de la cinemática inversa, y en el papel no se ve.
- Que el **pasador de índice hace su trabajo**: que el cartucho solo entra de
  una manera.
- Que el **levantamiento del lápiz** sube y baja limpio, sin arrastrar.
- Que el **par es el que dijimos**. Se mide con un dinamómetro de pesar
  maletas en la manivela, y contrasta C6 con la realidad.
- Que **escribe algo reconocible**. Con 4 mm de error será un garabato
  tembloroso, pero se verá si el reparto de θ y el canal de levantamiento
  están bien. Un fallo de programa se ve a 4 mm; uno de fidelidad, no.

**Si en el taller hay una impresora 3D, imprime las levas en vez de
recortarlas.** Una FDM decente da ±0,1 a 0,2 mm, es repetible, no gasta
habilidad y sale del STEP que el compilador ya emite. Es mejor mula que la
madera y es gratis.

### 3b. El cartucho de calibración — el que de verdad mide

Este es el que propongo con más ganas, porque ataca justo lo que E4 tiene que
medir y hoy no está modelado: **el juego**.

Tres levas que no son levas, sino **discos excéntricos**: círculos con el
agujero del eje descentrado una excentricidad conocida.

Un círculo es **la única forma que una persona puede fabricar con precisión
usando herramienta de mano**: se recorta basto, se monta en un pivote sobre
la lijadora de disco y se gira. Sale redondo por construcción, no por
pulso. La excentricidad se consigue taladrando el agujero descentrado, que se
mide con pie de rey.

Y un excéntrico tiene **solución cerrada**: la ley de movimiento del seguidor
se calcula exactamente. Con eso tienes lo que no se consigue de ninguna otra
manera:

- **Entrada conocida y salida medida.** La diferencia es todo lo que el
  modelo no sabe.
- **El juego, medido.** Se gira en un sentido, se marca; se gira en el otro,
  se marca. La diferencia es el juego total de la cadena, amplificado 12×, o
  sea visible a simple vista. Es *el* número que impide subir la relación del
  varillaje, y hoy es una incógnita.
- **La amplificación real**, contra el 12× teórico.
- **El rozamiento y el par**, sin la complicación de un perfil que cambia.

Un excéntrico de 2 mm de excentricidad da 24 mm de recorrido en la punta:
grande, fácil de medir con una regla, y separa limpiamente la señal del ruido.

**Esto es E4 empezando, con 10 € de DM y sin esperar a ningún proveedor.**

### 3c. El cartucho real, y qué queda para él

Solo una cosa, pero es la que decide si el producto existe: **si el trazo
sale a las décimas prometidas**. Eso necesita la pieza de POM cortada a
±0,05 mm, y no hay atajo. Pero llega a un banco donde todo lo demás ya
funciona, y eso convierte un experimento con diez incógnitas en uno con una.

### 3d. El orden que propongo

1. Fijar el calaje y congelarlo (§1). Sin esto, lo que se dibuje se mueve.
2. Fichas de piezas comerciales con cotas de interfaz.
3. `contratos.json` y la tabla de variables.
4. Plataforma paramétrica en Onshape, talla M.
5. **Pedir las piezas comerciales ya**, en paralelo con 4. Tienen plazo de
   entrega y el CAD no.
6. Cartucho de calibración en DM. Montar, medir juego y par.
7. Cartucho mudo en DM. Montar entero, comprobar que se mueve y escribe algo.
8. Corregir el modelo con lo medido.
9. Y entonces sí, encargar el bloque de POM.

---

## 4. El dossier completo de fabricación

Cinco cuadernos, y van separados porque los lee gente distinta en momentos
distintos. Mezclarlos es cómo alguien acaba cortando por una vista a escala
libre.

### Cuaderno 1 · Plantillas de corte 1:1 — `plantillas.pdf`

**Ya existe** (`emit/template.py`). Para el carpintero, sobre el tablero.
Escala 1:1 exacta, cuadro de calibración en cada hoja, semántica de línea en
blanco y negro, siete metadatos por pieza.

Lo que le falta: **una plantilla por material y espesor**, no por conjunto.
El carpintero corta todo el DM de 5 mm de una vez, no va pieza a pieza.

### Cuaderno 2 · Dossier de montaje — `dossier.pdf`

**No existe.** `emit/dossier.py` está en la estructura y vacío. Es el hueco
grande. Debería llevar:

- Vista de conjunto, tres ortográficas y una isométrica, con cajetín.
- **Explosionado por subconjunto**, no uno global ilegible: cartucho,
  seguidor (×3), cinco barras, palanca del lápiz, accionamiento, bastidor.
- **Secuencia numerada** con una imagen por paso, qué piezas entran, qué
  herramienta hace falta y qué hay que comprobar **antes de seguir**.
- **Las cotas de puesta a punto**, que son las que no están en ninguna pieza:
  el calaje de cada brazo, la precarga del muelle, el juego axial de la pila,
  la altura del lápiz sobre el papel.
- **La fase cero**: dónde está la marca, cómo se verifica, y qué pasa si se
  monta mal. Con foto.
- Plantilla de taladrado del bastidor, 1:1, aparte.

### Cuaderno 3 · Hoja de ruta del taller — `taller.pdf`

**No existe y es el que más falta hace en un taller ocupacional**, porque el
dossier de montaje asume a alguien que sabe leer un plano.

- Orden de operaciones con tiempo estimado por operación.
- Qué operaciones son de qué nivel de habilidad, para repartir el trabajo.
- **Galgas pasa / no pasa** en vez de cotas. Esto es lo importante: en lugar
  de «comprueba que quedan 9,5 mm», una galga cortada en el mismo DM que
  entra o no entra. Verificación sin instrumento, sin interpretación y sin
  saber leer un pie de rey. Se cortan con las mismas plantillas.
- Puntos de control con criterio **binario**: pasa o no pasa, nunca «más o
  menos bien».
- Qué hacer cuando no pasa, y a quién avisar.

### Cuaderno 4 · Verificación y ensayo — `verificacion.pdf`

- Hoja de comprobación final, para firmar.
- **La hoja de trazo patrón**, que es la idea que más rendimiento da por lo
  que cuesta: el compilador ya simula el trazo, así que puede **emitirlo
  como PDF a 1:1**. Se pone esa hoja bajo la máquina, se gira la manivela, y
  se ve si el lápiz cae sobre la línea impresa. Cualificación visual, sin
  medir, por cualquiera. Un emisor nuevo de media tarde.
- Registro de la unidad: número de serie, fecha, quién la montó, qué cartucho
  lleva, qué medidas dio. Es también el dato de `bench/` que alimenta E4.

### Cuaderno 5 · Lo que va al cliente — `manual.pdf`

- Cómo se usa y a qué velocidad se gira.
- **Cómo se cambia el cartucho y cómo se verifica la fase.** Si el cliente
  puede comprar cartuchos nuevos —y debería poder—, esta página es el
  producto.
- Mantenimiento: qué se lubrica y qué no, cada cuánto.
- La frase, la fecha, y quién lo fabricó. En un producto cuyo argumento es
  que lo hacen personas, eso no es decoración.

### De dónde sale cada cosa

| Cuaderno | Quién lo genera | Estado |
| --- | --- | --- |
| Plantillas 1:1 | `emit/template.py` | **Hecho** |
| DXF de corte | `emit/dxf.py` | **Hecho** |
| Cartucho 3-D | `emit/step.py` | **Hecho** |
| Trazo patrón | emisor nuevo, del simulador | Media tarde |
| Dossier de montaje | `emit/dossier.py` + vistas de build123d | El hueco grande |
| Hoja de taller y galgas | Plantilla fija + datos del pedido | Por diseñar |
| Manual del cliente | Plantilla fija + la frase | Por diseñar |

Los tres primeros ya salen de `compile.cli`. Los cuatro restantes entran por
el mismo sitio, `emit/paquete.py`, que ya decide qué archivos salen.

---

## 5. Utillajes y galgas

Piezas que no van en la máquina pero sin las cuales la máquina no sale igual
dos veces. Se cortan con las mismas plantillas y del mismo material.

| Utillaje | Para qué | Por qué importa |
| --- | --- | --- |
| **Plantilla de taladrado de postes** | Los tres postes a 71,1 mm y 120° | Si esto se descuadra, no hay ajuste posterior que lo salve |
| **Galga de calaje** | Cala el brazo sobre el eje del seguidor | Montarlo mal escribe basura, y no se nota hasta el final |
| **Galga de fase** | Verifica que el cartucho entra calado | Confirma el poka-yoke en vez de confiar en él |
| **Galga pasa/no-pasa del hueco** | El hueco leva-poste | Verificación binaria, sin pie de rey |
| **Pivote de lijado** | Redondear discos a mano | Es lo que hace posible el cartucho de calibración |
| **Cuna de montaje** | Sujeta el bastidor mientras se monta | Dos manos no bastan para un cinco barras |

---

## 6. La metodología de pedido

Lo que pasa desde que un cliente escribe hasta que sale una caja.

1. **Captura.** El cliente escribe en el lienzo. La interfaz **enseña la caja
   de escritura mientras escribe** y avisa si se sale. Un rechazo en el
   momento de escribir es una molestia; el mismo rechazo tres días después es
   un pedido perdido.
2. **Compilación.** El compilador devuelve veredicto: apto, o no apto con
   motivo y sugerencia. Ya funciona así.
3. **Talla.** Si no cabe en M, se prueba L. Si no cabe en L, se dice que no y
   se propone acortar. El cliente elige talla, no configura una máquina.
4. **Presupuesto.** Sale del informe: cartucho a precio cerrado más
   plataforma de stock. **No hace falta compilar para dar precio**, porque el
   bloque cuesta lo mismo sea cual sea la frase.
5. **Fabricación.** El DXF al taller de corte; las plantillas, el dossier y la
   hoja de taller a producción; la plataforma sale del stock.
6. **Verificación.** Hoja de trazo patrón, comprobación final, registro.
7. **Entrega.** Máquina, manual y el certificado con su frase.

Los pasos 1 a 4 son minutos y no tocan a nadie del taller. Es lo que permite
que un producto artesanal se pida por internet.

---

## 7. Qué hay que construir, por orden de lo que desbloquea

| | Qué | Por qué ahora |
| --- | --- | --- |
| 1 | **Fijar el calaje** a una constante de máquina | Sin esto el brazo no es pieza de stock y lo que se dibuje se mueve |
| 2 | Enchufar **C4** al compilador | El presupuesto de error deja de ser una estimación |
| 3 | **Fichas de piezas comerciales** | Evita la clase de error del Ø15 |
| 4 | **`contratos.json`** y la tabla de variables de Onshape | Un número, un sitio |
| 5 | **Pedir las piezas** | Tienen plazo; el CAD no. Va en paralelo |
| 6 | **Emisor de trazo patrón** | Media tarde, y da el método de verificación entero |
| 7 | **Plataforma paramétrica** en Onshape, talla M | Ya se puede: los parámetros están fijos |
| 8 | **Cartucho de calibración** en DM | E4 empieza aquí, sin esperar a nadie |
| 9 | **`emit/dossier.py`** | El hueco grande. Necesita el 3-D del 7 |
| 10 | Hoja de taller y galgas | Necesita el dossier del 9 |

Del 1 al 6 no hace falta CAD ni proveedor: son código, datos y una llamada de
teléfono. Del 7 en adelante, sí.
