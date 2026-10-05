# Propuesta · lo que encontró la tornillería al dibujarse

2026-10-05 · estado: **pendiente de decisión** (fase 6 de `propuesta_dossier.md`)

La fase 6 dibuja en 3D toda la tornillería que se compra: las 26 líneas de
`emit.materiales.tornilleria()`, 72 piezas, cada una en su sitio y con su
agujero en la pieza que la recibe. Cada línea declara qué pieza la dibuja
(`Fijacion.en_3d`) y un test exige que lo comprado y lo dibujado coincidan.

Dibujarla la ha medido. **Dos cosas se han arreglado sin preguntar**, porque
son largos de tornillo y no tocan ningún contrato:

| Antes | Ahora | Por qué |
| --- | --- | --- |
| DIN 912 M2 × 30, soportes de la mesa | **M2 × 25** (T-ELV-08) | Con la cabeza embutida bajo la base de 25, el de 30 llegaba al eje fijo, a 6 de la base. El de 25 rosca 2 en el soporte |
| DIN 912 M2 × 5, pestañas de las láminas | **M2 × 4** (T-POR-03) | En la pinza, el de 5 llegaba al portaminas. El de 4 deja 0,1 hasta su agujero |

Los números viejos (T-ELV-03, T-POR-02) quedan dados de baja, como dice la
numeración: no se reutilizan.

Y **uno era de los tests**: el barrido de choques solo mira pares con una
pieza móvil, y nada miraba dos piezas quietas. El M2 × 30 atravesaba el eje
fijo de la mesa sin que fallara nada. Ahora lo mira
`test_las_piezas_quietas_no_se_atraviesan`. Tampoco había nada que viera un
circlip dibujado más allá del final de su eje: lo mira
`test_cada_circlip_y_cada_arandela_esta_sobre_su_eje`.

**Lo que queda pide una decisión**, porque cambia una pieza, el contrato del
levantamiento o lo que se compra de otra forma. Cada choque está apuntado en
`tests/emit/test_montaje.py` (`PENDIENTES_DE_DECISION`, `SIN_EJE_PENDIENTES`)
con su sección de aquí: no se toleran en silencio, y en cuanto uno se
arregle el test obliga a quitarlo de la lista.

---

## 1. El circlip bajo el muñón no cabe

DIN 6799 para eje Ø10: 1,0 de espesor. Va bajo el plato 1 (cara baja a
z = 60), y por debajo pasa el proximal 1 (cara alta a z = 59): el hueco es
de 1,0 justo. Choca 0,22 con el proximal cuando el brazo pasa bajo el árbol.

**Propuesta:** un alojamiento de Ø17 × 1,2 en la cara baja del plato 1,
centrado en el árbol, donde el circlip queda embutido. Es una operación de
mecanizado sobre la platina (el perfil 2D no cambia; va en su ficha).

## 2. El M2 de cada orejeta atraviesa el eje móvil de la mesa

La orejeta tiene el eje móvil (Ø1,5) a 2,5 de su cara alta, que es la que
se atornilla a la mesa. Un M2 que baja desde la mesa solo puede roscar
2,5 − 0,75 = **1,75 mm** antes de llegar al agujero del eje, en cualquier
punto de los 40 de la orejeta, porque el eje la recorre entera. El M2 × 8
de la lista lo atraviesa (−1,48).

- **a)** M2 × 5: rosca 1 mm. Cabe, pero no aprieta.
- **b) Recomendada:** bajar el eje en la orejeta, de 2,5 a 4,5 de su cara
  alta (`mesa_biela_extremo_diametro_radio` deja de ser la cota de la
  orejeta; `orejeta_mesa_alto` 4,5 → 6,5). El M2 × 8 rosca 3,75. La mesa
  queda 2 mm más alta respecto de sus ejes: hay que rehacer su altura
  (`mesa_altura`) y volver a pasar el barrido.
  Toca el **contrato del levantamiento** (pendiente, no congelado).

## 3. El prisionero del collar del seguidor se mete en el muelle

El collar del seguidor mide Ø11,5 × 7 y lleva alrededor el muelle de
torsión, que ocupa sus 5 mm de arriba. Un M3 radial con 1,75 de pared
asoma 2,25 y entra en las espiras (−1,47). Por debajo del muelle quedan
2,0 de collar: un M3 no cabe.

- **a) Recomendada:** en los tres collares del seguidor, prisionero
  **DIN 913 M2 × 3** en esos 2 mm de abajo. Una línea nueva de tornillería;
  los otros seis collares siguen con su M3.
- **b)** collar del seguidor de 9 en vez de 7 (`collar_seguidor_largo`):
  deja sitio al M3, pero sube la placa de tope y el seguidor 2 mm, y el
  collar es una pieza para los nueve.

## 4. Los ejes de la mesa acaban enrasados: los 8 circlips no tienen dónde ir

- Eje fijo: `mesa_eje_fijo_largo` = 7 = biela 3 + soporte 4. Acaba en la
  cara de fuera del soporte.
- Eje móvil: `mesa_eje_movil_largo` = 142 = de la cara de fuera de una biela
  a la de la otra.

El DIN 6799 de Ø1,5 mide 0,3 y su ranura va a ~0,5 del extremo.

**Propuesta:** fijo 7 → **8**, móvil 142 → **144**. Son barras de Ø1,5
cortadas a medida; no cambia ninguna pieza más. Contrato del levantamiento.

## 5. La pata de la bieleta acaba enrasada en el balancín

`bieleta_pata_balancin` = 4 = 1 de holgura + 3 del balancín: la arandela de
presión que la retiene no tiene dónde ir.

**Propuesta:** pata 4 → **5**; la bieleta se desarrolla 1 mm más larga
(`bieleta_largo_desarrollado`). Contrato del levantamiento.

## 6. El anillo DIN 705 de Ø10 no es de 3

Bajo cada proximal el eje de pivote deja un hueco de 3
(`test_el_eje_de_pivote_llega_del_collar_al_circlip`), y la lista compra un
DIN 705 Ø10, que mide **Ø20 × 10**. Está dibujado Ø20 × 2,95, que es lo que
cabe, no lo que se compra.

**Propuesta:** sustituirlo por un collar fabricado, como `collar`: barra de
Ø16, 3 de largo, agujero de Ø10 y prisionero M3 radial (con 3 de pared,
cabe enrasado). Sale de la tornillería y entra en el listado como pieza del
cinco barras (marca P-CBR-05). La otra vía, alargar el eje de pivote 7 mm
para que quepa el DIN 705, toca el contrato del bastidor y no está medida.

---

## Qué hace falta para cerrar

Una respuesta por sección: cuál de las opciones, o otra. Con eso se
cambian contrato, piezas y tornillería, se quitan las entradas de
`PENDIENTES_DE_DECISION` / `SIN_EJE_PENDIENTES`, y los tests lo comprueban.
