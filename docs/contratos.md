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
| Pasador de índice | Ø3 mm, a **18 mm** del centro, sobre +X |
| Marca grabada | Una línea del pasador al borde, rotulada `FASE 0`. Apunta al pasador |
| Alcance | **Las tres levas y los separadores llevan el pasador en el mismo sitio** |

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
| Índice | Un pasador Ø3 transversal, a 18 mm del centro (ver contrato de fase) |
| Pila del cartucho | 3 levas de 5 mm + 2 separadores de 2 mm = **19 mm** |
| Altura máxima de pila | 80 mm |

Ø10 porque es la medida de varilla calibrada más corriente y porque tiene
rodamiento barato en cualquier catálogo. La pila de 19 mm sale de la
geometría y la comprueba `tests/compile/test_conjunto.py::test_la_pila_son_tres_levas_y_dos_separadores`.

**Lo que no se congela todavía:** el rodamiento concreto y el sistema de
retención axial. Dependen de la investigación de proveedores y de medir el
juego en el banco (E4), y ninguna de las dos cosas está hecha.

---

## Contrato de bastidor · PENDIENTE

Hay números que la geometría ya fija y que **no** se congelan hasta que el
banco diga que el modelo predice:

- Postes de seguidor: tres, a **71,1 mm** del árbol, repartidos a 120°.
  Sale de `hypot(radio_base, brazo_seguidor)` = `hypot(55, 45)`.
- Hueco entre la leva mayor y el poste vecino: **9,0 mm** con la caja de
  escritura por defecto. Encoge cuando la frase crece, y es el límite de
  conjunto que decide qué frases caben.
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
