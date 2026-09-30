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

No se congelan porque el radio base puede moverse cuando E4 mida el juego
real: la relación del varillaje, el radio base y el diámetro de la leva son
un solo compromiso, y todavía falta el dato que lo cierra.

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
