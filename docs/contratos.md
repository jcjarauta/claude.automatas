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
| Ajuste | **Deslizante en las tres levas** (POM, H8). Apretado solo en el plato de arrastre metálico |

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
El pasador va deslizante en las tres levas y apretado en un solo sitio, el plato
de arrastre metálico que lo lleva. El argumento del contrato no cambia —sigue
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

---

## Contrato de eje · CONGELADO 2026-09-29

| | |
| --- | --- |
| Diámetro | **Ø10 mm**, tolerancia h7 |
| Sentido de giro | Horario visto desde arriba, θ creciente |
| Índice | Un pasador Ø3 × 24 transversal, a 18 mm del centro (ver contrato de fase) |
| Pila del cartucho | 3 levas de 5 mm + 2 separadores de 2 mm = **19 mm** |
| Altura máxima de pila | 80 mm |

Ø10 porque es la medida de varilla calibrada más corriente y porque tiene
rodamiento barato en cualquier catálogo. La pila de 19 mm sale de la
geometría y la comprueba `tests/compile/test_conjunto.py::test_la_pila_son_tres_levas_y_dos_separadores`.

**Lo que no se congela todavía:** el rodamiento concreto y el sistema de
retención axial. Dependen de la investigación de proveedores y de medir el
juego en el banco (E4), y ninguna de las dos cosas está hecha.

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
- Poste de seguidor de **Ø8** con casquillo igus GFM-0810. **Lo que la leva ve
  no es el poste: es la valona del casquillo**, que mide **Ø15** —confirmado
  en la ficha del fabricante, d3 = 15 mm—. Con los Ø16 que se suponían antes
  y un casquillo de bronce con valona de Ø28, el hueco caía a 3,0 mm y
  saltaba el aviso. El Ø16 nunca estuvo justificado: la fuerza tangencial en
  el seguidor es de 0,7 N.
- Hueco entre la leva mayor y ese obstáculo: **9,7 mm** con «hola». Encoge
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
