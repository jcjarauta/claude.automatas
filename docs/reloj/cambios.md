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


### Lo que faltaba para poder dibujarla

La primera hoja del áncora era un **esquema cinemático**, no un plano: dos
líneas y la distancia entre centros. Sirve para entender el escape y no sirve
para cortar nada. Seis cotas nuevas, todas del cuerpo:

| Cota | Valor | Por qué |
| --- | --- | --- |
| `ancora_cubo_diametro` | **24** | El mismo que el de la rueda: un solo collar para las dos piezas del escape |
| `ancora_brazo_material` | **40** | Donde acaba la MADERA, 5 mm antes del contacto. Los últimos 5 los pone la paleta |
| `ancora_ranura_al_eje` | **32** · derivado | La ranura acaba en la punta del brazo, así que su principio es lo único que hay que marcar |
| `ancora_hueco_a_la_rueda` | **6,6** · derivado | `entre_centros − radio − cubo/2` |
| `ancora_caja_ancho` / `_alto` | **66,6 × 45,3** · derivados | El trozo de tablero que hay que reservar |

**El brazo acaba corto a propósito**, y era lo que el dibujo no decía: si la
madera llegase hasta el punto de contacto, la paleta no tendría nada que
ajustar y el escape dejaría de ser regulable. Por eso hay una tercera vista,
el canto: la paleta va **sobre la cara**, no en el canto, y eso de frente no se
ve.

### El límite de conjunto del escape

`ancora_hueco_a_la_rueda` = 6,6 mm es el equivalente exacto del **hueco al
poste** del escribiente: una cota que surge de montar dos piezas juntas y que
**no la ve ninguna envolvente de pieza**. La rueda gira a 45 mm de su centro y
el cubo del áncora está a 63,64 de ahí; entre el canto de una y el cubo del
otro quedan 6,6. Tiene test, y el mínimo es 3.


---

## El escape pasa a Graham, y con él la amplitud

Decidido el 2026-10-02 tras cotejar con la demostración de Wolfram y con
Headrick. El detalle está en `docs/reloj/escape-propuesta.md`; aquí lo que
cambió y por qué.

### Un contrato congelado se ha tocado, y hay que decirlo

`amplitud_nominal` estaba dentro de `oscilador`, que es **congelado**. La regla
9 de `CLAUDE.md` obliga a pararse y avisar. Se ha hecho, y además la cota **ha
salido de ahí**: no era de ese contrato.

> `oscilador` es la raíz de la cadena causal: el periodo se **elige** y de él
> salen la longitud y la vuelta de la rueda. La amplitud no es raíz, **la
> impone el escape**: el barrido del áncora es dos veces la amplitud, y de él
> tienen que caber reposo, impulso, caída y arco suplementario.

Ahora vive en `ancora`, que está pendiente, que es donde puede moverse cuando
R2 mida. `periodo_pendulo` y `longitud_pendulo_nominal` siguen congelados.

### La envolvente que estaba mal planteada

`test_el_reposo_cabe_en_el_recorrido_con_sitio_para_el_impulso` repartía el
barrido entre reposo e impulso. Eso vale para un retroceso y **no para un
Graham**:

> En un deadbeat la cara de reposo es un **arco centrado en el eje del
> áncora**. Mientras el diente apoya ahí, el áncora gira sin mover la rueda y
> sin recibir nada. Ese tramo —el **arco suplementario**— es gratis, y es
> exactamente lo que distingue los dos escapes.

El presupuesto correcto es `reposo + impulso + caída + suplementario = barrido`,
y lo comprueba `test_el_presupuesto_angular_cierra`.

### El paquete intermedio

| | Antes | Ahora |
| --- | --- | --- |
| Amplitud | ±2° | **±3°** |
| Barrido del áncora | 4° | **6°** |
| Reposo | 0,6° | **1,5°** · 3,9× el error de sierra |
| Impulso | no existía | **2,0°** |
| Caída | no existía | **0,75°** |
| Arco suplementario | no existía | **1,75°** de colchón |
| Energía por ciclo (Q 1.500) | 27 µJ | **60,7 µJ** |
| Potencia a reponer | 13,5 µW | **30,3 µW** |

**Lo que fija el reposo no es el barrido: es el error de sierra.** 1,5° sobre un
brazo de 45 son 1,18 mm, casi cuatro veces los ±0,3 que se le piden al corte de
la rueda. Por debajo hay dientes que no llegan a apoyar y el escape se dispara
solo en esos.

Y lo que cuesta subir la amplitud **no es la energía** —30 µW siguen siendo nada
frente a los 318 de la pesa prevista— sino **error circular**, que es constante
si la amplitud lo es. Con deadbeat lo es, y ese es el argumento circular que
cierra: el Graham se paga con amplitud y la amplitud se sostiene porque es
Graham.

### Los dos arcos que hacen el deadbeat

| | |
| --- | --- |
| `ancora_arco_entrada` | **44,21 mm** |
| `ancora_arco_salida` | **45,79 mm** |
| `ancora_impulso_profundidad` | 1,57 mm |

Son los dos radios de las caras de reposo, **centrados en el eje del áncora**, y
difieren exactamente en la profundidad del impulso. Headrick da el mismo par
para su ejemplo —5,69" y 6,31" sobre un brazo de 3"— y esa coincidencia es la
comprobación de que la construcción es la buena.

### El diente pasa de un ángulo a tres

| Cota | Valor | Qué dice |
| --- | --- | --- |
| `rueda_escape_socavado` | 8° | Lo que la cara de ataque se inclina del radio. Antes se llamaba `inclinacion_diente` |
| `rueda_escape_angulo_incluido` | **23°** | El ángulo de la punta, entre cara y dorso |
| `rueda_escape_espesor_punta` | **0,5°** | **La punta no es un filo**: medio grado a radio 45 son 0,39 mm, y es justo donde apoya la paleta |
| `rueda_escape_fondo_relativo` | 0,844 · derivado | El fondo como fracción: cambiar el diámetro ya no rompe la proporción |
| `rueda_escape_radios` | **3** | La rueda deja de ser un disco. Es el eje más rápido del reloj |

Que el socavado coincidiera en 8° con el `undercut angle` de la demostración,
después de la corrección de esta mañana, es una validación cruzada que no
esperaba.


### El ángulo incluido no era una cota suelta, y faltaba el hueco

Al acotar el diente para poder trazarlo salió que `rueda_escape_angulo_incluido`
= 23° **no encajaba con el resto**: con nuestra altura y nuestro socavado, la
cuña que sale de la geometría es de **132°**. Un diente romo, no un gancho.

La causa es que mi generador hacía el dorso llegar **hasta el fondo del diente
siguiente**. Así no hay cuña que valga: el perfil es una onda continua.

Leído como lo que es —la **cuña de la punta**, entre cara y dorso— el diente se
reparte y aparece lo que faltaba:

| | Ángulo en la punta | Ángulo de centro |
| --- | --- | --- |
| Cara de ataque | socavado **8°** | adelanto **1,25°** |
| Punta | — | espesor **0,50°** |
| Dorso | incluido − socavado = **15°** | retraso **2,39°** |
| **Hueco** | — | **7,86°** |

El diente ocupa 4,14° de los 12 y **el hueco se lleva el resto**: 5,21 mm de
arco en el fondo, tres veces y media la hoja de una segueta.

> **Esa es la envolvente de fabricación que faltaba.** El `paso ≥ 8 mm` decía
> que los dientes están lo bastante separados; no decía que haya por dónde
> meter la sierra entre dos. Son cosas distintas y ahora las vigilan dos tests.

### Dos clases de ángulo que no son la misma

El socavado y la inclinación del dorso se miden **en la punta**; un boceto se
traza por **ángulos de centro**. La conversión es `atan(altura × tan(ángulo) /
radio)` y no es despreciable: 8° de socavado son 1,25° de centro.

Las dos conversiones están ahora declaradas —`punta_adelanto` y
`dorso_retraso`— porque **son los números que se teclean**, y pedirle a quien
dibuja que los calcule con un lápiz es pedirle que se equivoque. Es el mismo
error que ya costó un STEP esta mañana, en la otra dirección.

### La hoja pasa a tres paneles

La rueda con sus radios, **un diente a 12:1 acotado para trazarlo** —con los
cuatro ángulos de centro acumulados desde el pie del dorso, que es como se
construye— y **el engrane**, con el áncora puesta y los dos arcos de reposo
dibujados con su radio. Ese tercer panel es el que explica para qué sirve el
perfil: el diente apoya en un arco centrado en el eje del áncora, y por eso la
rueda no se mueve.

## 2026-10-02 · La medida entre dientes: 12°, y qué lee un pie de rey

Pregunta directa: *¿la medida entre dientes es 360 / 30 = 12°?* **Sí.** Es
`rueda_escape_paso_angular`, y es también la suma de los cuatro ángulos de
centro que reparten el diente:

```
retraso del dorso   2,39°
espesor de la punta  0,50°
adelanto de la cara  1,25°
hueco                7,86°
                    ------
                    12,00°
```

El problema es que **ese 12 solo se podía deducir sumando**. No estaba acotado
en ningún sitio. Ahora se traza como cota angular en el panel del diente,
rotulada `12° = 360 / 30`, para que el que dibuja no tenga que reconstruirla.

### Un pie de rey no mide un arco

Al bajarlo a milímetros aparece una distinción que importa en el taller:

| | |
| --- | --- |
| Paso de **arco** sobre el círculo de punta | 9,4248 mm |
| **Cuerda** entre dos puntas contiguas | 9,4076 mm |
| Diferencia | 0,0172 mm = **0,18 %** |

El arco es lo que calcula el compilador; la cuerda es lo que mide una
herramienta, que apoya en dos puntos y va en línea recta. Confundirlas mete un
sesgo del 0,18 % en cada lectura, siempre en el mismo sentido.

### La verificación salta cinco dientes: 45,00 mm

Medir 9,41 mm con un pie de rey deja un error de lectura del 0,5 % —del orden
del triple de la diferencia que se acaba de discutir—, así que no sirve para
verificar nada. La medida buena **salta dientes**, que es lo mismo que ya se
hace con el patrón de la impresora y por el mismo motivo: el instrumento tiene
que ser más fino que el error que se busca.

Con 30 dientes sale un número redondo y no por casualidad:

> **Cinco pasos son 60°, y la cuerda de 60° vale exactamente el radio.**

Así que la cuerda sobre cinco dientes es **45,00 mm**, el radio de punta clavado,
sin decimales que copiar mal. El error de lectura baja al 0,11 %.

Queda declarada como `rueda_escape_cuerda_cinco`, con tolerancia
`+/-0,2 · VERIFICACION` —no es una cota que se fabrique, es una que se
comprueba— y escrita en la hoja en un bloque VERIFICAR aparte, para que no se
confunda con las que hay que trazar. La cuerda entre dientes contiguos va
también al contrato (`rueda_escape_cuerda_diente`) porque es el número que
alguien va a medir de todos modos, y es mejor que esté dicho que no.

Tres tests lo defienden: que la cuerda no es el paso de arco, que la
verificación salta cinco dientes, y que con treinta dientes ese salto vale el
radio.

## 2026-10-02 · Ampliar el diente destapa que el contrato mentía

Pedir el detalle del diente a mayor escala no era una petición de estética. A
34:1 el perfil se ve, y lo que se vio es que **las dos caras no salen al ángulo
que el contrato pide**:

| | Pedido | Salía | Ángulo de centro guardado |
| --- | --- | --- | --- |
| Cara de ataque (socavado) | 8° | **6,75°** | 1,25° |
| Dorso | 15° | **12,68°** | 2,387° |

6,75° es exactamente lo que midió el revisor sobre el primer STEP del escape.
El 30 de septiembre escribí aquí que la culpa era mía por leer mal el ángulo y
que el arreglo iba en el generador. **El diagnóstico era correcto a medias: el
dibujo estaba bien, pero el número que puse en su lugar también estaba mal.**

### La conversión era la ingenua

Puse `atan(altura × tanα / radio_punta)`. Esa fórmula trata el desplazamiento
tangencial del flanco como si ocurriera **a radio de punta**, y ocurre al
bajar hasta el de fondo, donde el mismo milímetro de arco vale más grados. Se
queda corta un 16 %, siempre en el mismo sentido.

La buena sale de **cortar la recta del flanco con el círculo de fondo**. Con
la punta en el eje y `t` el largo del flanco:

```
t² − 2·R·cos(α)·t + (R² − r²) = 0
```

y de las dos raíces vale la corta, que es la que cruza el círculo de fondo
viniendo de la punta. El ángulo de centro es entonces
`atan2(t·sinα, R − t·cosα)`.

| | Antes | Ahora |
| --- | --- | --- |
| `rueda_escape_punta_adelanto` | 1,25° | **1,486°** |
| `rueda_escape_dorso_retraso` | 2,387° | **2,848°** |
| `rueda_escape_hueco_angular` | 7,86° | **7,166°** |
| Hueco en mm de arco al fondo | 5,21 | **4,75** |

El hueco encoge porque el diente ocupa más de lo que decía: 4,83° de los 12 en
vez de 4,14. Sigue holgado para la segueta, que es lo que vigila su test.

### Por qué no saltó ningún test

Porque el test **comparaba la fórmula consigo misma**: leía
`punta_adelanto` del contrato y lo contrastaba contra
`atan(altura × tan(socavado) / radio)`, que es de donde había salido. Un test
así no puede fallar nunca, y no falló.

El que hay ahora traza el flanco con el ángulo de centro guardado y **mide**
lo que se aparta del radio en la punta. Es la ida y vuelta, y es la misma
definición que usa el revisor de STEP, así que el contrato y el revisor ya no
pueden discrepar en silencio. Al núcleo va `escape.angulo_de_centro`, con
cuatro tests propios, uno de los cuales deja constancia del tamaño del error
para que nadie vuelva a la fórmula corta pensando que es equivalente.

> **La lección de método**: un test que reproduce el cálculo que vigila no es
> un test. Vigilar una conversión exige medir el resultado por un camino que
> no comparta código con ella. Es lo mismo que ya se hace con la masa del
> kernel contra la del polígono, y lo que no se estaba haciendo aquí.

---

## 2026-10-02 · Las paletas, y que no son iguales

La pieza 2.3. El áncora tenía brazos, ranura y arcos, pero **lo que toca el
diente no estaba dibujado en ninguna parte**: la paleta era una línea gruesa.

### El plano de impulso sale de la geometría, no se elige

La paleta gira sobre su eje mientras el diente desliza sobre ella. Si se lleva
el contacto final al marco propio de la paleta —girándolo lo que la paleta
gira— la cara queda determinada:

```
media   = atan(profundidad / (brazo × impulso))
entrada = media − impulso/2
salida  = media + impulso/2
```

El contrato ya había elegido `profundidad = brazo × impulso`, que iguala la
bajada radial al barrido tangencial. Los dos catetos valen lo mismo, 1,571 mm,
y el plano que une los extremos es **la diagonal del cuadrado**: 45° de media
y 2,222 mm de largo.

### Y ahí está el que importa

> **La de entrada va a 44° y la de salida a 46°.** La diferencia no es un
> residuo de cálculo: es el ángulo de impulso **entero**, repartido mitad y
> mitad.

Viene de que la paleta gira mientras el diente desliza, lo que sesga la
geometría hacia un lado en la entrada y hacia el otro en la salida. Cortar las
dos a 45 —que es exactamente lo que invita a hacer un dibujo simétrico, y lo
que haría cualquiera con una sola plantilla— deja cada una a un grado de donde
va. Y un grado sobre dos de impulso es **la mitad del tramo en que entra
energía**.

Por eso las dos van juntas en la misma hoja y a la misma escala: es lo único
que impide el error.

Lo comprueban tres tests contra una construcción geométrica a pelo —intersecar
el círculo de punta con el arco de reposo y girar— que no comparte una línea
con la forma cerrada.

### El resto de la pieza

| | |
| --- | --- |
| Arco de reposo | R44,21 (entrada) y R45,79 (salida), centrados en el eje del áncora |
| Largo del arco | 4 mm, con mínimo de 3,2 |
| Plano de impulso | 2,222 mm |
| Taladro al arco | 9 mm, **la cota que fija el reposo** |
| Cuerpo | 14 × 10 × 4 |
| Material | Latón de 4 |

El **largo del arco** es la envolvente que faltaba por este lado. Tiene que
cubrir suplementario + reposo = 3,25°, que sobre R45,79 son 2,60 mm, más 0,59
de margen por si un diente corto de sierra apoya antes de lo previsto: 3,19.
Se dibuja 4. Corto, el diente se queda en el vacío al final del suplementario
y el escape se dispara solo.

El **taladro a 9 del arco** cae en el medio de la ranura de 8 del brazo, y eso
no es casualidad: deja ±4 mm de puesta a punto a cada lado. Descentrado, el
ajuste sale cojo —todo para un lado y nada para el otro— y mover la paleta 1 mm
cambia el reposo en 1,3°.

El **latón de 4** es el mismo espesor que la rueda, y el dossier exige las dos
caras coplanarias. Más delgada y el diente apoya en parte de su canto, que
marca la madera en una línea en vez de una cara. Va duro contra el abedul
porque la paleta recibe un golpe cada 2 s y cada diente uno cada 60: se
desgasta treinta veces más deprisa.

### De paso, el presupuesto del áncora era el del retroceso

La hoja 2.2 pintaba la barra como `reposo · impulso y caída · reposo`, con el
reposo a los dos lados. Eso es un retroceso. En un Graham son **cuatro tramos
y una vez cada uno**: suplementario 1,75 + reposo 1,50 + impulso 2,00 + caída
0,75 = 6°. Corregido en las dos hojas.

Y `revisar_cad.py` seguía pidiendo `rueda_escape_inclinacion_diente`, una cota
que dejó de existir cuando se partió en tres el 30 de septiembre: el revisor de
la rueda habría reventado al primer STEP. Ahora lee `rueda_escape_socavado`.

## 2026-10-02 · Revisar las cotas para trazar: faltaban cuatro y sobraba un filo

Al mirar la hoja 2.1-D con la pregunta correcta —**¿se puede trazar el diente
con lo que hay aquí?**— salen tres cosas.

### Faltaban las cotas con las que se traza

La hoja daba las cuatro separaciones perpendiculares y la tabla de los cinco
puntos. Las dos cosas sirven para un CAD, donde se teclean coordenadas. Para
un lápiz y un compás, no: **lo que se le da a un compás es el flanco**, y el
flanco no estaba.

| Cota nueva | Vale | Qué es |
| --- | --- | --- |
| `rueda_escape_dorso_largo` | 7,296 | El flanco A→B |
| `rueda_escape_cara_largo` | 7,082 | El flanco C→D |
| `rueda_escape_punta_cuerda` | 1,178 | El ancho de la punta, B–C |
| `rueda_escape_hueco_cuerda` | 4,087 | El hueco en el fondo, D–A′ |

Ninguno de los dos flancos vale 7. Esos son la **altura radial**, que es el
cateto; el flanco es la hipotenusa, y va más largo cuanto más tumbado. Darle 7
al compás deja el pie fuera del círculo de fondo.

Con esas cuatro, el trazado son seis pasos **sin un solo ángulo**, y la hoja
los lleva escritos. A 34:1 el centro de la rueda cae a metro y medio de la
hoja, así que no hay dónde poner el vértice de un ángulo: el único trazado que
vale es el que no usa ninguno.

De paso se acotan `R45` y `R38` en el dibujo, que estaban solo en la tabla.

### La punta era un filo: 0,5° → 1,5°

Medio grado a radio 45 son **0,39 mm**. El contrachapado de abedul tiene chapas
de 1,3 mm; una punta de cuatro décimas no es una pieza, es una astilla
esperando el primer golpe — y la punta recibe uno cada dos segundos, que son
43.200 al día.

> El test que lo vigilaba pedía ≥0,3 mm. Su propio docstring decía que 0,39 era
> «un filo que el contrachapado no da», y el umbral lo dejaba pasar. **Un
> umbral que no sostiene lo que dice su motivo no vigila nada.**

Sube a 1,5°, que son 1,178 mm, y el umbral a 0,8. Lo paga el hueco, que es de
donde sale: 7,166° → 6,166°, o 4,75 → 4,09 mm de cuerda en el fondo. Sigue muy
por encima de los 3 que pide la segueta.

Y el umbral ya no se escribe en grados sino en milímetros, contra
`punta_cuerda`. Es la misma lección que la cuerda de verificación: **medio
grado suena razonable y cuatro décimas de milímetro no**, y la unidad en que
se juzga una cota decide si el juicio es posible.

### Y la fórmula vieja seguía viva en un segundo sitio

`test_los_tres_angulos_del_diente_caben_en_el_paso` calculaba el ángulo de
centro con `atan(altura × tan(socavado) / radio)`, el resto del error de esta
mañana. Daba el diente más estrecho de lo que es, que es justo lo que ese test
tendría que cazar. Ahora llama a `escape.angulo_de_centro`.

**Cuando se corrige una fórmula hay que buscarla, no acordarse de dónde
estaba.** Un `grep` del patrón habría encontrado los dos sitios a la primera.

Al núcleo van `largo_del_flanco` —la raíz corta de la misma ecuación— y
`cuerda`, que es trivial y existe porque el proyecto ya se ha tropezado tres
veces con la diferencia entre el arco y la cuerda: tenerla con nombre obliga a
elegir cuál se está pidiendo.

## 2026-10-03 · La envolvente de conjunto del escape, y el banco R2 al doble

`core/reloj/graham.py` monta la rueda, las paletas y el yugo y **los mueve**:
gira el áncora en pasos de 0,05° y deja avanzar la rueda hasta que toca. Si
el áncora no cabe, el escape está atascado; si nada para la rueda, desbocado;
si la rueda tiene que volver atrás durante el reposo, ya no es un Graham.
`juzgar()` da la vuelta entera —cada diente pasa por las dos paletas— en unos
seis segundos.

Es la envolvente que faltaba: ninguna comprobación de pieza suelta ve si la
paleta cabe entre dos dientes o si el diente apoya en su punta.

### Lo que dice del contrato vigente

**No pasa**, y por eso la geometría del banco vive aparte, en
`docs/reloj/escape-r2.json`, hasta que R2 la confirme:

| | Contrato | Qué pasa | Banco R2 |
| --- | --- | --- | --- |
| Diente | cara con el pie 1,49° **por delante** de la punta | la paleta apoya en la cara, 1,1 mm bajo la punta, y la rueda retrocede ~0,2° por golpe | socavado de verdad: pie **detrás**. Apoya en R45,00 |
| Paleta | bloque de 14 a lo largo del camino del diente | no cabe entre dos puntas (8,2 mm): se atasca | dedo de 2,2 mm de ancho de trabajo |
| Caras de reposo | 44,21 / 45,79, las dos por fuera | la de salida tiene que bloquear por **dentro** | las dos en R45,00; caídas en 42,80 y 47,20 |
| Yugo | V de brazos tangentes | el canto interior pasa a 40 mm del centro, dentro de la banda de dientes | yugo a 20°, piernas hasta R53 |

Lo defienden `tests/reloj/test_graham.py`: el diente en cuña retrocede, una
paleta que no cabe se atasca, sin reposo se desboca, y la propuesta da la
vuelta entera también con error de sierra de 0,3 mm.

### El banco se imprime al doble, en A3

El error de sierra es en milímetros y los ángulos del escape no cambian al
escalar. Al doble (rueda de Ø180, 127,28 entre centros) el mismo ±0,3 mm pesa
la mitad:

| Ancho de paleta (equivalente a escala 1) | Escala 1, sierra ±0,3 | Escala 2, sierra ±0,3 |
| --- | --- | --- |
| 2,2 | funciona | funciona |
| 2,75 | se atasca | **funciona** |
| 3,0 | — | se atasca |

Una paleta más ancha empuja más rato: de 2,8° de impulso de rueda por golpe a
3,4°. Y todo es más fácil de cortar y de limar: la nariz de la paleta pasa de
2,2 a 4,4–5,5 mm y la punta del diente de 1,18 a 2,36.

**Lo que cuesta, y no es del banco sino del bastidor (paso 6).** La rueda de
Ø180 no cabe entre platinas con el tren de ejemplo: la tercera rueda engrana
con la linterna de escape a 68 mm, y un radio de 90 pasa por encima de su
eje. O el escape va por fuera de la platina —a la vista, como en muchos
relojes de madera—, o la última pareja se separa. Dentro, el máximo con 5 mm
de aire es una rueda de unos Ø116. La inercia de la rueda sube con la cuarta
potencia de la escala en un disco plano: los radios de aligerado pasan a ser
obligatorios en la definitiva.

`scripts/plantillas_escape_r2.py` saca el PDF: hoja de banco (taladros, rueda
ideal con banda de ±0,3 y escala de ángulos para una aguja), plantillas de
rueda, yugo y tres juegos de paletas (4,4 / 5,0 / 5,5) y el protocolo con la
tabla diente a diente. Juzga cada ancho antes de escribir nada.
