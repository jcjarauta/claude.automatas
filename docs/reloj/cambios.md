# Registro de cambios de los contratos del reloj

El equivalente de `docs/contratos.md` para el reloj: **por qué** cada número
se movió. Los números vivos están en `docs/reloj/contratos.json` y no se
copian aquí.

Una cota que cambia después de haberse dibujado obliga a redibujar, y eso
cuesta. Lo que hace que el coste merezca la pena es que se sepa por qué: si
el motivo no cabe en una línea, el cambio no estaba entendido.

---

## 1.1 · Varilla del péndulo

Tres revisiones, y **ninguna fue una corrección de un error de cálculo**: las
tres son la misma cota que deja de ser una estimación en cuanto la pieza de al
lado tiene ficha. `varilla_largo` es **derivada**, no elegida:

```
varilla_largo = longitud_pendulo_nominal
              - muelle_flexion_a_varilla      (lo que la suspensión se come arriba)
              - lenteja_centro_bajo_varilla   (lo que la lenteja se come abajo)
```

| Fecha | Valor | Qué lo movió | Qué se sabía que no se sabía antes |
| --- | --- | --- | --- |
| 2026-10-02 | 1080 mm | Primer trazo | Nada por abajo ni por arriba: el largo era la longitud del péndulo más holgura |
| 2026-10-02 | 990 mm | Ficha de la **lenteja** (1.2) | El centro de masas de la lenteja cae 44 mm bajo el extremo de la varilla, y el vástago M6 roscado ocupa ese tramo. Desaparece `varilla_sobrante` |
| 2026-10-02 | **935 mm** | Ficha del **muelle** (1.4) | El punto de flexión de un fleje plano está a **mitad del tramo libre**, no en el amarre: 15 mm y no los 40 que decía `varilla_sobre_flexion`, que era un marcador de posición |

**La cadena cierra en 994 exactos**, y lo exige
`tests/reloj/test_contratos_reloj.py`. Mientras falte una ficha aguas arriba o
aguas abajo, el largo seguirá siendo provisional: por eso la varilla no se
corta hasta cerrar la tanda 1 entera.

### Lo que no cambió, y conviene que se vea

| Cota | Valor | Por qué aguanta |
| --- | --- | --- |
| `varilla_ancho` | 15 mm | No entra en la cadena de longitud. Lo decide el rozamiento con el aire, y eso lo mide R1 |
| `varilla_espesor` | 8 mm | Igual: no participa en los 994 |
| `varilla_taladro_cerca` / `_lejos` | 15 / 35 mm | Ambos caen dentro del solape de 40 mm del fleje sobre la varilla, y hay un test que lo comprueba |
| `varilla_vastago_diametro` | 6,2 mm | Paso del M6 con holgura para la cola. Lo fija la pieza comercial |
| `varilla_vastago_profundidad` | 40 mm | Cinco diámetros de empotramiento. La unión trabaja a flexión |

**Qué hay que rehacer**: solo el largo. La pieza es un listón recto, así que
los dos taladros de arriba y el agujero de abajo no se mueven respecto de sus
extremos. En el CAD basta con que `#cota.varilla_largo` esté enlazada: si lo
está, el modelo se regenera solo al subir el CSV nuevo.

---

## 1.4 · Soporte de suspensión

Contrato `suspension` nuevo, 12 cotas. Tres decisiones que no se leen en el
dibujo y que son el motivo de que las cotas sean esas:

- **Los dos tornillos pasan a los lados del fleje, no por él.** De ahí
  `soporte_tornillo_separacion` = 24 con un fleje de 12. Taladrar un fleje de
  0,1 mm es dibujarle la línea por donde va a romper.
- **La placa de apriete existe porque dos tornillos aprietan en dos puntos.**
  Sin ella, el fleje flexa desde donde cada tornillo lo pellizca y el punto de
  flexión deja de estar donde dice el contrato.
- **El canto de abajo del bloque es el datum del péndulo entero.** Montarlo
  1 mm más arriba son 43 s/día. Va rotulado en el boceto, no solo aquí.

`muelle_flexion_a_varilla` está declarada como **aproximación**: el pivote
efectivo de un muelle de suspensión no es exactamente el centro del tramo
libre, depende de la carga. Lo mide R1 en el banco. Si sale distinto, se
corrige ahí y `varilla_largo` se recalcula sola — que es precisamente para lo
que se derivó en vez de elegirse.

### Tres cotas que faltaban, y por qué faltaban

Salieron de mirar el boceto, no de calcular: las tres son cosas que el dibujo
daba por supuestas y que con un lápiz no se pueden marcar.

| Cota | Valor | Qué se daba por supuesto |
| --- | --- | --- |
| `soporte_tornillo_al_lado` | **6 mm** (derivada) | Que los taladros van «centrados». Centrado es una restricción del CAD; en el banco se marca desde el canto, y hacía falta el número |
| `soporte_placa_ancho` | **36 mm** (derivada) | Que la placa mide lo mismo que el bloque. Se taladran juntos: si no coinciden, los taladros tampoco |
| `soporte_placa_alto` | **24 mm** | Que la placa «cubre». Si se queda por debajo de la línea de tornillos, el fleje flexa desde donde la placa acaba y el datum se mueve sin que nadie lo vea |

Las tres dejan margen holgado y hay un test por cada una: 3,9 mm de pared al
canto lateral, 3,9 mm del tornillo al borde del fleje y 11,9 mm de placa por
encima de los tornillos.

El boceto pasa a **tres vistas** —el bloque, la placa y el montaje— porque la
placa no se ve en la frontal del bloque, y era justo donde faltaban cotas. El
fleje desaparece de la vista frontal: quedaba detrás y lo único que hacía era
tapar el sitio donde van las cotas de los taladros.

---

## 1.3 · El fleje de suspensión

La única pieza de la tanda que no es de madera, y la última en tener boceto.
Dibujarla obligó a declarar tres cosas que estaban implícitas en una
descripción y por tanto no las vigilaba nadie.

| Cota | Valor | Qué estaba implícito |
| --- | --- | --- |
| `muelle_empotrado` | **20 mm** | «20 dentro del soporte», escrito en la descripción de `muelle_largo`. Una descripción no es una cota: no se puede cruzar con `soporte_placa_alto` |
| `muelle_solape` | **40 mm** | Igual. Y es la que tiene que cubrir los taladros de la varilla |
| `muelle_largo` | 90 mm, ahora **derivada** | Era un número suelto. Ahora es `empotrado + libre + solape`, con un test que lo exige |
| `muelle_taladro_cerca` / `_lejos` | **65 / 85 mm** (derivadas) | Los taladros existían en la varilla y no en el fleje, que es la pieza que se puede estropear |

### El fleje sí se taladra, y hacía falta decir dónde no

El contrato del soporte dice, y es verdad, que *taladrar un fleje de 0,1 es
crear la línea por donde va a romper*. Por eso los tornillos del bloque pasan
a los lados. Pero la varilla mide 15 de ancho y el fleje 12: ahí abajo los
tornillos **tienen** que pasar por el fleje.

No es una contradicción. Es una distinción que faltaba:

> **El fleje se rompe donde flexa, no donde tira.**

En el tramo libre, un agujero es una entalla en la zona de máxima tensión
alterna. En los 40 mm que solapan la varilla el fleje está muerto: aguanta
12 N sobre 1,2 mm², unos **10 MPa**, contra los 1.500 del acero de muelle.

La regla queda escrita en la hoja —«NO TALADRAR EN EL TRAMO LIBRE»— y
defendida por `test_el_fleje_se_taladra_solo_donde_no_flexa`, que comprueba que
los dos agujeros caen enteros, radio incluido, por debajo del tramo libre.

**Y una cosa que no es cota pero va en la lista de compra:** arandela ancha
bajo cada cabeza. Contra la varilla no hay placa que reparta, y una cabeza de
M4 apoyada en 0,1 mm de acero lo pellizca.

---

## 1.5 · El anclaje al bastidor

**No es una pieza. Es un contrato de interfaz, y por eso se puede cerrar hoy.**

El bastidor es el paso 6 y no existe. La tentación era dejar el soporte
PENDIENTE hasta entonces, y es el orden equivocado: el péndulo es la raíz de la
cadena causal y no puede esperar a la última pieza.

La salida es **invertir la dependencia**. El anclaje declara su patrón y lo
congela; el bastidor, cuando se dibuje, tendrá que respetarlo.

| Cota | Valor | De dónde sale |
| --- | --- | --- |
| `anclaje_tornillo_diametro` | 4,2 (derivada) | La misma broca que el muelle. Cuatro agujeros en el bloque y un solo cambio de herramienta: ninguno |
| `anclaje_tornillo_separacion` | 24 (derivada) | La misma que el muelle, así que los cuatro caen en dos líneas verticales y la plantilla de taladrado es una |
| `anclaje_tornillo_al_lado` | 6 (derivada) | `(soporte_ancho − separación) / 2` |
| **`anclaje_al_datum`** | **32 mm** | **Es la cota del contrato.** Del canto de apriete a la línea de anclaje |

Está arriba del todo a propósito: el péndulo cuelga por delante del bastidor,
así que el bloque tiende a volcar, se apoya por el canto de abajo y **tira** de
los tornillos. Puestos abajo, trabajarían a arrancamiento con poco brazo.

**Qué desbloquea.** El banco R1 se puede montar ya: el bloque se atornilla a
una tabla con este mismo patrón, y el día que haya bastidor se atornilla al
bastidor sin cambiar una cota.

**Qué sigue sin decidirse, y es correcto.** A qué altura queda el datum sobre
el eje del áncora. Esa cota es del bastidor, sale del paso 6 y **no está en el
contrato porque no se sabe**. Ponerle un número ahora sería inventárselo.

### Por qué 32 y no 30

El primer STEP del bloque trajo los taladros de anclaje a **30** del canto de
apriete, que es lo que sale solo al dibujar: con la fila del muelle a 10 y el
bloque de 40, poner la otra a 30 deja el boceto simétrico y se acota de una
pasada. **Pasa todas las envolventes** —7,9 mm de pared arriba, 3,9 sobre la
placa— y por eso no saltó nada.

Y sin embargo está mal, por una razón que no es de resistencia:

> Con 10 y 30 en un bloque de 40, **el patrón de los cuatro taladros es
> simétrico respecto a la mitad**. El bloque se puede montar del revés y los
> agujeros coinciden igual. Nadie lo ve en el taladro, y el canto de apriete
> acaba arriba: el datum se va al otro extremo del bloque.

Con 32, darle la vuelta da 8 y 30. No encaja, y eso es el seguro. Lo defiende
`test_las_dos_filas_de_taladros_no_son_simetricas`, que es el test que faltaba
—la asimetría no la pedía nadie, así que 30 parecía inocente.


---

## C11 · la corrección que no cabe en la tuerca

`core/reloj/pendulo.py` ya existe, y lo primero que ha dicho es que **la
varilla estaba mal cortada por 13 mm**.

Los 994 del contrato son la **longitud equivalente**: la del péndulo simple
que bate 2 s. Pero en un péndulo real la varilla tiene masa repartida, y su
masa está más arriba que la lenteja: sube menos el momento recuperador de lo
que sube la inercia, y el conjunto **oscila más deprisa**.

Con las cotas que había, el período salía **1,9874 s**: el reloj adelantaría
**544 s al día**, nueve minutos.

| | Antes | Ahora |
| --- | --- | --- |
| Centro de la lenteja al punto de flexión | 994 (el del péndulo simple) | **1007** · derivado por C11 |
| `varilla_largo` | 935 | **948** |
| Período calculado | 1,9874 s | **2,0002 s** |
| Desvío | +544 s/día | **−8,8 s/día** |

**Y lo que convierte esto en un hallazgo y no en un ajuste**: la tuerca M6 da
±10 mm en diez vueltas, unos ±440 s/día. La corrección son 563. **No cabe.**
Si la varilla se corta con el número del péndulo simple, el reloj no se puede
poner en hora por mucho que se gire la tuerca. Lo defiende
`test_la_correccion_de_c11_se_sale_del_recorrido_de_la_tuerca`.

Entra una cota nueva, `varilla_densidad` = 700 kg/m³, provisional: es la masa
de la varilla lo que mueve la corrección, así que **pesar la varilla real en R1
cambia el largo**. Por eso la varilla se corta larga y se recorta al final.

### La estimación de Q, y por qué 1.500

`bench/reloj/pendulo.json`, con `medido: false`. El número que hacía falta para
dimensionar el escape sin tener aún las piezas.

| | |
| --- | --- |
| Q si el aire fuese la única pérdida | **11.800** |
| Q previsto | **1.500** (rango 500–3.000) |
| Pierde por ciclo | 27 µJ |
| Potencia a reponer | **13,5 µW** |

El cálculo del aire no sirve para predecir: sirve para saber **dónde no está el
problema**. Con la lenteja de canto y una varilla de 8 mm, el aire daría un Q de
casi doce mil. Lo que va a limitar es el amortiguamiento interno del fleje y el
apriete de su mordaza, que no están en ninguna tabla. De ahí que 1.500 sea una
estimación conservadora y no un cálculo: **equivocarse por abajo sobredimensiona
la pesa, que es la pieza más barata de cambiar.**

---

## 1.6 · La escuadra del banco R1

Utillaje, no pieza del reloj. Se dibuja igual porque sin ella no hay medida, y
sin medida el escape se dimensiona a ojo.

**Lo que la hace útil es que respeta el contrato de anclaje**: el bloque se
atornilla aquí con el mismo patrón con el que se atornillará al bastidor, así
que pasa de uno a otro sin volver a taladrarlo. Es el primer cobro del contrato
de interfaz congelado en la 1.5.

| Cota | Valor | Por qué |
| --- | --- | --- |
| `escuadra_taladro_diametro` | **3,4** | **Guía, no paso.** Aquí el tirafondo rosca en la madera. Taladrar a 4,2 deja el bloque suelto y el péndulo bailando |
| `escuadra_bloque_al_canto` | **50** | Con el anclaje a 32 del datum, deja 18 mm de tablero sobre los tornillos. Con 40 quedaban 6 y el canto del tablero revienta |
| `escuadra_mordaza_libre` | 30 | Franja sin taladros a cada lado. Si la mordaza del banco pisa un tornillo, la tabla se monta torcida y el datum se inclina |
| `escuadra_espesor` | 18 | Más fino vibra con el péndulo y se lleva energía. Lo que se mide es el Q del péndulo, no el del banco |


---

## Paso 2 · 2.1, la rueda de escape

**C12 en el núcleo** (`core/reloj/escape.py`) antes que la pieza, porque el
número manda sobre la geometría. Con el Q previsto de 1.500:

| | |
| --- | --- |
| Par ideal en el eje de escape | **129 µN·m** |
| Con rendimiento del 12 % (optimista) | 1,07 mN·m |
| Con rendimiento del 2 % (pesimista) | **6,45 mN·m** |

El ideal supone que toda la energía de la rueda llega al péndulo. En un reloj
de madera llega entre el 2 y el 12 %, así que **el par real es entre ocho y
cincuenta veces mayor**. El valor del cálculo no es predecir: es saber qué
esperar del banco R2, y detectar que algo va mal si la medida se sale del
rango. Para el tambor son cifras ridículas, y eso confirma la viabilidad.

Un detalle que el núcleo obligó a corregir: **hay dos impulsos por oscilación**,
uno por paleta, y entre los dos la rueda avanza un diente. Olvidar el dos
duplica el par calculado.

### La primera pieza cuyo contorno se genera

Los treinta dientes salen del paso angular y de la inclinación: tocar
`dientes_escape` los redibuja todos. Es la diferencia entre paramétrico de
verdad y un dibujo con un número al lado.

| Cota | Valor | Por qué |
| --- | --- | --- |
| `rueda_escape_diametro` | **90** | Lo elige el paso: con 30 dientes da 9,4 mm de arco, el mínimo que se corta a mano con segueta sin astillar |
| `rueda_escape_paso_diente` | 9,42 · derivado | **Tiene envolvente propia**: ≥ 8 mm. Es la cota que decide si la rueda es fabricable |
| `rueda_escape_altura_diente` | **7** | Más alto da más retroceso y una punta más frágil; más bajo y la paleta se sale del diente al retroceder |
| `rueda_escape_inclinacion_diente` | **8°** | De los 12° del paso. Con 0 el diente es radial y la paleta resbala; con mucho, la punta es una astilla |
| `rueda_escape_cubo_diametro` | **24** | Dos diámetros y medio de eje. Menos y la rueda se descentra al apretar; más y pesa de más en el eje más rápido |

Es la primera pieza que usa **los tres mapas** del Variable Studio: longitudes
en `reloj_cota`, los dos ángulos en `reloj_angulo` y el número de dientes y el
abarque en `reloj_num`. Hasta ahora `reloj_angulo.csv` estaba vacío.

**Material y altura del diente los cierra R2.** Es la única pieza del reloj con
un modo de desgaste conocido: si el canto se marca antes de 10.000 ciclos, pasa
a latón.


### La inclinación del diente significaba dos cosas, y el STEP lo destapó

El primer STEP de la rueda trajo la cara del diente a **6,75°** del radio y el
contrato dice 8. La causa no es el dibujo: es que **la cota admitía dos
lecturas y mi propia hoja usaba las dos a la vez.**

- La vista de planta la generaba como **ángulo central**: punta desplazada 8°
  de centro, que a radio 45 son **6,3 mm de arco** y una cara a **44° del
  radio**. Otro diente.
- La vista de detalle la dibujaba como **ángulo de la cara con el radio**, que
  es la lectura correcta y la que siguió el CAD.

Arreglado el generador y fijada la lectura en la descripción: **el ángulo se
mide en la punta, entre la cuerda punta-fondo y la dirección radial.** Con 8° y
un diente de 7 mm, el desplazamiento de la punta es 0,98 mm de arco, que a
radio 45 son **1,486° de ángulo central** — el dibujo tiene 1,250.

### Y una cosa que un disco plano no puede llevar dentro

La rueda es simétrica en espesor, así que **darle la vuelta invierte hacia
dónde miran los dientes** y no hay geometría que lo impida. No es un defecto:
es el ajuste —si el escape no engancha, se voltea—. Pero obliga a declarar el
convenio, porque sin él el dibujo no tiene sentido de giro:

> Los dientes se inclinan en el sentido de giro **visto desde la esfera**.

Va en el contrato como `rueda_escape_vuelco_cambia_el_sentido`, en la hoja como
flecha de giro y rótulo «VISTA DESDE LA ESFERA», y en la banda de aviso.

El `rueda_escape_cubo_diametro` tampoco es geometría: en un disco plano de 4 mm
no hay cubo que tornear. Es el **asiento del collar** que aprieta la rueda
contra el eje, y la descripción lo dice ahora para que nadie lo busque en el
STEP.


---

## 2.2 · El áncora

**La cota que manda no está en la pieza: está entre las dos.**
`ancora_entre_centros` = 63,64 mm, del centro de la rueda al eje del áncora, y
es la más apretada del reloj. Por eso la hoja dibuja el escape montado y no el
áncora sola: en un dibujo de la pieza aislada esa cota no se ve.

No se elige. Sale de la construcción clásica del áncora de retroceso, que pone
el eje donde **cada brazo queda perpendicular al radio de la rueda en el punto
de contacto** —así la paleta empuja en la dirección del movimiento y no contra
el eje—. Eso hace el triángulo rectángulo, y con abarque de un cuarto de vuelta
sale isósceles: el brazo mide justo el radio de la rueda, 45 mm.

| Cota | Valor | De dónde sale |
| --- | --- | --- |
| `ancora_entre_centros` | **63,64** | `radio / cos(abarque/2)` |
| `ancora_brazo` | **45** | `radio × tan(abarque/2)` |
| `ancora_angulo_brazos` | **90°** | El mismo que abarca sobre la rueda |
| `ancora_recorrido` | **4°** | Dos veces la amplitud: la horquilla ata áncora y péndulo |

### El presupuesto angular, que es de suma cero

Los 4° del recorrido son **todo** lo que hay. Reposo, impulso y caída salen de
ahí; no se añaden. Y el reposo está apretado por los dos lados:

- **Por arriba**: los dos reposos no pueden pasar de la mitad del recorrido, o
  no queda ángulo para empujar. Con 1° el test falló por exactamente eso: 2° de
  reposo contra 2° de impulso.
- **Por abajo**: el reposo tiene que superar el **error de sierra** de la rueda.
  0,6° sobre un brazo de 45 son **0,47 mm**, contra los ±0,3 que se le piden al
  corte. Un reposo menor que el error de corte deja dientes que no llegan a
  apoyar, y el escape se dispara solo en algunos.

Queda en **0,6°**, que es el punto donde los dos límites dejan más margen. Si
R2 dice que es poco, el único sitio de donde sacar más es la **amplitud del
péndulo**, y eso cuesta energía al cuadrado.

### Lo que esta hoja no lleva, y no es un olvido

El reposo y el impulso **no van en ningún plano de pieza**. Las paletas son
postizas con ranura y tornillo: se ajustan en el banco R2, se marca la posición
buena, y entran en el dossier como **cotas de puesta a punto**. La ranura de
8 mm da 10,2° de recorrido de ajuste, diecisiete veces el reposo buscado.
