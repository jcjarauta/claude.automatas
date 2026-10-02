# Plan de diseño, de la primera pieza al bastidor

Qué se diseña, en qué orden, de qué parámetro sale cada cota y qué lo
comprueba. Es la aplicación pieza a pieza de `docs/reloj/metodologia.md`.

- La **metodología** (`metodologia.md`) dice cómo se diseña y por qué ese orden.
- Las **piezas** (`piezas.md`) dicen qué se fabrica y en qué tanda.
- Las **etapas** (`ROADMAP.md`) dicen cuándo y con qué puerta.
- Este documento es el puente entre los tres: **el recorrido de diseño**.

---

## El principio de orden

**Cada paso fija lo que el siguiente necesita, y nada más.** No es una
preferencia de método: es la cadena causal del §1 de la metodología, y
saltársela obliga a inventar un número.

```
  1. PÉNDULO        periodo -> longitud, inercia, Q
         |          ...............................
         v          el Q dice cuánta energía reponer
  2. ESCAPE         geometría del áncora -> PAR MÍNIMO MEDIDO
         |          ...............................
         v          el par dice cuánto puede perder el tren
  3. TREN           dientes, módulo -> distancias entre centros
         |          ...............................
         v          las distancias dicen dónde van los ejes
  4. TAMBOR         autonomía, caída -> diámetro, gargantas
         |
  5. ESFERA         relación 12:1 -> cañón, agujas
         |          ...............................
         v          todas las posiciones de eje, conocidas
  6. BASTIDOR       platinas, pilares, tabla de pared
         |
  7. ENSAMBLAJE     secuencia, cotas de puesta a punto, regulación
```

**El bastidor es lo último que se dibuja y lo primero que se monta.** Esa
inversión es la que hace que el orden importe: una platina taladrada antes de
conocer las distancias entre centros no tiene arreglo, porque en madera un
agujero mal puesto no se corrige.

### Lo que entrega cada paso

Un paso no termina con una pieza dibujada: termina con **un módulo del
compilador y una medida**. Si el módulo no existe, la cota siguiente se teclea
a mano; si la medida no existe, se inventa.

| Paso | Módulo | Medida que lo cierra | Etapa |
| --- | --- | --- | --- |
| 1 · Péndulo | `core/reloj/pendulo.py` | 100 oscilaciones en 200,0 s, y el Q | R1 |
| 2 · Escape | `core/reloj/escape.py` | **El par mínimo de arranque** | R2 |
| 3 · Tren | `core/reloj/tren.py`, `dentado.py` | Automática: relación exacta | R3 |
| 4 · Tambor | `core/reloj/energia.py` | Automática: la cuerda cabe | R3 |
| 5 · Esfera | `core/reloj/esfera.py` | Humana: se pone en hora sin mover el tren | R3 |
| 6 · Bastidor | `compile/reloj/conjunto.py` | Galga de centros, y nada choca | R3 → R5 |
| 7 · Ensamblaje | `emit/reloj/dossier.py` | 30 h sin pararse, y 7 días de marcha | R5 → R6 |

---

## Paso 0 · Antes de dibujar nada

Tres cosas que no son piezas y sin las cuales lo que se dibuje se mueve.

1. **El contrato de oscilador congelado.** Ya lo está: periodo 2 s, longitud
   nominal 994 mm. Es la raíz; si se mueve, se mueve todo.
2. **Las fichas de las piezas comerciales**, en `docs/piezas/`: muelle de
   suspensión, rodamientos, varilla calibrada, cuerda. Sus **cotas de
   interfaz** entran en el diseño; el STEP del fabricante se importa para
   mirar, no para acotar.
3. **El documento de Onshape del reloj**, con su tabla de variables propia.
   Hecho: `variables-reloj-*.csv`. Las de `REFERENCIA` no se importan.

**Nada se dibuja con un número tecleado.** Si una cota no está en
`docs/reloj/contratos.json` ni sale de una variable que sí esté, es que falta
decidirla, y decidirla a mano dentro del CAD es exactamente lo que el flujo de
un solo sentido existe para impedir.

---

## Paso 1 · El péndulo

**Es la primera pieza porque es la raíz de la cadena y porque no depende de
nada.** Se puede cortar hoy.

**Qué se fija.** La longitud real del péndulo, su momento de inercia y su Q.

**De dónde sale.** `periodo_pendulo` = 2 s. Pero **la fórmula del péndulo
simple no vale**: la varilla tiene masa repartida y la lenteja no es un punto.
El periodo real sale del péndulo compuesto,

```latex
T = 2\pi\sqrt{\frac{I_O}{m\,g\,d}}
```

con `I_O` el momento de inercia respecto al punto de suspensión y `d` la
distancia de la suspensión al centro de masas. Los dos salen del polígono con
`core/solido.py`, que ya existe y ya está probado contra el kernel 3-D.

**Piezas.** Varilla, lenteja, soporte de suspensión, tuerca de regulación.

**Las tres decisiones de diseño:**

- **Dónde empieza a medirse la longitud.** No en el extremo de la varilla: en
  el **punto de flexión del muelle de suspensión**, que está unos milímetros
  por debajo de su amarre y depende del espesor de la lámina. Es la cota de
  interfaz que la ficha del muelle tiene que declarar.
- **Cuánta masa va en la lenteja.** Cuanto más concentrada, más se parece al
  péndulo simple y menos le afecta el escape. Una lenteja pesada respecto al
  tren es la versión reloj del principio P3 del baseline: memoria gruesa,
  resultado fino.
- **La varilla se corta larga.** El nominal son 994 mm, pero la posición
  definitiva de la lenteja la decide la regulación. Se corta con 20 mm de más
  y se recorta al final, nunca antes.

**Envolvente.** El recorrido de la tuerca M6 tiene que cubrir el error de
montaje: diez vueltas dan ±7 min/día, de sobra.

**Cómo se comprueba.** Automática: un péndulo con toda la masa a distancia L
devuelve el periodo del péndulo simple dentro del 0,1 %; la varilla sola
devuelve el de una barra que pivota por un extremo. **Cruzada:** se cuelga y
se cronometran 100 oscilaciones, que deben ser 200,0 s.

**Qué desbloquea.** El Q medido, que dice cuánta energía hay que reponer por
oscilación. Sin ese número, el ángulo de impulso del escape es una suposición.

---

## Paso 2 · El escape

**El paso crítico.** Todo lo que viene después se dimensiona con el número que
sale de aquí.

**Qué se fija.** La geometría del áncora de retroceso y, sobre todo, **el par
mínimo con el que el escape arranca y mantiene la amplitud**.

**De dónde sale.** `dientes_escape` = 30 y `abarque_ancora` = 7,5. Con 30
dientes cada uno ocupa 12°, así que **el áncora abarca 90° de la rueda**: las
dos paletas trabajan a un cuarto de vuelta una de otra, que es lo que las hace
alternarse.

**Piezas.** Rueda de escape, cuerpo del áncora, dos paletas postizas,
horquilla, y una platina provisional de banco que se tira después.

**Las decisiones de diseño:**

- **Paletas postizas, con ranura y tornillo.** Es la única pieza del reloj
  donde ±0,3 mm de sierra cuestan marcha. Se diseñan para ajustarse después de
  cortar, no para salir exactas. El reposo y el impulso se buscan en el banco
  y se anotan como **cotas de puesta a punto**, que son las que no están en
  ningún plano de pieza.
- **Horquilla con fricción sobre el eje del áncora.** Poner el reloj en golpe
  se hace girándola, no inclinando el reloj en la pared. Un reloj que solo
  anda torcido es un reloj mal montado que alguien dio por bueno.
- **El material de la rueda de escape es provisional.** Abedul para empezar.
  Si el canto se marca antes de 10.000 ciclos, pasa a latón o a impresión 3-D.
  Es la única pieza del reloj con un modo de desgaste conocido.

**Envolvente.** Con reposo cero el modelo devuelve veredicto negativo: un
escape sin reposo se dispara con cualquier vibración. Y la energía por impulso
tiene que cubrir la pérdida por oscilación del Q medido en el paso 1, con
margen declarado.

**Cómo se comprueba.** **Cruzada, y es la puerta más importante del
proyecto:** se cuelga una pesa pequeña del eje de la rueda de escape y se
busca la mínima que mantiene la amplitud. **Humana:** se escucha. El tictac
tiene que sonar parejo; si suena cojo, las paletas no están simétricas.

**Qué desbloquea.** Todo. Hasta que el par no está medido, cualquier rueda que
se corte se corta con un número inventado.

---

## Paso 3 · El tren de marcha

**Qué se fija.** Número de dientes de cada rueda, pernos de cada piñón, módulo
del dentado y, de ahí, **las distancias entre centros**.

**De dónde sale.** La relación total es exacta y no negociable: de 1 vuelta por
minuto en la rueda de escape a 1 vuelta por hora en la central son 60:1, en dos
parejas. Un tren que redondea atrasa, y atrasa siempre en la misma dirección.

**Piezas.** Rueda grande, rueda central, tercera rueda; tres piñones de
linterna; cuatro ejes.

**Las decisiones de diseño:**

- **Los piñones son de linterna.** Dos discos y ocho pernos de varilla, no
  ocho perfiles cicloidales cortados a mano. Traslada la precisión de la
  sierra al taladro con plantilla, que es donde el taller puede ganarla.
- **El módulo lo pone la separación entre pernos**, no el tamaño de la rueda.
  Con 8 pernos de Ø3 en un primitivo de Ø16 quedan 6,28 mm entre centros
  contra un límite de 6,0: pasa, y por poco. Bajar el módulo deja los pernos
  sin madera entre ellos.
- **El compilador busca, no se elige a mano.** Hay varias combinaciones de
  dientes que dan la relación exacta. Se elige la que más margen deja en las
  siete envolventes, no la primera que aparece.

**Envolvente.** Las siete del §2b de la metodología. Las tres que de verdad
muerden aquí: pernos ≥ 8, separación entre pernos ≥ 2 × diámetro, y par
disponible > demandado en cada eje con el factor medido en el paso 2.

**Cómo se comprueba.** Automática: relación exacta sin redondeo, y un caso
construido a propósito con relación de contacto menor que 1 devuelve veredicto
negativo. **Humana:** mirar diez trenes dibujados. Un tren absurdo se ve antes
de calcularlo.

**Qué desbloquea.** Las distancias entre centros, que son lo que el bastidor
necesita y lo único que no tiene arreglo si se taladra mal.

---

## Paso 4 · El tambor, la cuerda y la pesa

**Qué se fija.** Diámetro del tambor, número de gargantas, longitud de cuerda
y la masa de la pesa.

**De dónde sale.** `autonomia` ÷ `periodo_rueda_grande` = 7,5 vueltas de
tambor. Con 2,0 m de cuerda, el tambor mide 85 mm.

**Piezas.** Tambor, trinquete, cliquet y su muelle, polea, cubo de la pesa.

**La decisión que hay que tomar antes de cortar el tambor:**

**¿Qué pasa mientras se da cuerda?** Con tambor y trinquete, al subir la pesa
el tren deja de recibir par durante los veinte segundos que dura la operación.
El péndulo tiene energía almacenada de sobra para seguir oscilando, así que el
reloj no se para, pero pierde algo cada día.

La alternativa clásica para un reloj de 30 horas es la **cuerda sin fin de
Huygens**: un lazo continuo sobre un tambor con púas, con la pesa en un ramal
y un contrapeso pequeño en el otro. Se da cuerda tirando del contrapeso y
**el tambor no deja de recibir par en ningún momento**. No lleva ni una rueda
más; lleva una polea más y un tambor que agarre.

| | Tambor y trinquete | Cuerda sin fin |
| --- | --- | --- |
| Piezas | Trinquete, cliquet, muelle | Una polea más, púas en el tambor |
| Al dar cuerda | El tren se queda sin par | Sigue recibiendo par |
| Cuerda | 2,0 m | Un lazo más largo, por calcular |
| Riesgo | Pierde unos segundos al día | La cuerda tiene que agarrar de verdad |

**Propuesta: decidirlo en R3, antes de cortar el tambor**, y por defecto
cuerda sin fin, que es lo que hacen los relojes de 30 horas desde hace tres
siglos. La longitud del lazo es un número abierto y sale del compilador, no de
este documento.

**Envolvente.** La caída de la pesa ≤ `caida_disponible`, y la cuerda
dimensionada con `tension_cuerda_techo` = 24,5 N, que sale del **techo de
5 kg** y no de la previsión de 3,5.

**Cómo se comprueba.** Automática: π × diámetro × vueltas = longitud de
cuerda, que es el test que impide que el reloj se pare antes de la autonomía
prometida.

---

## Paso 5 · La esfera y las agujas

**Qué se fija.** El tren de esfera, 12:1, y el ajuste a fricción que permite
poner el reloj en hora.

**De dónde sale.** `relacion_tren_esfera` = 12. El eje central da una vuelta
por hora y lleva la aguja de minutos; de ahí salen las horas.

**Piezas.** Cañón de minutos, rueda y piñón de minutos, rueda de horas, tres
agujas, esfera.

**La decisión de diseño que importa:**

**El cañón de minutos va a fricción sobre el eje central**, no calado. Es lo
que permite mover las agujas sin arrastrar el tren: se agarra la aguja, se
gira, y el tren se queda donde está. Calado, poner el reloj en hora significa
forzar el tren entero y, en madera, romper un diente.

La fricción se consigue con un tubo hendido o con fieltro, y tiene una
ventana estrecha: demasiada floja y las agujas se caen por su peso;
demasiado apretada y se arrastra el tren. **Es una cota de puesta a punto**,
no una cota de plano.

**Piezas que no dependen del movimiento.** La esfera, las agujas y la caja
no dependen del par ni del tren, así que **se fabrican en paralelo** con el
paso 6. Es el trabajo de nivel inicial del taller y no bloquea nada.

**Cómo se comprueba.** Humana: se mueve la aguja de minutos una vuelta
completa y el tren no se mueve; se suelta y el reloj sigue andando.

---

## Paso 6 · El bastidor

**Aquí converge todo.** Es el último paso de diseño y el primero de montaje.

**Qué se fija.** Dónde va cada eje, el tamaño de las platinas, la longitud de
los pilares y cómo se cuelga el reloj de la pared.

**De dónde sale.** Las distancias entre centros del paso 3. Pero una distancia
entre centros solo dice **cuánto** separar dos ejes, no **hacia dónde**: la
posición angular de cada pareja es libre, y elegirla es el diseño del bastidor.

**Piezas.** Platina delantera, platina trasera, cuatro pilares, separadores,
tabla de pared.

### Las cuatro restricciones que colocan los ejes

1. **El eje central es el centro de la esfera.** Lleva la aguja de minutos, así
   que su posición no se elige: es el datum, y todo lo demás se coloca
   respecto a él.
2. **La rueda de escape va arriba.** El áncora pivota sobre ella y el péndulo
   cuelga por detrás desde su suspensión: cuanto más alto el escape, más corta
   la horquilla y menos juego acumula.
3. **La rueda grande va abajo.** De ella cuelga la pesa, y tiene que caer libre
   por delante de las platinas.
4. **La pesa y el péndulo se reparten el mismo metro de pared.** El péndulo
   mide 994 mm y la pesa cae 1.000: **ocupan el mismo espacio y no pueden
   ocupar la misma vertical**. O la pesa cae a un lado del péndulo, o el
   péndulo va detrás y la pesa delante. Es la decisión de arquitectura del
   bastidor y conviene tomarla dibujando, no montando.

### La envolvente de conjunto

**Ninguna envolvente de pieza ve si una rueda choca con un eje que no
engrana.** Con cuatro ejes en una platina y una rueda grande de Ø128, hay
parejas de rueda y eje que se cruzan sin tocarse por pocos milímetros, y ese
hueco encoge cuando sube el módulo.

Es el mismo problema que el **hueco al poste** del escribiente, con otro
nombre: una cota que surge de montar varias piezas juntas y que no mira
ninguna comprobación de pieza suelta. Vive en `compile/reloj/conjunto.py` y
su límite son 3 mm.

### Cómo se fabrica, que condiciona cómo se diseña

**Las dos platinas se taladran apiladas, bajo una sola plantilla.** No
coinciden porque alguien mida bien: coinciden por construcción. De ahí salen
dos consecuencias de diseño:

- La plantilla de taladrado es **una pieza del paquete**, numerada y aparte
  de las plantillas de corte.
- Toda cota de posición de eje tiene que estar **en la plantilla**, no en el
  dossier. Si hay que leer un plano para taladrar, el método ha fallado.

**Cómo se comprueba.** Automática: nada choca, todo cabe en la platina con
10 mm de margen. **Humana:** la galga de centros entra o no entra en cada
pareja de agujeros. Binario, sin pie de rey.

---

## Paso 7 · El ensamblaje

**Qué se fija.** La secuencia de montaje, las cotas de puesta a punto y el
procedimiento de regulación.

### La secuencia, y dónde está el momento difícil

1. Platina trasera plana sobre la mesa, pilares puestos.
2. Ejes desde abajo: rueda grande, central, tercera, escape. Cada uno con sus
   separadores.
3. **La platina delantera entra con los cuatro pivotes a la vez.** Es el
   momento en que todo puede salir mal, y es la razón de que exista la cuna
   de montaje: dos manos no bastan para alinear cuatro pivotes.
4. Pasadores de los pilares.
5. Áncora y horquilla. Primera comprobación: el tren gira libre a mano.
6. Tambor y cuerda.
7. Colgar en la pared, nivelar, colgar el péndulo, colgar la pesa.
8. **Poner en golpe** girando la horquilla hasta que el tictac suene parejo.
9. Esfera y agujas, al final: estorban para todo lo anterior.

### Las cotas de puesta a punto

Son las que no están en ninguna pieza y por eso se pierden si no se escriben.
Van en el dossier, no en las plantillas.

| Cota | Dónde se ajusta | Cómo se sabe que está bien |
| --- | --- | --- |
| Reposo de las paletas | Tornillos de las paletas postizas | Galga de reposo, del paso 2 |
| Puesta en golpe | Horquilla, a fricción | El tictac suena parejo al oído |
| Juego axial de cada eje | Separadores | Gira libre, no cabecea |
| Fricción del cañón de minutos | Tubo hendido o fieltro | Se pone en hora sin mover el tren |
| Altura de la lenteja | Tuerca M6 | Marcha medida en 7 días |
| Nivelado del reloj | Tornillo de la tabla | Anda igual con la puerta abierta |

### La verificación, en dos puertas

- **Treinta horas sin pararse**, con la pesa nominal y sin esfera. Binario. Si
  se para siempre en el mismo punto del ciclo, es un pivote o un engrane; si
  se para al azar, falta pesa.
- **Siete días dentro de ±1 min/día**, ya completo y en la pared. Se regula
  con la tuerca el primer día usando los segundos por vuelta medidos en el
  paso 1, y se deja correr seis más.

La **hoja de marcha** —siete filas donde se anota la diferencia con el móvil—
es el equivalente de la hoja de trazo patrón del escribiente: cualifica el
reloj sin instrumentos, la rellena cualquiera, y alimenta `bench/reloj/` con
datos reales de deriva por unidad.

---

## Resumen: qué fija cada paso y qué no tiene arreglo

| Paso | Piezas | Fija | Si se hace mal |
| --- | --- | --- | --- |
| 1 · Péndulo | 4 | Longitud real, Q | Se recorta la varilla, tiene arreglo |
| 2 · Escape | 5 | **El par mínimo** | Se reajustan las paletas, tiene arreglo |
| 3 · Tren | 10 | Distancias entre centros | Rueda nueva, cara pero posible |
| 4 · Tambor | 6 | Autonomía real | Tambor nuevo, barato |
| 5 · Esfera | 8 | Puesta en hora | Cañón nuevo, barato |
| 6 · Bastidor | 8 | Posición de los ejes | **Platina nueva. No hay ajuste** |
| 7 · Ensamblaje | — | Cotas de puesta a punto | Se repite el montaje |

**La única pieza sin arreglo es la platina**, y por eso es la última que se
dibuja, se taladra con plantilla y con las dos apiladas, y se verifica con
galga antes de montar nada encima.

## Las decisiones que hay que tomar por el camino

| Cuándo | Decisión | Propuesta |
| --- | --- | --- |
| Paso 1 | Cuánta masa en la lenteja frente a la varilla | Lenteja pesada: perturba menos |
| Paso 2 | Material de la rueda de escape | Abedul, y latón si se marca antes de 10.000 ciclos |
| Paso 3 | Qué combinación de dientes, de entre las válidas | La de más margen en las siete envolventes |
| Paso 4 | **Tambor con trinquete o cuerda sin fin** | Cuerda sin fin, decidido antes de cortar el tambor |
| Paso 6 | Pesa a un lado del péndulo, o péndulo detrás | Dibujando las dos y mirando cuál cabe mejor |
