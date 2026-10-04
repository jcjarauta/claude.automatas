# Levas, cartucho y máquina

El escribiente se fabrica y se monta en tres niveles. Cada uno lo hace alguien
distinto, con otra frecuencia, y por eso las mejoras se buscan nivel a nivel:

- **Levas.** Las tres levas de POM que genera el compilador: la frase del
  cliente. Lo único que no puede tenerse a stock.
- **Cartucho.** Las levas más el metal que las enhebra: eje del cartucho,
  cubo, separadores y pasador. El metal es igual en todos los pedidos y va a
  stock; el cartucho se monta para cada pedido.
- **Máquina.** La plataforma, todo lo demás. A stock, igual en todas.

En el código son `emit.montaje.NIVELES`, y en el visor
`scripts/ver.py --conjunto --nivel levas|cartucho|maquina`.

## Lo que tiene cada nivel

Cada fila cuenta solo lo propio de su nivel: el cartucho lleva además las
levas, y la máquina no lleva ninguna de las dos.

<!-- niveles:inicio · generado por scripts/niveles.py, no editar a mano -->

| Nivel | Quién y cuándo | Piezas fabricadas | Unidades | Materiales | Procesos | Comerciales (ud.) | Fijaciones | Ajustes a mano |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| **levas** | por pedido, fuera: fresado en un solo amarre | 3 | 3 | 1 | 1 | 0 (0) | 0 | ninguno |
| **cartucho** | metal a stock; se monta por pedido con las levas | 2 | 3 | 2 | 2 | 1 (1) | 0 | ninguno |
| **maquina** | a stock, igual en todos los pedidos | 40 | 81 | 22 | 28 | 14 (99) | 70 | orientar 3 collares de seguidor con la galga de 1,20; calar 2 brazos con la mordaza de la cinta; apretar 6 collares de plato a su altura |

<!-- niveles:fin -->

## Levas: la precisión es la palanca

**Datos** (pedido de ejemplo «hola»):
- Tres piezas de POM-C de 5, fresadas en un solo amarre: 394 s de máquina.
  De una plancha salen 81 levas, o sea 27 cartuchos.
- Cuestan 37,70 € de los 39,04 del cartucho. 35 € son el corte, una
  previsión sin cerrar; por tarifa saldría a 19,76.
- El **error de perfil** (±0,05) se amplifica ×17 y ×20 en los dos brazos, y
  se lleva **1,88 mm de los 2,62 mm** del peor caso en la punta: el 72 %
  (`compile.tolerancias`). Ninguna otra pieza de la máquina pesa tanto en
  lo que se ve escrito.

| # | Mejora | Por qué | Esfuerzo |
| --- | --- | --- | --- |
| L1 | **Pedir el perfil a ±0,02** al taller, o cortar las levas en casa | **Hecho en el plano** (2026-10-04): el rótulo de cada leva lo pide y `Holguras.error_de_perfil` lo usa. Peor caso en la punta de 2,47 a **1,35 mm**, cuadrático de 1,37 a 0,62. La siguiente palanca es la cinta (0,18 mm). El muestreo del modelo son 3 µm: los 0,14 mm que se daban eran de medir mal (ver `compile.escribiente.UMBRAL_DE_APOYO`). Falta que un taller lo acepte por ese precio | Medio: presupuesto |
| L2 | **Que el plano diga H8 en los dos taladros** | **Hecho** (2026-10-04): `Taladro.tolerancia`, rotulado en el DXF de taller y en la plantilla 1:1 | — |
| L3 | **Cerrar el precio del corte por bloque** | 35 € es una previsión y es el 90 % del cartucho. El caso malo es cortar las tres levas en tres amarres: eso es lo que hay que pactar | Bajo: negociación |
| L4 | **Grabar en cada leva el pedido y su número** | **Hecho** (2026-10-04): «hola 001» en la capa GRABADO del DXF de taller, al otro lado del pasador. No va a los DXF del CAD, que no admiten texto | — |

## Cartucho: la fase no debería montarse

**Datos:** 3 piezas fabricadas (4 unidades), 3 materiales y 3 procesos, más
el pasador. Tres uniones: el cubo a presión en el eje, el pasador m6 en el
cubo, y levas y separadores enhebrados en los dos. **Un ajuste**: al prensar
el cubo hay que dejar el pasador a 60° de la ranura del eje.

| # | Mejora | Por qué | Esfuerzo |
| --- | --- | --- | --- |
| C1 | **Eje y cubo en una sola pieza** | **Hecho** (2026-10-04): el eje lleva su valona, torneado de Ø25, y la ranura y el pasador se mecanizan en el mismo amarre. Fuera la prensa, una pieza y el único ajuste del cartucho | — |
| C2 | ~~Plantilla de montaje del cartucho~~ | Ya no hace falta: con C1 no hay nada que orientar al montar | — |
| C3 | Separadores cortados en la chapa de 2 junto a la placa de tope | Ya es así; anotado para que el anidado de la chapa los cuente por pedido | — |

## Máquina: menos piezas sueltas que ajustar

**Datos:** 39 piezas fabricadas (84 unidades), 21 materiales, 28 procesos, 14
comerciales (108 unidades) y 79 fijaciones. **20 ajustes a mano**: 3
collares con galga, 2 calajes con mordaza y 15 collares de plato apretados a
su altura.

| # | Mejora | Por qué | Esfuerzo |
| --- | --- | --- | --- |
| M1 | **Tubos separadores donde no gira nada** | **Hecho** (2026-10-04): tubo de latón 12 × 1,5 de la base al plato 1 (60) y del plato 2 al 3 (20). El M3 de la punta aprieta plato 3, tubo y plato 2 contra su collar. Collares de plato de 15 a 6, prisioneros de 23 a 14, ajustes de la máquina de 20 a 11. Un material más (el tubo de 12) a cambio de nueve piezas torneadas menos | — |
| M2 | **Tres espesores de chapa de latón en vez de cuatro** | Solo el soporte de la mesa y el poste de la horquilla van en 4. Pasarlos a 3 o a 6 quita una chapa del pedido | Medio: recalcular las dos piezas |
| M3 | **Unificar largos de tornillería** | 79 fijaciones en 21 referencias. Varios M2 (×4, ×5, ×8) pueden ser un solo largo | Bajo |
| M4 | Con M1, los prisioneros bajan de 23 a 14 | **Hecho** con M1 | — |

## Prioridades

| | Mejora | Qué gana |
| --- | --- | --- |
| 1 | **L2**, la tolerancia de los taladros en el plano | Que el taller corte lo que pide el contrato. Barata y sin riesgo |
| 2 | **C1**, eje y cubo en una pieza | Quita el único ajuste del cartucho, que es justo el que puede desfasar la escritura |
| 3 | **L1**, perfil a ±0,02 | La mayor mejora de calidad del escribiente: de 2,6 a 1,5 mm en la punta |
| 4 | **M1**, tubos separadores | De 20 ajustes a mano a 11 en la máquina |
| 5 | L4, M2, M3 | Trazabilidad y orden de compra |
