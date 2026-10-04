# Contratos congelados

Un contrato congelado es lo que hace que un módulo fabricado hoy encaje en una
máquina construida dentro de tres años. **No se modifica sin decirlo en voz
alta y sin registrar el cambio aquí, con fecha y motivo.**

Un contrato solo vale si algo lo comprueba. Cada uno dice al final qué test lo
defiende; si no hay test, es una intención, no un contrato.

---

## Contrato de fase · CONGELADO 2026-09-29

**El cartucho es una sola pieza lógica y solo se puede montar de una manera.**

Es el contrato que evita el fallo más caro del proyecto: un cartucho calado
donde no toca escribe basura, y no se nota hasta que se gira la manivela.

### Qué se congela

| | |
| --- | --- |
| Cero lógico | θ = 0 del árbol maestro, que es el eje **+X** del marco de la leva |
| Taladro del eje | Ø10 mm, centrado. **Centra, no orienta** |
| Pasador de índice | Ø3 mm, **largo 24**, a **18 mm** del centro, sobre +X |
| Marca grabada | Una línea del pasador al borde, rotulada `FASE 0`. Apunta al pasador |
| Alcance | **Las tres levas y los separadores llevan el pasador en el mismo sitio** |
| Ajuste | **Deslizante en las tres levas** (POM, H8). Apretado solo en el cubo de latón del cartucho, el antiguo «plato de arrastre» |

### Por qué así

**Dos referencias que puedan discrepar son peores que ninguna.** El taladro
del eje deja girar la leva a cualquier ángulo: centra pero no orienta. Con un
segundo taladro fuera del centro solo hay una forma de meter los dos, y el
error de fase deja de ser posible en vez de ser improbable.

El pasador está **en el mismo ángulo en las tres levas**. Ahí está lo que
convierte tres discos sueltos en un cartucho: enhebradas en el mismo pasador
quedan caladas entre sí sin que nadie las alinee. De las tres referencias de
fase que había —leva contra leva, leva contra leva, cartucho contra árbol—
queda **una sola**, y es física.

Un pasador y no una cara plana en el eje: en 5 mm de POM una cara plana sobre
un agujero de Ø10 tiene poca superficie de apoyo y se redondea con el uso. El
pasador toma el par —48 mN·m sobre 18 mm son 2,7 N, nada— y el agujero
redondo se queda como lo que es, un cojinete.

**El pasador no aprieta en el POM.** Un DIN 6325 es m6, un ajuste pensado para
apretar en acero, y el POM fluye en frío: la interferencia se relaja en semanas
y el calaje se pierde **después de la venta**, en silencio y sin que nada avise.
El pasador va deslizante en las tres levas y apretado en un solo sitio, el cubo
de latón del cartucho, que lo lleva (hasta el 2026-10-04 se llamaba «plato de
arrastre» y no estaba definido; ver el contrato de cartucho). El argumento del contrato no cambia —sigue
habiendo una sola forma de enhebrar las tres levas— y deja de depender de una
interferencia sobre plástico.

La marca grabada no añade una referencia: **señala la que hay**. Sale del
pasador y llega al borde, para que la pieza y el dibujo digan lo mismo.

### Qué lo comprueba

`tests/compile/test_escribiente.py`:
`test_las_tres_levas_llevan_el_pasador_en_el_mismo_sitio`,
`test_el_pasador_cae_en_material_y_no_en_el_taladro_del_eje`,
`test_la_marca_grabada_apunta_al_pasador_y_no_a_otro_sitio`,
`test_dos_frases_distintas_comparten_el_mismo_pasador`.

**La fase del cartucho respecto de la plataforma** no la da el pasador sino la
garra del eje motriz, que solo entra en la ranura descentrada de la cabeza
del eje del cartucho en fase cero. Es del contrato de cartucho, más abajo.

---

## Contrato de eje · CONGELADO 2026-09-29

| | |
| --- | --- |
| Diámetro | **Ø10 mm**, tolerancia **h6** (eje del cartucho, muñón y eje motriz) |
| Sentido de giro | Horario visto desde arriba, θ creciente |
| Índice | Un pasador Ø3 × 24 transversal, a 18 mm del centro (ver contrato de fase) |
| Pila del cartucho | 3 levas de 5 mm + 2 separadores de 2 mm = **19 mm** |
| Altura máxima de pila | 80 mm |

Ø10 porque es la medida de varilla calibrada más corriente y porque tiene
rodamiento barato en cualquier catálogo. La pila de 19 mm sale de la
geometría y la comprueba `tests/compile/test_conjunto.py::test_la_pila_son_tres_levas_y_dos_separadores`.

**Lo que no se congela todavía:** el rodamiento concreto. Depende de la
investigación de proveedores y de medir el juego en el banco (E4). La
retención axial, que también estaba aquí abierta, la resuelve el cartucho
entre puntos: la garra baja empujada por su muelle y aprieta la pila contra
el muñón (contrato de cartucho).

El «árbol» deja de ser una pieza (2026-10-04): son tres ejes Ø10 h6 en línea,
el muñón de abajo, el eje del cartucho y el eje motriz de arriba. El
diámetro, el sentido y la pila no cambian.

---

## Contrato de cartucho · PENDIENTE

**La interfaz entre la plataforma, que va a stock, y el cartucho, que se
fabrica por pedido.** Se congela cuando el primer cartucho entre y salga en el
banco (H3.5 del baseline): a partir de ahí, todo cartucho vendido tiene que
caber en toda plataforma vendida.

El cartucho va **entre puntos**, como una pieza en el torno: abajo, un muñón
de la plataforma con una horquilla en U donde entra de lado el tetón del eje
del cartucho; arriba, una garra que baja con un muelle y mete su lengüeta en
la ranura de la cabeza del eje. Se saca hacia atrás, entre los postes 1 y 2.

| | |
| --- | --- |
| Radio máximo de leva | **55,5 mm**: el hueco entre los postes traseros (115,1) menos 2 de paso a cada lado. Lo vigila el compilador: `cartucho_no_sale` |
| Dirección de salida | 60° en el marco de la leva: lejos del poste 3, hacia atrás. **Por ahí no puede ir nada** entre el plato 1 y los seguidores |
| Bajo las levas | 1 de holgura + 4 del muñón con su horquilla + 5 del cubo = `leva_sobre_plato` **10** (eran 2) |
| Eje del cartucho | Ø10 h6 × 27: cubo, pila y 3 de cabeza ranurada. Tetón Ø5 × 4 debajo |
| Cubo | Latón Ø24 × 5, con el pasador m6. Es el antiguo «plato de arrastre» |
| Garra | Ranura de 3 × 3 **descentrada 1,5**: girada media vuelta no coincide, así que solo entra en fase cero. Carrera 5 |
| Holgura de paso | 1 mm al sacar y meter, que es a mano y despacio |

Lo comprueban `tests/compile/test_contratos.py` (que las cotas sumen lo que
tienen que sumar y que la ranura solo entre de una manera) y
`tests/emit/test_montaje.py::test_el_cartucho_sale_por_detras_entre_los_dos_postes`.

---

## Contrato de calaje · CONGELADO 2026-09-30

**El ángulo al que se cala cada brazo sobre el eje de su seguidor es una
constante de la máquina, no un resultado del pedido.**

| | |
| --- | --- |
| Referencia de los dos brazos | El **centro de la caja de escritura**: (0, `caja_centro_y`) |
| Referencia de la palanca | **Media altura** de levantamiento |
| Brazo izquierdo | **-3,749°** con la geometría por defecto |
| Brazo derecho | **-176,251°** |
| Palanca del elevador | **+2,149°** |

### Por qué

El calaje se calculaba como la media de los ángulos del brazo a lo largo del
ciclo. Eso minimiza el barrido de la leva —sale lo más pequeña posible— pero
**la media depende de por dónde escriba el cliente**: entre cuatro frases de
prueba se movía de -2,10° a -5,41°, un rango de 3,3°. Sobre 90 mm de brazo
proximal, 5 mm de trazo desplazado.

La consecuencia es la que importa: con el calaje dependiendo de la frase, **el
brazo no es pieza de stock**. Habría que calarlo en cada pedido y no se podría
premontar la plataforma, que es justo lo que el modelo plataforma-más-cartucho
necesita.

Con la referencia fija la leva crece o encoge unas décimas según la frase —con
«hola» el radio máximo baja de 54,08 a 53,83 mm; con un barrido de toda la
caja sube de 54,45 a 54,66— y el brazo vuelve a calarse una sola vez, en el
diseño.

La referencia no es arbitraria: el centro del papel es donde la punta pasa más
tiempo, así que el barrido del seguidor queda repartido a los dos lados en vez
de irse a un extremo.

### Qué lo comprueba

`tests/compile/test_escribiente.py`:
`test_el_calaje_es_una_constante_de_la_maquina_y_no_del_pedido`,
`test_el_calaje_es_el_angulo_del_brazo_en_el_centro_de_la_caja`,
`test_fijar_el_calaje_apenas_cuesta_radio_de_leva`.

---

## Contrato de bastidor · PENDIENTE

Hay números que la geometría ya fija y que **no** se congelan hasta que el
banco diga que el modelo predice:

- Postes de seguidor: tres, a **71,1 mm** del árbol, repartidos a 120°.
  Sale de `hypot(radio_base, brazo_seguidor)` = `hypot(55, 45)`.
- **La pila es escalonada.** El eje de cada rodillo baja desde el plano único
  de seguidores hasta su leva pasando junto a las que tiene encima; con las
  tres del mismo radio base, el de abajo las atravesaba casi 2 mm. Cada leva
  es ahora más pequeña que la de debajo: de abajo arriba, **elevador R 55,
  derecho R 48,4 e izquierdo R 39,6** de radio base. No se mueve el bastidor:
  con el poste fijo, un brazo de seguidor más largo da una leva más pequeña
  (`radio_base² + brazo² = 71,06²`), y los brazos son **45, 52 y 59**, los
  tres agujeros de rodillo de UN solo seguidor. El izquierdo va al revés para
  dejar libre el pasillo por el que sale el cartucho. El compilador lo vigila:
  `eje_de_rodillo_contra_leva` si un eje pasa a menos de 2 mm de una leva.
- Poste de seguidor de **Ø8** con casquillo igus GFM-0810. **Lo que la leva ve
  no es el poste: es la valona del casquillo**, que mide **Ø15** —confirmado
  en la ficha del fabricante, d3 = 15 mm—. Con los Ø16 que se suponían antes
  y un casquillo de bronce con valona de Ø28, el hueco caía a 3,0 mm y
  saltaba el aviso. El Ø16 nunca estuvo justificado: la fuerza tangencial en
  el seguidor es de 0,7 N.
- Hueco entre la leva mayor y ese obstáculo: **11,3 mm** con «hola» (9,7
  antes de escalonar la pila; la mayor es ahora la del elevador). Encoge
  cuando la frase crece —8,9 mm con un barrido de toda la caja— y es el
  límite de conjunto que decide qué frases caben.
- Caja de escritura: 80 × 30 mm, centrada a 100 mm sobre la línea de pivotes.
- **Del cinco barras se acotan las distancias entre ejes, no el contorno.** Un
  brazo es, para la cinemática, una distancia entre dos agujeros; ancho,
  espesor y material no cambian ningún número del compilador y se deciden en
  el CAD. Los agujeros de codo y punta tampoco están aquí: no los fuerza
  ninguna pieza que ya exista.
- **Los codos van hacia fuera**, que es la rama más lejana de la singularidad
  del brazo estirado, y la consecuencia visible es que los dos proximales se
  cruzan: con la punta en el centro de la caja, los codos caen a 5,9 mm **por
  debajo** de la línea de pivotes.
- **El amplificador 6:1 es un cabestrante de cinta**: sector de R 48 en el
  poste del seguidor, tambor de R 8 en el eje del brazo, fleje de 1.4310 de
  0,05 × 5 anclado por los dos extremos. La relación es el cociente de
  radios y es exacta; una cinta anclada no desliza.

  **Los radios del contrato son los de la FIBRA NEUTRA, y los mecanizados
  valen medio espesor menos.** Restar lo mismo a dos números no conserva su
  cociente: tornear 48 y 8 daría 5,9844 en vez de 6, un 0,26 % de escala de
  menos en todo lo que escriba la máquina, sistemático y sin aviso.

  **Espesor 0,05 y no 0,1**: arrollada en el tambor de R 8, la de 0,1 trabaja
  a 1206 MPa con una relación r/t de 80, por debajo del 100 que se respeta en
  una cinta que va a doblarse millones de veces. **Ancho 5** porque el sector
  es una plancha de POM de 5, el mismo material y el mismo corte que las
  levas: con 10 hacían falta dos laminadas, una operación de montaje más por
  canal, a cambio de 0,046 mm de elasticidad.

  **La cinta deja el sector a ±54° de la línea de centros** —`cos t = (R−r)/a`,
  porque el radio a la tangencia es perpendicular a la cinta— y **abraza los
  252° del lado opuesto al tambor**. Los anclajes van justo por fuera de esos
  dos puntos.

  **El sector es un disco entero y ninguna de las dos piezas lleva pestañas.**
  La muesca de 80° en el lado libre no compraba nada —el ramal sale tangente
  y se aleja, el tambor queda a 10 mm del borde y los discos vecinos se llevan
  27— y además daba a la pieza una orientación que un disco con un agujero no
  tiene. Y las pestañas no hacen falta porque la cinta va anclada por los dos
  extremos: no puede andar sin estirarse. Lo que sí hay que respetar es que
  los dos asientos queden **coplanarios dentro de 0,2 mm**, que es un criterio
  y no una medida: lo mide E4.
- **Dónde está el cinco barras respecto de las levas.** Hasta ahora eran dos
  sistemas de coordenadas sin transformación entre ellos: las levas con el
  árbol en el origen y el cinco barras con sus pivotes en ±60. El marco del
  brazo queda en (−16,225, −28,103) y girado 150°, que lleva los pivotes
  junto a sus postes y el centro del papel a 132,5 mm del árbol.

  **Es una elección de empaquetado, no una consecuencia.** Con engranajes el
  entre-ejes lo habría fijado la relación de diámetros; con cinta es libre,
  así que la separación de 120 mm entre pivotes se queda como estaba y el
  marco se coloca donde conviene. Mover estos tres números no cambia ningún
  número que calcule el compilador.
- **El amplificador va en su propio plano.** Con cualquier radio de sector
  que dé la relación 6, el arco se acerca a unos 53 mm del árbol y la leva
  tiene 55 de radio base. No es cosa de la cinta: con engranajes pasaba
  igual.

No se congelan porque el radio base puede moverse cuando E4 mida el juego
real: la relación del varillaje, el radio base y el diámetro de la leva son
un solo compromiso, y todavía falta el dato que lo cierra.

---

## Dónde vive el calaje · DECIDIDO 2026-10-01

El calaje del brazo —el ángulo al que se monta sobre su eje— **no se mecaniza
en ninguna pieza**. Lo da la mordaza de la cinta, deslizando antes de apretar.

### Por qué no puede estar mecanizado

La cinta entra al tambor por un radio de 8 mm y el brazo mueve la punta con una
palanca efectiva de 172,5. Así que:

> **1 mm de error en la longitud libre de la cinta son 21,6 mm en la punta.**

Un fleje cortado y anclado a mano no tiene esa longitud a la décima, y a la
décima ya son 2,2 mm. Con anclajes en agujeros fijos la máquina saldría calada
donde cayera, y el error sería **invisible y permanente**: nadie puede medir una
longitud de cinta montada, y no hay forma de corregirla sin rehacer la pieza.

Con el ajuste en el anclaje el error sigue existiendo, pero es **visible y
corregible**: se afloja, se desliza y se vuelve a apretar.

### Cómo se cala, y cómo se sabe que está bien

1. Cartucho en fase cero, que lo garantiza el pasador de índice.
2. Brazo sujeto a su calaje.
3. Se tensa la cinta tirando, se desliza la mordaza y se aprieta.
4. **Se comprueba con la hoja de trazo patrón** (`emit/patron.py`): se pone
   debajo, se gira la manivela y se mira si el lápiz cae sobre la línea.

El paso 4 no es un extra. Es lo que convierte un ajuste en una verificación, y
ya existía: su lista de lo que caza empieza por «un brazo con el calaje
equivocado». Sin él esto sería cambiar un error imposible por uno ajustable;
con él es cambiarlo por uno que se ve.

Sí va contra el patrón del pasador de índice —no hacer el error improbable,
hacerlo imposible—. La diferencia es que aquí lo imposible no estaba
disponible: la alternativa no era un error imposible, era uno invisible.

### La mordaza agarra por rozamiento, y eso lo decide la cinta

Lo natural en un anclaje de fleje es darle media vuelta a un pasador para que
agarre por arrastre y no solo por fricción. **No se puede**: un fleje de 0,05 no
se arrolla a menos de cien veces su espesor sin pasarse de flexión, o sea 5 mm
de radio, y un pasador de Ø10 no cabe en una mordaza.

No hace falta. Un M3 a 0,3 N·m da unos 188 N de agarre por rozamiento entre dos
caras, contra una carga de trabajo de unos pocos newton.

### Y el tensor no puede llevar muelle

| | |
| --- | --- |
| Estirar la cinta a 5 N | **5,8 µm** |
| Recorrido para calar el brazo ±10° | **1,4 mm** |

Son 241 a 1. El anclaje tiene que moverse milímetros para calar y luego sujetar
a micras para tensar, y **un tornillo tensor no hace las dos cosas**: a paso 0,5,
una vuelta son 500 µm, es decir pasar de nada a 430 N.

Meter un muelle en serie daría la compliancia que falta, y reintroduciría
exactamente la flexibilidad por la que se eligió la cinta en lugar de los
engranajes. Por eso el recorrido lo da el **deslizamiento** de la mordaza y la
tensión la da el **tirón** antes de apretar: la ranura resuelve los milímetros y
el apriete resuelve las micras.

### Lo que esto simplifica

El **eje de pivote** deja de llevar ángulo. Era la pieza que iba a traer el
calaje mecanizado a cuatro decimales, con una por lado; ahora es una barra Ø10 h6
con una cara plana a 4 del eje, igual en los tres sitios y cortada a medida. El
**tambor** se aprieta donde caiga.

### Qué queda abierto

**Dónde se ancla el segundo extremo — ya no está abierto: lo cerraron los
números que ya estaban escritos.** Se dijo que el contrato soportaba dos
arreglos, las dos mordazas en el sector con la cinta rodeando el tambor o una
en cada pieza. No los soporta: **una mordaza en cada pieza**, porque dos en el
sector obligan a que uno de los dos ramales cruce.

| | Una en cada pieza (correa abierta) | Las dos en el sector (un ramal cruzado) |
| --- | --- | --- |
| Vano recto | `sqrt(a²−(R−r)²)` = **54,990908** | `sqrt(a²−(R+r)²)` = 38,574603 |
| Abrazado al sector | **252,064°** | 290,879° |

`amplificador_vano_libre` vale 54,990908 y el abrazado al sector 252,06°, con
test. Son los dos números de la correa abierta, a seis decimales y por dos
caminos distintos. El otro arreglo no aparece por ningún lado.

Lo que sí queda por cerrar es **dónde cae la mordaza en el tambor**, y con
cuánto margen. Los 185° de `amplificador_tambor_abrazado` son 107,94 de correa
abierta más 33 de barrido más **44 repartidos en «dos anclajes»**, y en el
tambor hay uno solo: o el margen es generoso a propósito, o el número se
calculó con el arreglo que los números descartan. Se vuelve a derivar al
dibujar el tambor, que es la pieza a la que afecta.

---

## Contrato de base · PENDIENTE

La tabla de nogal. La **planta está cerrada** y la **altura no**, y por eso el
grupo entero está pendiente: todo lo vertical cuelga de `base_al_plato`, que
no se puede decidir hasta saber cómo se sujeta el portaminas.

### El marco de la base es el del cinco barras

La máquina no tenía frente declarado. Lo tiene de balde: el centro de la caja
de escritura cae a **240° exactos** del árbol en el marco de la leva, porque
la caja está sobre el eje +Y del cinco barras y ese marco está girado 150°.
Visto desde el cinco barras, entonces, todo sale simétrico:

| | x | y |
| --- | --- | --- |
| árbol | 0 | −32,451 |
| pivotes del cinco barras | ±60 | 0 |
| postes de seguidor | ±61,543 y 0 | −35,532 y +71,063 |
| plato Ø170 | ±85 | −117,45 … +52,55 |
| caja de escritura | ±40 | 85 … 115 |

Es lo que convierte la base en un rectángulo centrado en vez de una tabla con
la máquina de medio lado. **No hace falta cota para ello**: la base se sitúa
en el conjunto por sus tres agujeros, que son los de los platos.

### La planta la cierran el plato y la tarjeta

Nada más. Por detrás manda el plato —85 de radio—, por delante el borde
lejano del papel, y a los lados el plato otra vez. Con **10 mm de nogal a las
cuatro puntas** salen **190 × 275 × 25**.

`docs/ficha-producto.md` decía «210 × 160 mm de base»: se escribió antes de
saber dónde cae el papel y el fondo se queda **115 mm corto**. Eso mueve la
línea del nogal, que se presupuestaba a 13 bases por tabla de 2 m.

El papel es un **A7 apaisado**, 105 × 74, centrado en la caja de escritura y
no en la tabla. Deja 12,5 a los lados de los 80 de la caja, 22 delante y
detrás de los 30, y su borde cercano queda a 10,45 del canto del plato: si
entrara por debajo, la tarjeta no se podría poner ni quitar sin mover la
máquina.

### Los postes bajan hasta la base y hacen de pata

No hay pilar. Es el mismo argumento que hizo del tercer plato la misma pieza:
un pilar propio obligaría al plato 1 a llevar tres agujeros que los otros dos
no tienen, y los tres platos dejarían de ser intercambiables.

A cambio el poste crece. Y de paso se acaba el «70 de antes», que era un
número heredado con el vano entre platos escondido dentro:

```
poste_largo 195 = 15 empotrado en el nogal
                + 75 base_al_plato      <- PENDIENTE
                + 27 tres platos de 9
                + 58 poste_vano
                + 20 reductor_bahia
```

`poste_vano` es nuevo y es lo que antes no estaba declarado: dentro van la
pila de 19 sobre 2 de holgura, el seguidor y el sector hasta 33, y los 25 que
se lleva la cinta con sus dos mordazas.

Los tres agujeros de la base son el patrón de los platos visto desde otro
datum. Aquí no hay árbol que poner en el origen, así que el datum es un poste
y el siguiente va sobre +X; como los tres están a 120° del árbol, el
triángulo es **equilátero** y se acota con un lado y 60°. Son agujeros
**ciegos**, 15 de los 25, para que no asome el acero por debajo.

### Por dónde pasa la mano

Tres números que salieron al cerrar la planta y que conviene tener delante:

- El **volante** gira entero dentro de la tabla. Son 294 g de latón al
  alcance de una manga.
- El **pomo de la manivela** se sale **19 mm por la izquierda**, y por detrás
  le sobran 19.
- En su paso de delante, la manivela cruza **29 mm sobre la tarjeta**, a unos
  190 mm de altura.

No choca con nada. Lo que hace es que la mano pase una vez por vuelta sobre
lo escrito, y que la máquina no se pueda arrimar a una pared por la
izquierda. Viene de que el eje de la manivela se colocó en el marco de la
**leva** —a −90° allí— sin mirar dónde cae eso visto desde quien escribe: en
el marco de la base queda a **120°**, arriba y a la izquierda. Ponerlo a −90°
del marco de la base lo dejaría atrás y simétrico, y **costaría redibujar la
platina, que ya está entregada**. El número está escrito para que esa
decisión se tome con él delante.

### Lo que falta

`base_al_plato` son **60 ESTIMADOS** (2026-10-04). Fueron 75 provisionales,
elegidos para que la máquina midiera los 200 de alto de la ficha; ahora los
fija el portaminas, con medidas estimadas mientras no haya un ejemplar en la
mano: 152 de largo, cuerpo de 8, agarre hasta 40 y de Ø9, clip de 50. La
ventana sale de 46 a 74 y se toma el CENTRO, que es lo que deja sitio a los
dos lados cuando lleguen las medidas de verdad. Con él se mueven el poste
(180) y el tirante (105,5). La máquina baja 15 mm.

**Ya se sabe qué lo fija** (2026-10-04): la pinza del portaminas cuelga del
plato 1 y tiene que apretar plástico liso, por encima del agarre metálico y
por debajo del clip. Eso da una ventana —46..72 con un portaminas de 150, 40
de agarre y 50 de clip— y el 75 de hoy caería fuera. `compile/portaminas.py`
la calcula y `scripts/medir_portaminas.py` la cierra con el lápiz medido.

`eje_pivote_largo` ya no está aquí: no depende de `base_al_plato`, sino de lo
que se apila entre el collar del proximal y el tambor, todo colgado del plato
1. Son **55**, uno solo para los dos lados.

---

## Contrato de levantamiento · PENDIENTE

El canal 3 no tenía etapa de salida. Tres señales lo decían: `eje_pivote` eran
tres y la platina solo tiene dos agujeros de Ø10; un cabestrante exige ejes
paralelos y el lápiz tiene que subir; y `PalancaElevadora` vale igual para un
eje horizontal que para cualquier conversor 1:1, así que el modelo tampoco lo
decidía.

### Lo que la medida tumbó

La primera propuesta era bajar el canal 3 a 1:1, con el argumento de que el
6:1 no compraba nada y costaba un factor seis de alzada. **Medido, es falso.**

| arco \ relación | 1 | 2 | 3 | 6 |
| --- | --- | --- | --- | --- |
| **8°** | 41,4 ✗ | 23,8 ✓ | 16,4 ✓ | **8,3 ✓** |
| 16° | 23,9 ✓ | 12,4 ✓ | 8,4 ✓ | 4,2 ✓ |

Ángulo de presión máximo contra un límite de 30. El levantamiento es un
**evento**: sube 3 mm en 8° de θ, y lo que dispara la presión es la pendiente,
no la amplitud. A 1:1 la leva se autointerseca.

Y la alzada pequeña que preocupaba —0,563 mm— no importa: ±0,05 de corte más
0,040 de polígono dan ±0,48 mm sobre un levantamiento de 3, y el lápiz solo
tiene que librar el papel. **No es una cota de precisión.**

Consecuencia: **la leva no cambia, la relación sigue siendo 6, `calaje_elevador`
no se mueve y los golden no se regeneran.** `core/` y `compile/` no se tocan.

### Lo que sí cambia: quién hace el 6:1

Un **balancín** en vez de un cabestrante. Da el cuarto de vuelta *y* la
relación en una pieza, y con él desaparecen del canal 3 el sector, el tambor,
sus dos mordazas y un eje: `sector` y `tambor` pasan a ×2, `mordaza` a ×4 y
`eje_pivote` a ×2.

El pasador que lo ataca va en **el agujero que dejó el sector**, a 38 del
pivote, así que el seguidor sigue siendo la misma pieza en los tres canales.

### La bieleta, que no era de 25 (2026-10-04)

La bieleta de 25 suponía que **el pasador del seguidor 3 estaba en el eje de
simetría** del cinco barras. No está ahí: el seguidor apunta a 9,3° en el
marco de la leva, y el pasador cae en **(−29,41, 14,55)**. Con la de 25
estirada hasta ese punto, la bieleta trabajaba a 37° del movimiento del
seguidor y **la mesa bajaba 2,45 mm en vez de 3**.

La solución es una bieleta **isógona**: se orienta para que el balancín se
mueva exactamente lo mismo que el pasador, así que la relación vuelve a ser 6
sin tocar la leva, el balancín ni su pared.

- **No hace falta «tracción pura».** Una bieleta articulada en sus dos
  extremos solo trabaja a tracción o compresión con cualquier ángulo. Lo que
  el ángulo cambia es la relación.
- **Mide 60,24** y lo calcula `compile/levantamiento.py`.
  `tests/compile/test_levantamiento.py` la cruza con este contrato y resuelve
  la cinemática exacta: 3,000 mm de bajada.

Con ella se mueven tres cosas:

- **El balancín apunta HACIA ARRIBA**, con su cara plana girada
  `balancin_chaveta_angulo` = 90°. Así la palanca y él van en un eje de una
  sola cara plana. Hacia arriba y no colgando por el signo: en el compilador,
  una desviación positiva del seguidor 3 es lápiz arriba, y colgando ese
  empuje subía la mesa.
- **El eje del balancín** pasa a x = 25,028 (el tirante cae en 65 con la
  palanca a ±calaje, no en 64,97). Mide 96,75, y la palanca queda a 89,75 del
  balancín, no a 78: la pata de la bieleta atraviesa el balancín, que va
  por detrás de su codo para que la varilla no lo cruce.

### La pared que decide el diámetro del eje

`balancin_entrada` vale 38/6 = **6,333**, y no es una elección: es lo que la
relación obliga. De ahí sale lo demás, incluido que el eje sea de 4 y no de 10
como los otros tres:

| eje | pared entre el pasador y el agujero del eje |
| --- | --- |
| Ø10 | **−0,17** — el pasador entra DENTRO del agujero |
| Ø6 con M3 | 1,83 |
| Ø4 con pasador Ø2 | **3,33** ✓ |

La regla del repo pide 3. Con Ø4 y un pasador de Ø2 —la carga son 6,4 N, que
en un Ø2 dan 2 MPa de cortadura— quedan 3,33 sin forzar nada.

**Y arrastra la palanca del lápiz**, que cuelga de ese mismo eje: su cubo y su
cara plana dejan de ser los de un eje de 10. Es una pieza ya entregada y hay
que redibujarla.

### Por dónde baja

El tirante cae a **x = 65**, medido barriendo el cinco barras por toda la caja
de escritura: deja 19,6 mm a los brazos y 43,7 fuera del canto del plato, y
queda por fuera de la tarjeta. La línea central no vale: por ahí barren los
brazos.

### El lápiz deja de deslizar

Va **rígido** sobre una flexura de dos láminas de 1.4310 de 0,15 × 12 × 25:
1037 N/m, 0,52 N a 0,5 mm y 144 MPa, el 10 % del límite. Dos láminas y no una
en voladizo, que giraría la punta 1,5 veces la flecha partido por el largo.

Eso mete una cota nueva en el contrato y es la más fácil de olvidar:
**`mesa_planitud` = 0,5 mm** sobre los 105 × 74 de la tarjeta. Lo único que
absorbe el alabeo es la flexura, y 0,5 es todo su recorrido.

---

## Registro de cambios

| Fecha | Contrato | Cambio | Motivo |
| --- | --- | --- | --- |
| 2026-09-29 | Fase | Congelado. Pasador de índice Ø3 a 18 mm sobre +X, igual en las tres levas | El cartucho de una pieza deja el error de fase fuera de lo posible, en vez de fuera de lo probable |
| 2026-09-29 | Eje | Congelado Ø10 h7, pila de 19 mm, giro horario | Medidas corrientes de catálogo; la pila sale de la geometría y está comprobada |
| 2026-09-29 | Fase | **Añadido el ajuste** del pasador: deslizante en las tres levas, apretado solo en el plato metálico | El m6 del DIN 6325 aprieta en acero; en POM la interferencia se relaja por fluencia y el calaje se pierde tras la venta. La geometría congelada no se toca: Ø3 a 18 mm sobre +X |
| 2026-09-29 | Bastidor | Poste de seguidor de Ø16 a **Ø8**, y el hueco se mide contra la valona del casquillo y no contra el poste | Un poste lleva casquillo y la valona es mucho mayor que el eje. Con la valona de bronce de Ø28 el conjunto se quedaba sin hueco |
| 2026-09-29 | Bastidor | Corregida la valona del GFM-0810: **Ø15**, no Ø12. El hueco pasa de 11,0 a **9,5 mm** | El Ø12 se anotó de una investigación sin contrastar con el fabricante. La ficha de igus da d3 = 15 mm. Sigue holgado, pero con menos margen del que se dijo |
| 2026-09-30 | **Calaje** | Congelado. El calaje pasa de ser la media de los ángulos de la frase a ser el ángulo del brazo en el centro de la caja | Con la media, el calaje se movía 3,3° entre frases y el brazo dejaba de ser pieza de stock. Cuesta décimas de milímetro de leva |
| 2026-09-30 | Bastidor | Hueco al poste de 9,5 a **9,7 mm** con «hola» | Consecuencia de fijar el calaje. No es una decisión, es el número que sale |
| 2026-09-30 | Fase | Pasador de índice de Ø3 × 16 a **Ø3 × 24** | Con 16 no llegaba a la tercera leva de una pila de 19 mm, que es justo lo que el contrato promete calar. Lo encontró un test que cruza la ficha del pasador con la de la plancha y la del separador |
| 2026-10-04 | **Fase** | El «plato de arrastre» pasa a ser el **cubo de latón del cartucho**. Ningún valor cambia: Ø3 × 24 a 18 sobre +X | Aprobado con la propuesta del cartucho intercambiable. Era texto sin pieza |
| 2026-10-04 | **Eje** | Tolerancia de h7 a **h6**; el árbol se parte en muñón, eje del cartucho y eje motriz; la retención axial la da la garra | Aprobado con la propuesta. La pieza ya era h6 |
| 2026-10-04 | Cartucho | **Nuevo contrato, pendiente**: radio máximo 55,5, salida a 60°, muñón, cubo, garra con ranura descentrada | La interfaz plataforma-cartucho estaba repartida en textos y no la vigilaba nada |
| 2026-10-04 | Bastidor | `leva_sobre_plato` de 2 a **10**, `eje_pivote_largo` de 55 a **63**, `apoyo_balancin_alto` de 27 a **19**, `tirante_largo` de 105,5 a **113,5** | Sitio para el muñón y el cubo bajo las levas; lo demás es lo que cuelga de la pila |
| 2026-10-04 | Bastidor | **Pila escalonada**: radios base 55 / 48,4 / 39,6 (elevador abajo, derecho, izquierdo arriba), brazos de seguidor 45 / 52 / 59 en una sola pieza, izquierdo al revés, descuelgues 21 / 14 / 7 reasignados. Hueco al poste de 9,7 a **11,3 mm** | Al meter los rodillos y sus ejes en el montaje 3D, el eje del rodillo de abajo atravesaba las dos levas de encima entre 1,4 y 2 mm en los tres casos de referencia. No toca ningún contrato congelado: calaje, fase y pila de 19 siguen igual |
| 2026-10-01 | Bastidor | **Añadido el amplificador 6:1**: cabestrante de cinta, sector R 48 y tambor R 8 | Era un escalar en el código sin mecanismo. Se eligió frente a engranajes por el juego: un par de calidad 8d daba 1,98 mm en la punta y llevaba el peor caso de 2,84 a 6,74; la cinta da 0,0115 |
| 2026-10-01 | Bastidor | **Añadida la transformación** entre el marco de la leva y el del cinco barras: origen (−16,225, −28,103), 150° | Eran dos sistemas de coordenadas sin relación. Con cinta el entre-ejes es libre, así que es una elección de empaquetado y `brazo_separacion` no se toca |
| 2026-10-01 | Bastidor | **Añadidas las cotas del cabestrante**: fibra neutra y canto mecanizado del sector y del tambor, cinta, tangencia y arcos | La relación la fija la fibra neutra y no el canto; la tangencia cae a 126° y no a 54, así que el sector necesita 140° de semiarco y no 25 |
| 2026-10-01 | Bastidor | **Añadidos `brazo_palanca` y `brazo_eje_diametro`** | El primero faltaba: la palanca del lápiz es una longitud de máquina que el compilador usa y el CAD necesita. El segundo estaba conflado con `eje_diametro`, que es el árbol de levas: son el mismo stock Ø10 y dos ejes distintos |
| 2026-10-01 | Bastidor | **Corregida la tangencia**: 53,968° y no 126, y la cinta abraza el arco OPUESTO al tambor | Se escribió mal dos veces: primero con el seno en vez del coseno, después poniendo el material en el lado libre. Lo cazó el plano al dibujarlo |
| 2026-10-01 | Bastidor | **Cinta de 10 a 5 mm de ancho**, y añadidas las cotas de contorno del sector y del tambor | Con 5 el sector es una plancha de POM en vez de dos laminadas: una operación de montaje menos por canal, a cambio de 0,046 mm de elasticidad |
| 2026-10-01 | Bastidor | **El sector pasa a disco entero y desaparecen las pestañas del tambor**; en su lugar, una tolerancia de coplanaridad | La muesca no daba holgura a nada y le ponía orientación a una pieza que no la necesita. Las pestañas no sujetan una cinta anclada por los dos extremos: lo que la sujeta es que los dos asientos sean coplanarios |
| 2026-10-01 | Bastidor | **Añadido el contorno de los brazos**: ancho, espesor, cubo, perno y cara plana del calaje | Sin contorno no hay plano que copiar. Las interfaces siguen saliendo de la cinemática; el contorno es una propuesta |
| 2026-10-01 | Bastidor | **El calaje pasa a vivir en la mordaza de la cinta**, no mecanizado en el eje | 1 mm de error en la longitud de la cinta son 21,6 mm en la punta, y un fleje anclado a mano no tiene esa longitud a la décima. Mecanizado el error sería invisible y permanente; ajustable es visible y se comprueba con la hoja de trazo patrón |
| 2026-10-01 | Bastidor | **Añadida la mordaza**: bloque, M3 de apriete, M4 de fijación y ranura de 6 de recorrido | Agarra por rozamiento y no por arrastre porque la cinta no se arrolla a menos de 5 mm de radio. El recorrido lo da el deslizamiento y la tensión el tirón: un tornillo tensor no hace las dos cosas, son 241 a 1 entre lo que hay que mover y lo que hay que sujetar |
| 2026-10-01 | Bastidor | **El eje de pivote se queda sin ángulo**: barra Ø10 h6 con una cara plana, igual en los tres | Consecuencia de lo anterior. No es una decisión, es lo que sobra |
| 2026-10-02 | **Accionamiento** | Añadido el grupo: volante Ø104 × 6 aligerado, manivela de 100 entre centros, 90 rpm y bahía del reductor de 20 | El volante no se había calculado nunca. Dimensionado contra «firma», que pide 3,62 × 10⁻⁴ kg·m² frente a los 2,28 de «hola»: sobre el demo se habría quedado un tercio corto |
| 2026-10-02 | Bastidor | **Añadido el séptimo agujero de la platina** y `poste_largo` de 70 a 105 | El eje de la manivela estaba en voladizo. Con un Ø19 más a 28 del árbol y 90° bajo +X, los TRES platos son la misma pieza y el tercero lo apoya |
| 2026-10-02 | Bastidor | `platina_radio` → **`platina_diametro`**, `platina_pivote_radio` → `platina_pivote_al_arbol` | El contorno es un círculo entero y la herramienta de círculo acota el diámetro. Renombradas ANTES de entregarlas, que es cuando sale gratis |
| 2026-10-02 | **Base** | Añadido el grupo: 190 × 275 × 25 de nogal, tres agujeros ciegos de Ø8 en triángulo equilátero y la tarjeta A7 | La planta la cierran el plato por detrás y el papel por delante, con 10 mm a cada punta. Los 210 × 160 de la ficha se quedaban 115 mm cortos de fondo |
| 2026-10-02 | Bastidor | **Añadido `poste_vano`** y `poste_largo` de 105 a **195**, derivado de la cadena entera | El poste baja hasta la base y hace de pata, así que no hace falta pilar y los tres platos siguen siendo la misma pieza. Y el «70 de antes» llevaba dentro, sin declarar, el vano entre el plato 1 y el plato 2 |
| 2026-10-02 | **Levantamiento** | Añadido el grupo: balancín 6,333/40, tirante a x = 65, mesa del papel sobre dos bielas de 40 y flexura de dos láminas | El canal 3 no tenía etapa de salida. Medir tumbó el 1:1 —41,4° de presión contra 30— así que la relación 6 se queda y la hace un balancín: una pieza en vez de cinco, y la leva no se toca |
| 2026-10-04 | Levantamiento | **Bieleta isógona de 60,24** (era 25), `balancin_chaveta_angulo` **90°** (nuevo), `balancin_eje_x` **25,028**, `balancin_eje_largo` **96,75** | El pasador del seguidor 3 no está en el eje de simetría: con la de 25, la mesa bajaba 2,45 en vez de 3. Las tres salen de `compile/levantamiento.py` y un test las cruza |
| 2026-10-04 | Bastidor | `eje_pivote_largo` de 45 a **55**; nuevos `brazo_arandela` 0,5, `punta_tubo_diametro` y `punta_tubo_interior_diametro` 13/10,6, `casquillo_rueda_diametro/largo` 15/4, `distal_punta_diametro` 19 y `eje_manivela_largo` 51 | 45 no llegaba del collar del proximal al tambor (hacen falta 51 y 54,5). Los brazos se solapaban con 1 de desnivel y 3 de espesor. El lápiz y el perno de la punta no caben en el mismo eje: la punta se hace hueca. El eje de la manivela no existía |
| 2026-10-02 | Levantamiento | Eje del balancín de **Ø4**, no Ø10 como los otros tres, y pasador de Ø2 | Con el brazo de entrada en 6,333, un Ø10 mete el pasador DENTRO del agujero del eje: pared −0,17. Con Ø4 y Ø2 quedan 3,33. Arrastra el cubo y la cara plana de la palanca del lápiz, que hay que redibujar |
