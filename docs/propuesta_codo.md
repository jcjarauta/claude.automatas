# Propuesta · el codo del cinco barras y las uniones que faltan

2026-10-05 · estado: **aprobada; pasos 1 y 2 hechos** (orden A, eje de 69,5, perno del codo, arandela y casquillo de la punta). El paso 3, la tornillería dibujada, va con el bloque B del dossier.

## 1. El problema

El distal 1 y el proximal 2 chocan, y no es un error de dibujo: es el orden de
los planos. Los cuatro brazos van apilados bajo el plato 1, 3 mm de pletina y
0,5 de arandela, de arriba abajo:

| Plano | Brazo | z |
| --- | --- | --- |
| 1 | proximal 1 | 56,0 – 59,0 |
| 2 | proximal 2 | 52,5 – 55,5 |
| 3 | distal 1 | 49,0 – 52,0 |
| 4 | distal 2 | 45,5 – 48,5 |

El distal 1 se une al proximal 1 en el codo 1, así que **el perno de ese codo
baja del plano 1 al 3 y atraviesa el plano del proximal 2**. Como los
proximales se cruzan, el proximal 2 pasa por debajo del codo 1. En el montaje
no se veía porque **el perno del codo no está dibujado**: no existe como pieza,
aunque el contrato ya lleva su diámetro (`brazo_perno_diametro`, Ø6).

Medido en planta con un barrido de toda la caja de escritura (bordes y
diagonales), holgura entre cada elemento vertical y los brazos de los planos
que cruza:

| Elemento vertical | Contra | Orden actual | Orden propuesto |
| --- | --- | ---: | ---: |
| perno del codo 1 (con su casquillo, Ø12) | proximal 2 | **−6,0 mm (choca)** | no lo cruza |
| perno del codo 2 | distal 1 | 37,0 | no lo cruza |
| eje de pivote 2 (Ø10) | distal 1 / proximal 1 | — / 19,0 | 13,3 / 19,0 |
| collar bajo el proximal 1 | el brazo de debajo | 14,0 | 46,0 |
| collar bajo el proximal 2 | el brazo de debajo | 8,3 | 46,0 |
| tubo de la punta (Ø13) | los proximales | 71,8 | 71,8 |

## 2. Opciones

**A · Cada distal bajo su proximal** (recomendada). Orden proximal 1, distal 1,
proximal 2, distal 2. Cada codo une dos planos **contiguos** y ningún elemento
vertical atraviesa un brazo; la holgura mínima pasa de −6 a **13,3 mm**. Son los
mismos cuatro planos y la misma altura total: no cambia la cinemática, ni los
calajes (congelados), ni el plato. Cambia:

- el eje de pivote 2 baja con su proximal 3,5 mm: o dos largos de eje, o el
  mismo eje para los dos, de 69,5 en vez de 66;
- entre los dos distales, en la punta, queda un plano vacío: el tubo de la
  punta lleva un casquillo separador de 4 mm entre ellos.

**B · Mantener el orden y librar el codo con un puente**: el distal 1 sube con
un codillo hasta el plano 1. Es una pieza doblada, más cara y menos rígida, y no
arregla nada que A no arregle.

**C · Que los proximales no se crucen.** Cambia la rama del cinco barras, los
calajes y la caja: toca un contrato congelado. Descartada.

## 3. El codo con el orden A

El codo 1 queda entre el plano 1, que tiene encima el plato a 1 mm
(`HOLGURA_AXIAL`), y el plano 2, que en algunas posturas tiene debajo el
proximal 2. **No puede asomar nada por ninguna de las dos caras.** Así que el
perno va **enrasado**:

- pasador Ø6 m6 **calado a presión en el cubo del distal** y deslizante H7 en el
  del proximal; largo 3 + 0,5 + 3 = 6,5, enrasado en las dos caras;
- arandela de latón de 0,5 entre los dos cubos, que es la `brazo_arandela` que
  hoy es solo un hueco;
- sin anillo de retención. Lo que fija la altura del distal es el otro extremo,
  el tubo de la punta con su retención; la del proximal la fija su collar en el
  eje de pivote. El codo solo tiene que transmitir el giro.

El codo 2 es la misma pieza; debajo del distal 2 no hay nada, pero se repite el
mismo pasador para que sea una sola referencia.

## 4. Las uniones que faltan para terminar el dibujo

Inventario: lo que se compra o se fabrica (`emit.plataforma.LISTADO`,
`emit.materiales.tornilleria`) frente a lo que coloca `emit.montaje.colocar`.

**Faltan en todas partes** (ni pieza, ni compra, ni 3D):

| Unión | Qué hace falta |
| --- | --- |
| Codo 1 y codo 2 | pasador Ø6 × 6,5 enrasado, ×2 (`perno_codo`); arandela de latón Ø12/6 × 0,5, ×2 |
| Punta | casquillo separador Ø19/13 × 4 entre los dos distales (con el orden A); arandela de 0,5 |

**Se compran pero no se dibujan** (están en la tornillería, no en el 3D):

| Unión | Elemento |
| --- | --- |
| Ejes de pivote | anillo de ajuste DIN 705 Ø10 bajo cada proximal; DIN 6799 Ø10 sobre cada tambor |
| Tubo de la punta | su retención bajo el distal de abajo |
| Eje del balancín | DIN 6799 Ø4, ×2 |
| Bulón del tirante | DIN 6799 Ø6 |
| Ejes de la mesa | DIN 6799 Ø1,5, ×8 |
| Apoyos del balancín | DIN 912 M3 × 16, ×2 |
| Postes | DIN 7991 M3 × 10 en la punta de cada poste, ×3 |
| Collares, casquillo de la rueda, pinza | prisioneros DIN 913 M3, ×11 |
| Láminas de flexura, mesa, soportes | DIN 912 M2, ×10 |
| Bieleta | arandela de presión Ø2 |
| Sectores y ejes de rodillo | tuercas DIN 439 M3 |

Las del primer grupo cambian la máquina; las del segundo solo completan el
dibujo y el despiece (y el dossier, que las necesita para la secuencia de
montaje). Se propone una pieza de catálogo por designación
(`core/comercial.py`, `PiezaComercial`), dibujada a su medida de norma y
colocada por `colocar`, con
un test que exija que todo lo de la tornillería aparece en el 3D.

## 5. Plan si se aprueba

1. Orden A en `emit.montaje.alturas`; eje de pivote de 69,5; contrato de
   bastidor (pendiente): `eje_pivote_largo`, `perno_codo_largo`,
   `casquillo_punta_largo`. Test: la holgura de §1 en planta, ≥ 3 mm en toda
   la caja.
2. Piezas nuevas: `perno_codo`, `arandela_brazo`, `casquillo_punta`, con ficha.
3. Tornillería dibujada (§4, segundo grupo) y el test de que no falta ninguna.
4. Dossier y animación al día.

No toca contratos congelados.
