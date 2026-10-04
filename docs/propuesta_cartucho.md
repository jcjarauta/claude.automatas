# Propuesta: cartucho intercambiable y fabricación

Estado: **APROBADA** (2026-10-04): garra con muelle, cartucho con su eje y su
cubo, y cambio de los contratos de fase y eje. **Fase 1 hecha**, ver §0. No toca código ni contratos
hasta que se apruebe. Lo que cambia un contrato congelado está marcado
**[CONTRATO]**.

## 0. Resultado de la fase 1 (viabilidad)

**Encontró un fallo de la máquina que no era del cartucho.** Al meter en el
montaje 3D los rodillos con sus ejes —no estaban—, el eje del rodillo de la
leva de abajo atravesaba las dos levas de encima entre 1,4 y 2,0 mm en los
tres casos de referencia, y el del medio rozaba la de arriba. El barrido no
lo veía porque los rodillos no estaban en él.

Arreglo, sin tocar ningún contrato congelado ni mover los postes:

- **Pila escalonada**: de abajo arriba, elevador R 55 (no cambia, ni su
  cadena de levantamiento), derecho R 48,4 e izquierdo R 39,6 de radio base.
  Cada eje queda a ≥ 5 mm de las levas de encima (mínimo exigido 2), y el
  ángulo de presión máximo sube de 8,3° a 11,4°.
- **Un solo seguidor con tres agujeros de rodillo, a 45, 52 y 59**: con el
  poste fijo, el brazo largo da la leva pequeña. 52 es el mínimo para que la
  tuerca del eje quede fuera del sector.
- **El seguidor izquierdo, al revés**, para que ningún rodillo quede en el
  pasillo de salida.
- Nueva comprobación del compilador: `eje_de_rodillo_contra_leva`.
- El cartucho baja a **Ø104,6** (manda la del elevador); quedan 5,2 por lado
  entre los postes.

Y el cartucho **sale por detrás sin tocar nada** salvo el árbol, que es lo que
la fase 3 parte: test `test_el_cartucho_sale_por_detras_entre_los_dos_postes`,
holgura mínima 1,25 mm. Las levas se alejan de los rodillos al salir; la
palanca de servicio no tiene que apartar los seguidores 65°, solo
**sujetarlos** donde están para que los muelles no los metan en el hueco
(§3.3).

## 1. El problema

El modelo de negocio es plataforma a stock más cartucho por pedido, que «se
cambia en un minuto, a mano» (`ficha-producto.md`, `expediente.md`). La
máquina que tenemos montada no lo cumple:

- **El cartucho no puede salir.** Las levas van en el árbol de 92, que
  atraviesa los rodamientos del plato 1 y del plato 2 y lleva la rueda Z60
  con prisionero en la bahía. Para sacar las levas hay que sacar el árbol, y
  para eso hay que desmontar la rueda y el plato 2. Del plato 2 cuelgan el
  reductor, los apoyos y el eje del balancín. Cambiar una frase es desmontar
  media torre.
- **Las piezas que harían de cartucho no están definidas.**
  - El «plato de arrastre» es solo texto en cuatro documentos. No tiene
    medidas, material ni fijación, y deja un hueco de 2 en el montaje frente
    a los 5 de pasador que el contrato le reserva.
  - La retención axial de la pila sigue abierta (`contratos.md` §eje).
  - El separador del catálogo es Ø3,2 × Ø6, así que solo entra en el
    pasador y no en el eje.
  - Las fuentes no se ponen de acuerdo sobre el pasador: el contrato dice
    uno de Ø3 × 24 y los precios cuentan tres de Ø3 × 16.
- **Nada impide montarlo desfasado.** La fase la da el pasador entre las
  levas, pero entre el árbol y las levas no hay referencia, así que el
  cartucho puede entrar girado. La hoja patrón lo detecta después, pero no
  lo impide.

## 2. Lo que la geometría permite (medido en el montaje actual)

| Dato | Valor |
| --- | --- |
| Radio máximo de leva, cuatro pedidos de referencia | **R54,17** (el caso «apretada») |
| Altura de las levas | z 71–90. Plato 1 arriba en 69, seguidores en 92–97, plato 2 en 127 |
| Postes | Tres a 120° sobre R71,06. Los dos de atrás están 35,5 detrás del árbol, a ±61,5 |
| Hueco libre entre los dos postes de atrás, a la altura de las levas | 123,1 − Ø8 = **115,1** |
| Lo que sobra a cada lado de un cartucho de Ø108,4 | **3,36**. `holgura_minima` es 2 |
| Detrás del árbol | 95 de base. El levantamiento (balancín, apoyos) está delante, en y +4…+39 |

**Conclusión:** el cartucho cabe por detrás, entre los dos postes traseros,
como un cajón, **sin mover los postes**. Eso importa porque mover un poste
obliga a rehacer `brazo_origen`, resintetizar las levas y reabrir el
contrato de bastidor. Aquí no hace falta nada de eso. El calaje (de los
brazos) tampoco cambia.

## 3. Arquitectura propuesta: cartucho «entre puntos»

El árbol de 92 se parte en tres. El cartucho queda entre un muñón fijo abajo
y una garra motriz arriba, como una pieza entre puntos en un torno.

```
plato 2 ──┬── rodamiento 6800 ── EJE MOTRIZ (rueda Z60 en la bahía, como hoy)
          │                        │
          │                  GARRA deslizante + muelle   ← se sube con dos dedos
          │   ┌───────────────────┴──────────┐
          │   │ CARTUCHO: eje Ø10 corto       │  ← sale hacia atrás (−Y)
          │   │ cubo de latón + pasador Ø3    │    entre los postes traseros
          │   │ 3 levas POM + 2 separadores   │
          │   └───────────────────┬──────────┘
plato 1 ──┴── rodamiento 6800 ── MUÑÓN inferior con horquilla en U
```

### 3.1 Piezas del cartucho (por pedido)

| Pieza | Qué es | Fabricación |
| --- | --- | --- |
| L-001…003 | Levas, como hoy | POM-C 5, fresado o láser. **Taladro Ø10 H8 de verdad**: hoy se cortan a nominal |
| Eje del cartucho | Ø10 h6 × ≈ 27. Abajo un tetón Ø5; arriba la ranura de la garra, **asimétrica** | Torno, de la misma barra que el resto de ejes Ø10. Va a stock aunque viaje con el cartucho |
| Cubo (sustituye al «plato de arrastre») | Latón Ø24 × 4, a presión o con prisionero en el eje. Lleva el pasador m6 a 18 sobre +X | Torno + taladro con plantilla. A stock |
| Pasador índice | **Uno**, Ø3 × 24 (DIN 6325), m6 en el cubo y deslizante en las levas | Comercial |
| Separadores | Arandelas de latón Ø10,2 × Ø20 × 2 con agujero Ø3,1 a 18: van en el eje Y en el pasador | Láser en chapa de 2, junto con el resto del latón |
| Retención | La da la garra con su muelle: aprieta la pila contra el muñón. **Cierra el hueco abierto de la retención axial** | — |

Lo único que cambia de verdad con cada pedido son las tres levas. El eje, el
cubo, el pasador y los separadores son iguales en todos los cartuchos, se
compran o se fabrican en lote y se montan con una plantilla de fase.

### 3.2 La garra es la llave de fase

- La garra y la ranura del eje son asimétricas: una lengüeta descentrada, o
  dos de anchos distintos. **Solo encajan con el cartucho en θ = 0**. Montarlo
  desfasado deja de ser posible.
- El muñón de abajo lleva una horquilla en U que gira con él. Solo mira
  hacia atrás en θ = 0, así que el cartucho solo entra y sale en fase cero.
  La manivela tiene que estar en su marca para cambiarlo, y eso refuerza lo
  anterior.
- La garra pasa el par (48 mN·m; 2,7 N a 18 mm, de sobra). El pasador queda
  para lo que dice el contrato: poner las tres levas en fase entre sí.

**[CONTRATO] fase.** El pasador, su sitio y el Ø10 de las levas no cambian.
Cambia la pieza que el contrato llama «plato de arrastre metálico»: pasa a
ser el cubo del cartucho, y `leva_sobre_plato` y `pasador_longitud` se
recalculan con él. Lo digo porque el contrato está congelado.

**[CONTRATO] eje.** El «árbol» deja de ser una sola pieza. Se mantienen el
Ø10 y los rodamientos 6800. De paso se corrige h7/h6: el contrato dice h7 y
la pieza dice h6.

### 3.3 Retirar los seguidores (corregido por la fase 1: basta sujetarlos)

Los rodillos cuelgan dentro de la pila, por fuera de las levas, y los muelles
los aprietan contra ellas. Para sacar el cartucho se propone una **palanca de
servicio**:

- Una leva excéntrica en el plato 1 empuja los tres seguidores hacia fuera a
  la vez, contra sus muelles, y los deja trabados.
- Así se aprovecha que los tres están en un solo plano.
- Al volver la palanca a su sitio, los rodillos bajan sobre las levas en
  fase cero, que es una posición conocida.

Esto hay que comprobarlo con geometría antes de dar nada por hecho: cuánto
gira cada seguidor hasta que su rodillo sale del pasillo de Ø108,4 + 2 × 2
hacia −Y. Es la primera prueba de la fase 1 (§6).

### 3.4 El procedimiento (lo que irá en el dossier)

1. Girar la manivela hasta la marca FASE 0.
2. Bajar la palanca de servicio: los seguidores se retiran.
3. Subir la garra con dos dedos y sacar el cartucho hacia atrás.
4. Meter el nuevo, que solo entra en fase cero, y soltar la garra.
5. Subir la palanca y trazar la hoja patrón.

Sin herramientas, en menos de un minuto.

## 4. Separar plataforma y cartucho en el proyecto

| | Plataforma (a stock) | Cartucho (por pedido) |
| --- | --- | --- |
| Código | `emit/plataforma.py` `LISTADO` | Nuevo `emit/cartucho.py`: levas del compilador, eje, cubo, separadores |
| Contrato | eje, bastidor, calaje | fase y **envolvente**: `leva_radio_maximo` = 54,5, que el compilador tiene que respetar o rechazar la frase |
| Montaje | `taller()` y `colocar()` de la plataforma | Un subconjunto que se coloca por la interfaz: garra + muñón + θ = 0 |
| Precios | `precios.json` «plataforma» | «cartucho»: levas + corte. El resto de metal va a la plataforma como «portalevas» |
| Pruebas | barrido de la máquina entera | barrido del **camino de extracción** y la prueba «solo encaja en fase cero» |

La interfaz plataforma ↔ cartucho queda en **un solo sitio**, como
contrato nuevo «cartucho»:

- cotas de la garra y la ranura;
- tetón y horquilla;
- altura entre puntos;
- radio máximo;
- pasillo reservado entre los postes traseros, donde no se puede poner nada
  (muelles, tornillos, cinta).

## 5. Piezas que hay que reformular (desactualizadas o sin definir)

| # | Pieza | Estado hoy | Qué se hace |
| --- | --- | --- | --- |
| 1 | Árbol de levas 92 | Una pieza que bloquea el cambio | Se parte en eje motriz, eje del cartucho y muñón |
| 2 | Plato de arrastre | Solo texto | Pasa a ser el cubo del cartucho |
| 3 | Separador de pila | Ø3,2 × Ø6, no entra en el eje | Arandela Ø10,2 × Ø20 × 2 con agujero de pasador |
| 4 | Pasador índice | 1 × 24 en el contrato, 3 × 16 en precios | Uno de Ø3 × 24, y se corrigen `precios.json` y `ficha-producto` |
| 5 | Retención axial | Abierta | La da el muelle de la garra |
| 6 | Anclaje del muelle del seguidor y varilla guía | «PENDIENTE» | Pivote fijo en el plato 1, fuera del pasillo trasero |
| 7 | Eje del rodillo (M3) y casquillos de descuelgue 21/14/7 | Sin largos ni separadores | Tornillo DIN 912 M3 a medida + casquillo de latón del lote de torno |
| 8 | Altura de los platos sobre los postes | Sin definir cómo se sujetan | Tubos espaciadores Ø8,2 × Ø12 cortados a largo. Fijan las alturas sin medir en el montaje |
| 9 | Taladros de leva | A nominal, sin el H8 del contrato | Compensación en el DXF de corte |
| 10 | Costes | `expediente.md` dice 81,09 / 119,17 (viejos); `precios.json` dice árbol de 120 | Regenerar desde `compile/coste.py` |
| 11 | Dossier de fase cero | No existe | Procedimiento del §3.4 con la verificación por hoja patrón |
| 12 | Palanca de servicio | Nueva | Latón de 3, láser, pivote en un poste |

## 6. Optimización de la fabricación

- **Una plancha por material y espesor.** Todo el latón de 3 anidado en una
  sola chapa de láser:
  - brazos y sector;
  - mordazas;
  - balancín, mesa y bielas;
  - palanca de servicio y separadores.
  
  Antes se revisan las piezas de 4 y 6 para pasarlas a 3 o a 2 × 3 donde se
  pueda. Cada espesor de menos es un pedido de chapa y una preparación de
  máquina de menos.
- **Un solo lote de torno:**
  - de una barra Ø10 h6: eje motriz, eje del cartucho, muñón y eje de la
    manivela;
  - de un tubo de latón: espaciadores de poste, casquillos de rodillo,
    casquillo de rueda y tubo de punta.
  
  Hay que unificar los diámetros exteriores a dos o tres medidas.
- **Platos a láser** en contrachapado de 9, con los alojamientos de los
  rodamientos y las marcas de montaje grabadas en la misma pasada.
- **Tornillería reducida a M2 y M3** en largos estándar. Una sola caja de
  referencias.
- **El cartucho por pedido queda mínimo:** tres levas de POM de una plancha
  y un montaje con plantilla de fase. Así el plazo del pedido depende solo
  del corte de las levas.
  - El metal del cartucho (unos 3–5 € entre eje, cubo, pasador y
    separadores) va a stock.
  - El coste por pedido sigue en torno a 38 €, casi todo corte.
- **Salidas automáticas:** `emit` genera un DXF anidado por material, la
  hoja de torno y la lista de compra. Así cada pedido produce lo mismo sin
  trabajo a mano.

## 7. Plan por fases (cada una con lint, tipos, pruebas, commit y push)

1. **Viabilidad, solo geometría.**
   - Cálculo de cuánto tiene que girar cada seguidor para dejar libre el
     pasillo.
   - Barrido del cartucho saliendo hacia −Y en el montaje actual.
   - Si no sale, se replantea antes de tocar contratos.
2. **Contratos.**
   - Contrato «cartucho» (interfaz y envolvente).
   - Ajustes de fase y eje marcados arriba.
   - Corrección de las incoherencias del §5 (4, 9, 10).
3. **Piezas y montaje del cartucho.**
   - Eje motriz, garra, muñón, cubo, separadores y `emit/cartucho.py`.
   - Prueba de que la máquina entera no choca en todo el ciclo.
   - Prueba nueva de que solo encaja en fase cero.
4. **Seguidores.**
   - Palanca de servicio, anclajes de muelle, ejes y casquillos de rodillo.
   - Barrido del camino de extracción con los seguidores retirados.
5. **Fabricación.**
   - Unificación de espesores y diámetros, espaciadores de poste, DXF
     anidados, hoja de torno y precios.
   - Dossier de cambio de cartucho y fase cero.

## 8. Decisiones que necesito

- **Garra con muelle** (propuesta) frente a una tapa atornillada. La tapa es
  más simple, pero necesita destornillador y no da la fase por forma.
- Si el cartucho que se vende incluye el eje y el cubo (cambio en un minuto
  por el cliente, unos 4 € más) o solo las levas, montadas en taller sobre
  un portalevas. Recomiendo lo primero, porque es lo que promete la ficha.
- Si se acepta tocar los contratos congelados de fase y eje como se describe
  en el §3.2.
