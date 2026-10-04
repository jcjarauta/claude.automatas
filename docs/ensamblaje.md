# El ensamblaje en Onshape

Cómo se monta el escribiente dentro del CAD, qué comprueba eso y qué **no**
comprueba. Investigado contra la documentación de Onshape el 2026-10-03; las
fuentes están al final.

El plano de conjunto que acompaña a este documento lo genera
`scripts/dibujar_conjunto.py` desde `docs/contratos.json`. Este documento es
la otra mitad: el de ahí dice dónde va cada pieza, y este dice **con qué
emparejamiento se dice eso en Onshape y en qué orden**.

---

## 0. Qué es Onshape para esta máquina, y qué no

Es un solucionador **cinemático**: emparejamientos, relaciones y arrastre.
Aparte, y sin tocarse con lo anterior, lleva un FEA **estático lineal y
modal**. Entre esas dos cosas no hay nada.

| Lo que necesitamos | Onshape | Dónde se queda |
| --- | --- | --- |
| Girar el árbol y ver la frase escribirse | **Sí** — un emparejamiento animado | — |
| Que el rodillo siga el perfil de la leva | **Sí, con cuidado** — tangente vértice ↔ curva de paso | §5 |
| Amplificación 6:1 del cabestrante | **Sí** — relación de engranaje, ratio 6 | §3 |
| Reducción 3:1 de la manivela | **Sí** — relación de engranaje, ratio 3 | §3 |
| Cerrar el cinco barras | **Sí**, con el último emparejamiento cilíndrico | §4 |
| Hueco al poste durante el giro | **Manual**, posición a posición | §6 |
| Error de trazo, ángulo de presión, par, energía | **No existe** | `core/` |
| Volante, inercia, suavidad, el tacto de la mano | **No existe** | `compile/energia.py` |
| Detección de colisiones al moverse | **No existe** | §6 |
| Exportar la animación a vídeo | **No existe** | grabador de pantalla |

Tres ausencias que conviene tener claras antes de empezar, porque cambian el
plan y no se arreglan con maña:

- **No hay motion study.** No hay línea de tiempo, ni fotogramas clave, ni
  gráficas de posición, velocidad o aceleración. Hay un botón que anima **un**
  emparejamiento y nada más.
- **No hay dinámica.** Ni gravedad que mueva nada, ni fuerzas, ni inercia. La
  «Acceleration» de Simulation es una carga estática, no un campo.
- **No hay contacto.** Ni colisión, ni rodadura, ni detección de choque al
  moverse. Lo dice el blog de Onshape de la propia relación de engranaje:
  *«does not detect geometry collisions; it is a mathematical link»*.

**Entonces, ¿para qué?** Para lo mismo que la hoja de trazo patrón, pero en
pantalla y antes de cortar: caza un cartucho calado donde no toca, un brazo
con el calaje equivocado, una leva cambiada de sitio, un poste donde no cabe.
No caza décimas. El número lo sigue dando `core/`, y si el CAD y el
compilador discrepan en un número, **el que se equivoca es el CAD**.

---

## 1. El árbol de subconjuntos

En Onshape **un subconjunto es flexible por defecto** y no hay interruptor que
lo cambie: el movimiento definido dentro sube solo al nivel de arriba. Lo
contrario —la rigidez— se gana de tres maneras, y la que nos sirve es la
primera: *«zero degrees of freedom between all parts in an Assembly, and one
of the parts is fixed»*. Un subconjunto rígido **el nivel de arriba se lo
salta al resolver**, así que agrupar bien es también lo que hace que la
máquina se arrastre sin pensárselo.

```
escribiente                      ← el conjunto de arriba
├── bastidor            RÍGIDO   base FIJA + 3 postes + 3 platos + 4 rodamientos
│                                + 2 apoyos del eje del balancín (colgados del plato 2)
│                                + 4 soportes de la mesa + 4 ejes fijos de la mesa
├── cartucho            RÍGIDO   árbol (92) + 3 levas + 2 separadores + pasador
│                                + casquillo de la rueda + rueda Z60
├── canal               RÍGIDO   seguidor + sector + 2 mordazas + casquillo + rodillo
│                                ×2 (canal izquierdo y canal derecho)
├── canal_elevador      RÍGIDO   seguidor + casquillo + rodillo + casquillo de la bieleta
├── pivote              RÍGIDO   eje_pivote (55) + tambor (en D) + brazo_proximal
│                                ×2 (izquierdo y derecho; el derecho VOLTEADO)
├── accionamiento       RÍGIDO   eje de la manivela + piñón Z20 + volante + manivela + pomo
│                                (el volante ENCIMA del plato 3, no en la bahía)
├── brazo_distal                 ×2 CURVOS, sueltos en el nivel de arriba (el izquierdo volteado)
├── punta               RÍGIDO   tubo de la punta + brazo y poste de la horquilla
├── lapiz               RÍGIDO   portaminas + pinza; cuelga de la punta por las 2 láminas
├── eje_balancin        RÍGIDO   eje Ø4 + balancín (a 90°, hacia arriba) + palanca + bulón
│                                + tirante
├── bieleta                      varilla doblada: seguidor 3 ↔ balancín
├── mesa                RÍGIDO   mesa + 2 orejetas + 2 ejes móviles
└── biela_mesa                   ×4, sueltas en el nivel de arriba
```

Tres decisiones de agrupación que no son evidentes:

**El árbol va dentro del cartucho**, no fuera. Las tres levas, los dos
separadores, el pasador de índice y la rueda Z60 no se mueven unos respecto de
otros ni respecto del árbol: son un solo sólido con un solo grado de libertad.
Metidos juntos, el nivel de arriba gasta **un** emparejamiento donde si no
gastaría seis, y es además donde el pasador de índice hace su trabajo: si
atraviesa los tres taladros, la fase está bien, y eso se ve dentro del
subconjunto sin montar nada más.

**El eje de pivote, el tambor y el brazo proximal son una pieza sola.** Los
tres están calados entre sí por la misma cara plana de la barra Ø10 h6. Que
sean tres piezas es una decisión de fabricación, no de cinemática.

**El cinco barras se queda en el nivel de arriba**, sin subconjunto. Un lazo
cerrado metido dentro de un subconjunto es más difícil de diagnosticar: hay
casos documentados en el foro de errores que persisten dentro del subconjunto
después de suprimir todos los emparejamientos de arriba. Y es justo la parte
que va a dar problemas (§4), así que conviene tenerla a la vista.

**La cinta del cabestrante no se modela.** Un fleje de 0,05 mm no es una pieza
rígida y Onshape no tiene nada que hacer con ella. Lo que la sustituye es una
relación de engranaje con ratio 6, que es cinemáticamente lo mismo mientras no
deslice. Lo que la relación no sabe es que la cinta se estira 0,092 mm; eso
está en `compile/tolerancias.py` y ahí se queda.

---

## 2. Los emparejamientos, uno a uno

**Un emparejamiento por par de instancias.** En Onshape el emparejamiento *es*
la articulación entera, no media restricción: *«the movement (degrees of
freedom) between those two instances is embedded in the Mate»*. Apilar
«concéntrica + coincidente» al estilo de SolidWorks es la causa número uno de
sobrerrestricción, y aquí no hace falta ni una vez.

| # | Tipo | Entre | Dónde | Deja |
| --- | --- | --- | --- | --- |
| M0 | **Fix** | base | — | 0 |
| M1 | **Revolute** | cartucho ↔ plato 1 | árbol, Ø19 H7 central | Rz ← **el animado** |
| M2 | **Revolute** | canal izquierdo ↔ poste 1 | (−61,543, −67,982) | Rz |
| M3 | **Revolute** | canal derecho ↔ poste 2 | (+61,543, −67,982) | Rz |
| M4 | **Revolute** | canal elevador ↔ poste 3 | (0, +38,613) | Rz |
| M5 | **Revolute** | pivote izq ↔ plato 1 | (−60, 0) | Rz |
| M6 | **Revolute** | pivote der ↔ plato 1 | (+60, 0) | Rz |
| M7 | **Revolute** | distal izq ↔ proximal izq | codo izquierdo | Rz |
| M8 | **Revolute** | distal der ↔ proximal der | codo derecho | Rz |
| M9 | **Cylindrical** | distal izq ↔ distal der | la punta, (0, 100) | Rz + Tz ← **cierra el lazo** |
| M10 | **Revolute** | accionamiento ↔ plato 2 | (−14, −8,202) | Rz |
| M11 | **Tangent** | vértice del rodillo izq. ↔ curva de paso izquierda | — | §5 |
| M12 | **Tangent** | vértice del rodillo der. ↔ curva de paso derecha | — | §5 |
| M13 | **Tangent** | vértice del rodillo elev. ↔ curva de paso del elevador | — | §5 |

Coordenadas en el **marco del cinco barras**, que es el de la base y el de la
planta del plano de conjunto. El árbol cae en (0, −32,451).

Los tres canales se llaman como en `compile/escribiente.py` —**izquierdo**,
**derecho** y **elevador**— y no «x» e «y»: el cinco barras no se conduce por
coordenadas, sino por los dos ángulos de brazo. El poste 1 es el del canal
izquierdo, el 2 el del derecho y el 3 el del elevador, en el mismo orden en
que `poste_reparto` los va colocando a 120°.

**M9 es cilíndrico y no de revolución, y eso no es un apaño.** Los dos
distales trabajan en planos distintos —los proximales se cruzan, el derecho
queda un milímetro más bajo que el izquierdo— así que el perno de la punta
tiene juego axial de verdad. El cilíndrico lo dice y el de revolución mentiría.
Que además sea lo que salva el lazo (§4) es una coincidencia afortunada.

---

## 3. Las relaciones

Solo existen **cuatro** en todo Onshape: engranaje, piñón-cremallera, husillo
y lineal. No hay relación de leva, ni de cable, ni de correa. Y se aplican a
**emparejamientos ya hechos**, no a piezas.

| # | Tipo | Entre | Ratio | ¿Invierte? |
| --- | --- | --- | --- | --- |
| R1 | **Gear** | M2 ↔ M5 (izquierdo) | **6** | NO — es una cinta |
| R2 | **Gear** | M3 ↔ M6 (derecho) | **6** | NO — es una cinta |
| R3 | **Gear** | M1 ↔ M10 | **3** | SÍ — son dos engranajes |

El 6 sale de los radios de fibra neutra: sector 48, tambor 8. No de dientes,
porque no hay dientes; la ayuda de Onshape autoriza expresamente usar la
relación de engranaje para *«any two components that should rotate with
respect to one another with a given ratio»*, poleas incluidas.

**La casilla Reverse es la que distingue una cinta de un engranaje.** Una
correa abierta hace girar las dos poleas en el **mismo** sentido; un par de
engranajes en sentidos **opuestos**. Así que R1 y R2 llevan una marca y R3
lleva la contraria, y cuál es cuál depende del convenio interno de Onshape,
que no he podido verificar. **Se comprueba mirando**: arrastra el seguidor y
mira hacia dónde se va el brazo. Si el brazo se va al revés que el seguidor,
marca Reverse en esa relación.

Y hay una restricción que cierra una puerta: **«Tangent Mate does not work
with any Relations»**. Los tangentes M11–M13 no pueden entrar en ninguna
relación. No nos hace falta —la amplificación va entre dos revolutes, no toca
al tangente— pero conviene saberlo antes de intentarlo.

---

## 4. El lazo cerrado, que es lo que va a dar guerra

El cinco barras es un lazo cerrado y Onshape **no tiene tratamiento especial
para los lazos**: intenta satisfacer todas las restricciones a la vez. Un lazo
plano montado todo con revolutes es redundante, y solo es consistente si la
geometría es exacta hasta el último bit. Como no lo es, sale en rojo:

> `Mate overdefines the assembly`

A veces sobre varios emparejamientos a la vez, no sobre el culpable. El
diagnóstico de sobrerrestricción de Onshape es flojo —no hay contador numérico
de grados de libertad, solo un icono— y eso es una queja constante en el foro.

**La receta, y viene del propio personal de Onshape, repetida en cuatro hilos
distintos: el emparejamiento que CIERRA el lazo se pone cilíndrico.**

NeilCooke (Senior Director Technical Services EMEA de Onshape): *«Change one
of the revolute mates to a cylindrical mate — it's a tolerance thing where the
translation part of the two revolute mates are fighting each other»*. Y en
otro hilo: *«there will be a planar offset tolerance issue somewhere in the
chain»*. El cilíndrico libera `Tz`, que es exactamente donde se acumula el
desajuste fuera del plano. La articulación sigue girando igual; lo único que
se afloja es un deslizamiento axial de micras.

Aquí eso es **M9**, el perno de la punta. Que además sea físicamente cierto
(§2) lo hace fácil de defender.

**Procedimiento, y es lo que ahorra la tarde:**

1. Pon los emparejamientos del lazo **de uno en uno**, y deja M9 para el
   final.
2. Si al poner M9 sale rojo con un revolute, cámbialo a **cilíndrico**.
3. Si sigue rojo, cambia M9 a **esférico** (`Ball`). Un cilíndrico libera `Tz`
   pero en un lazo plano quedan `Rx` y `Ry` todavía redundantes; en la
   práctica los otros revolutes los fijan de forma consistente, pero si no,
   el esférico es el siguiente escalón. *(Esto último es razonamiento propio,
   no está en ninguna fuente.)*
4. Si aparece en rojo algo que ya estaba bien, **suprime** candidatos con el
   botón derecho hasta aislar el conflicto. Suprimir es más barato que borrar
   y rehacer.

**Y una trampa aparte, la de las ramas.** Un cinco barras tiene dos soluciones
por punto, y el solucionador puede elegir la que no es: el codo apunta hacia
dentro en vez de hacia fuera. Es el mismo problema que ya está documentado en
`CLAUDE.md` para `core/actors/`. Si al cerrar el lazo la figura sale doblada
del revés, arrastra un codo hacia donde debe ir **antes** de poner el último
emparejamiento: el solucionador parte de donde están las piezas.

---

## 5. El contacto leva–rodillo

**No hay nada nativo.** No existe emparejamiento de leva, ni contacto, ni
rodadura. Philip Thomas (Onshape), textual: *«outside of a kinematic tool,
Onshape does not support intermittent contacts»*.

Lo que sí hay, y está documentado por Onshape en una tech tip, es un
**emparejamiento tangente entre un vértice y una curva**. El tangente es el
único que no usa conectores: *«it only requires two entity selections»*. Y el
vértice que nos interesa es el **centro del rodillo**, cuyo lugar geométrico
es exactamente la **curva de paso** que ya calcula `core/cam/synth.py`.

```
vértice  = punto del croquis en el centro del rodillo, sobre el seguidor
curva    = curva de paso de esa leva, importada y unida en UNA sola curva
```

Cuatro detalles que deciden si funciona:

- **Es la curva de paso, no el perfil cortado.** El perfil es por dónde pasa
  el canto del rodillo; la curva de paso es por dónde pasa su centro. Son dos
  curvas distintas separadas por los 3 mm del radio del rodillo.
- **Tiene que ser UNA curva.** Se unen los tramos con un *3D fit spline* y se
  mete en el ensamblaje como **Composite Part**: *«Use a 3D fit spline to
  combine multiple segments of curves or sketches into one single 3D curve»*.
  Con la curva partida, el tangente coge solo el primer trozo.
- **Cara contra cara NO vale.** La ayuda del tangente: *«Only swept faces are
  supported (torus, cones, etc), no generic faces (like splines)»*. Un perfil
  de leva sintetizado es exactamente una cara genérica. Esta es la razón por
  la que el camino es vértice ↔ curva y no el que parecería natural.
- **Cuidado con sobredefinir.** Hay un caso en el foro donde *«the revolute
  mate was keeping the tangent from working»*. Si el tangente no engancha,
  suprime temporalmente el revolute del seguidor.

**Hace falta una curva de paso en DXF que hoy no sale del compilador.**
`PerfilLeva.paso` la tiene calculada; el paquete de CAD exporta el perfil
cortado y no ella. Es un emisor pequeño y lo añadimos cuando lleguemos al
paso 10.

### El plan B, que además es mejor para verificar

NeilCooke, sobre un tangente que daba problemas: *«requires a lot of
calculation and therefore can sometimes be unpredictable»*.

Si el tangente se porta mal, **quítalo y conduce cada canal a mano**: pulsa
`J`, doble clic sobre el valor del revolute del seguidor, y teclea ψ.

Y esto no es una derrota, es mejor: **ψ lo calcula `core/cam/contacto.py`
apoyando el rodillo en el perfil cortado**, que es más exacto que lo que
Onshape va a deducir de un spline importado. El tangente sirve para ver la
máquina moverse de corrido; el ψ tecleado sirve para **comprobar**. Para la
comprobación de §6 hace falta el segundo de todas formas.

*(Esto último es recomendación propia, no de la documentación de Onshape.)*

---

## 6. Qué se verifica, y cómo

**Grados de libertad.** Bien montado, el conjunto entero queda con **uno**, el
del árbol. La cuenta: el árbol 1, los tres canales 3 más, los dos pivotes
atados por R1 y R2, el accionamiento atado por R3, el cinco barras cerrado
exactamente por M7+M8+M9, y los tres canales atados al árbol por M11–M13.
1 + 3 − 3 = 1.

Onshape **no lo va a decir con un número**: no hay contador de grados de
libertad, solo un icono de triedro por instancia y un icono de conjunto rígido
cuando todo está a cero y hay una pieza fija. La comprobación es arrastrar:
agarra una pieza cualquiera y mira si se mueve algo que no debería.

**Interferencias.** `Show analysis tools`, abajo a la derecha → *Interference
Detection*. Marca en rojo el solape de volumen entre las piezas seleccionadas.

**Y aquí está la parte que hay que hacer a mano.** La detección es **estática**:
mira la posición en la que está el conjunto ahora mismo, no durante el
movimiento. No existe detección continua ni parada al chocar. Así que el hueco
de 9,7 mm al poste —que es el límite de conjunto que decide qué frases caben,
y que ninguna envolvente de C3 ve— **se comprueba congelando θ y repitiendo**:

1. Pulsa `J` para ver los emparejamientos.
2. Doble clic sobre el valor de M1 y teclea θ.
3. Lanza *Interference Detection* sobre las tres levas y los tres postes.
4. Repite. Una rejilla de 24 posiciones (cada 15°) es lo razonable para una
   primera pasada.

El número continuo lo sigue dando `compile/conjunto.py`, y esto solo confirma
que el modelo dibujado dice lo mismo.

**Lo que Onshape no va a decir nunca:**

- El error de trazo, el ángulo de presión, el radio de curvatura, el par, la
  energía, la inercia del volante. Nada de eso existe aquí.
- Si la cinta se estira o el rodamiento tiene juego.
- Nada durante el movimiento: ni roces, ni choques.
- **Simulation no sirve para este conjunto.** Está excluido justo lo que lo
  mueve: los emparejamientos no soportados son *Tangent, Pin Slot, Parallel y
  Width*, y las relaciones no soportadas son *las cuatro*. El conjunto que se
  mueve no es simulable, y haría falta montar otro distinto, congelado, con
  emparejamientos soportados. (Y requiere plan Professional o Enterprise.)
- Los límites de emparejamiento (`Limits`) **no aceptan variables**. Un tope
  del contrato hay que teclearlo a mano, y por eso aquí no se usan: la
  geometría ya restringe lo que hay que restringir.

---

## 7. El orden en el que se monta

Cada paso deja algo comprobable. Si un paso no sale, el anterior sigue
sirviendo.

| | Qué | Qué se comprueba al terminarlo |
| --- | --- | --- |
| **1** | **Variable Studio** al día: los cinco mapas importados | `scripts/csv_pendientes.py` no dice nada |
| **2** | **Bastidor**: base FIJA, 3 postes, 3 platos, 4 rodamientos | Icono de conjunto rígido. Nada se arrastra |
| **3** | **Cartucho**: árbol, 3 levas, 2 separadores, pasador, rueda Z60 | El pasador atraviesa los tres taladros. Rígido |
| **4** | Nivel de arriba: bastidor (fijo) + cartucho + **M1** | Arrastra el cartucho: gira y nada más se mueve |
| **5** | **Canal** ×2 (izq. y der.) + canal elevador, **M2 M3 M4** | Arrastra un seguidor: bascula en su poste |
| **6** | **Pivote** ×2 (el derecho volteado), **M5 M6** | Arrastra un brazo proximal: gira en su pivote |
| **7** | **R1 R2**, ratio 6 | Arrastra el seguidor: el brazo le sigue **seis veces**. Comprueba el SENTIDO |
| **8** | Dos distales, **M7 M8**, y al final **M9 cilíndrico** | Arrastra un seguidor: la punta se mueve por la caja. Aquí sale el rojo (§4) |
| **9** | **Accionamiento** + **M10** + **R3** ratio 3 | Gira la manivela: el árbol va a un tercio y todo el varillaje le sigue |
| **10** | Curvas de paso + **M11 M12 M13** tangentes | Botón derecho sobre M1 → **Animate** → Play |
| **11** | Barrido de θ con *Interference Detection* | El hueco al poste (§6) |
| **12** | **Eje del balancín** en sus dos apoyos, con el balancín a 90° y la palanca; la **bieleta** del seguidor 3 al balancín | Arrastra el seguidor 3: el balancín le sigue y la palanca gira seis veces más |
| **13** | **Mesa** sobre sus cuatro bielas laterales; el **tirante** de la palanca al eje móvil trasero | Arrastra el seguidor 3: la mesa baja 3 mm sin girar y se corre 0,113 |
| **14** | **Punta** (tubo y horquilla) en los dos distales; **lápiz** en sus láminas | La mina toca el papel con la mesa arriba y queda a 3 con la mesa abajo |

**Solo un emparejamiento puede estar animado a la vez** en todo Onshape; el
resto se mueve por las relaciones. Ese emparejamiento es M1 y no otro: es el
árbol, que es de donde cuelga todo porque **todo programa es función de θ**.

Y conviene tener presente que de los pasos 1 a 9 sale una máquina que ya se
mueve entera salvo las levas. Los pasos 10 y 11 son los frágiles. Si hay que
parar en algún sitio, se para después del 9 y se conduce a mano (§5).

---

## 7 bis. El otro montaje: el que corre solo

Lo de arriba se monta a mano en Onshape y sirve para **verlo y
arrastrarlo**. En paralelo hay un montaje que no se toca con el ratón y
que hace lo que Onshape no puede: `emit/montaje.py` levanta los sólidos
de **todas** las piezas desde sus perfiles —las 32 de la plataforma y las
comerciales— y las coloca a partir de lo que calcula el compilador: el giro
de cada brazo, el del eje del balancín y lo que baja la mesa.

```
θ → core/ → ψ de cada seguidor → emit/montaje.py → sólidos en su sitio
                                        ↓
                         visor de VS Code  ·  barrido como test
```

**build123d no resuelve la cinemática, y no hace falta que lo haga.** Sus
articulaciones existen —`RevoluteJoint` y compañía— pero `connect_to()`
construye un árbol: coloca el hijo respecto del padre y no reconcilia dos
caminos que llegan al mismo sitio. El cinco barras es un lazo cerrado, el
contacto leva-rodillo no es una articulación y el cabestrante es una
relación entre dos giros: ninguno cabe. Y aunque cupieran, la cinemática
vive en `core/` por la regla 2.

**Lo que esto aporta y no aporta nada más:**

| | |
| --- | --- |
| Ver un sólido sin abrir el CAD | `scripts/ver.py`, en el visor de VS Code |
| Hueco al poste en TRES dimensiones, barriendo el ciclo | `compile.conjunto.barrer`, como test |
| Cerrar el lazo por su cuenta y decir si no cierra | **no** — eso solo lo hace Onshape |
| Arrastrar con el ratón | **no** |

El barrido es el **tercer camino** sobre el hueco de 9,7 mm: el plano lo
mide con la leva como un radio máximo y el poste como el círculo del
obstáculo; aquí se mide con el perfil entero, los sólidos de verdad y el
poste real de Ø8. Los dos coinciden en los 3,5 mm que separan los dos
radios, y no comparten una línea de código.

Y desde 2026-10-04 **el barrido ve los solapes**: una holgura negativa es
menos la raíz cúbica del volumen común, y `tests/emit/test_montaje.py`
recorre la máquina entera en doce ángulos sin más contactos que los dos
que lo son a propósito —el engrane, que se mete dos módulos, y la mina
sobre el papel—. Lo que encontró la primera vez está en `docs/contratos.md`:
proximales solapados, balancín dentro de la leva 3, volante atravesado por
el árbol, distales rectos cruzando el poste 3.

---

## 8. Lo que todavía no está cerrado

Desde 2026-10-04 todas las piezas tienen ficha, perfil, hoja, material y
proceso, y la máquina entera se monta y se mueve sin chocar en
`emit/montaje.py`. Lo que queda:

- **Onshape va por detrás**, por decisión: se saltó para cerrar la máquina
  en el repo. No están dibujadas las piezas nuevas ni las cambiadas
  (balancín girado, tambor en D, distal curvo, eje de pivote de 55, platina
  con los dos M3 de los apoyos). El STEP guardado de la platina lo dice en
  su test.
- **`base_al_plato` está ESTIMADO en 60**, y ya se sabe de qué depende: la
  pinza cuelga del plato 1 y tiene que apretar plástico liso, entre el agarre
  metálico y el clip del portaminas (`compile/portaminas.py`). Con el
  portaminas estimado la ventana va de 46 a 74 y se ha tomado el centro, para
  que la pieza real tenga sitio a los dos lados. Se afina midiendo el lápiz:
  `scripts/medir_portaminas.py` (sin `--estimado`), que reescribe a la vez la
  pinza, el plato 1, el poste y el tirante.
- **Precios**: `bench/precios.json` no tiene las piezas nuevas, así que el
  coste de la plataforma del informe se queda corto.
- **El portaminas sin medir**: cinco medidas con pie de rey —largo, cuerpo,
  fin del agarre, pie del clip y diámetro del agarre—. La pinza se taladra al
  cuerpo medido más 0,1, y el tubo de la punta (10,6 por dentro) tiene que
  dejarlo pasar.
- **La cinta del cabestrante y sus mordazas** no se colocan en 3D: su sitio
  sobre el sector lo dicen sus fichas.

---

## 9. Dónde las fuentes no cierran

Lo que he dado arriba como cierto y **no** está verificado:

| Asunto | Estado |
| --- | --- |
| Grados de libertad del tangente | **No documentado** en ninguna página de Onshape |
| Qué relación lleva `Reverse` marcada | Depende del convenio interno; se comprueba mirando |
| Que un cilíndrico baste para este lazo plano | Es lo que recomienda el personal de Onshape y lo que funcionó en cuatro hilos; el plan B del esférico es razonamiento propio |
| Que `Replicate` conserve el TIPO de emparejamiento | No verificado. Por eso aquí no se usa: el canal se inserta dos veces y se ponen dos revolutes a mano |
| Campos exactos del diálogo `Animate` | Solo `Steps` está confirmado por personal de Onshape en el foro |
| `Interference Detection` durante una animación | La ayuda no se pronuncia; todo lo demás apunta a que no |

---

## Fuentes

**Ayuda oficial** — [Mates](https://cad.onshape.com/help/Content/Assembly/mates.htm) ·
[Revolute](https://cad.onshape.com/help/Content/Assembly/revolute_mate.htm) ·
[Cylindrical](https://cad.onshape.com/help/Content/Assembly/cylindrical_mate.htm) ·
[Ball](https://cad.onshape.com/help/Content/Assembly/ball_mate.htm) ·
[Tangent](https://cad.onshape.com/help/Content/mate-tangent.htm) ·
[Group](https://cad.onshape.com/help/Content/Assembly/group.htm) ·
[Relations](https://cad.onshape.com/help/Content/Assembly/relations.htm) ·
[Gear Relation](https://cad.onshape.com/help/Content/Assembly/gear_relation.htm) ·
[Mate Connector](https://cad.onshape.com/help/Content/PartStudio/mate_connector.htm) ·
[Instances List](https://cad.onshape.com/help/Content/Assembly/instances_list.htm) ·
[Replicate](https://cad.onshape.com/help/Content/replicate.htm) ·
[Interference Detection](https://cad.onshape.com/help/Content/View/interference_detection.htm) ·
[Simulation](https://cad.onshape.com/help/Content/Assembly/simulation.htm) ·
[Performance Considerations](https://cad.onshape.com/help/Content/Home/performance_considerations.htm) ·
[Modeling In-Context](https://cad.onshape.com/help/Content/in-context.htm)

**Blog y resource center de Onshape** —
[Assemblies, Mates, and Simulation](https://www.onshape.com/en/blog/kinematics-assemblies-mates-simulation) ·
[Advanced Mating Techniques for Sliding Motions](https://www.onshape.com/en/resource-center/tech-tips/advanced-mating-pin-slot-tangent-mate) ·
[Positioning Parts Based on Mate Values](https://www.onshape.com/en/resource-center/tech-tips/precisely-position-mates) ·
[Multi-Part Part Studios vs. Assemblies](https://www.onshape.com/en/resource-center/tech-tips/multi-part-studio-vs-assembly)

**Foro, respuestas de personal de Onshape** —
[Last revolute in a chain overdefines the assembly](https://forum.onshape.com/discussion/20736/last-revolute-in-a-chain-overdefines-the-assembly) ·
[Revolute mate over defining the assembly in a linkage](https://forum.onshape.com/discussion/22053/revolute-mate-over-defining-the-assembly-in-a-linkage) ·
[Fairly new here, need help with mates and overdefined assemblies](https://forum.onshape.com/discussion/13633/fairly-new-here-need-help-with-mates-and-overdefined-assemblies) ·
[Why is this overdefined?](https://forum.onshape.com/discussion/25634/why-is-this-overdefined-is-there-a-better-way) ·
[Dealing with subassemblies in an assembly](https://forum.onshape.com/discussion/22027/dealing-with-subassemblies-in-an-assembly) ·
[How to make these parts interact with each other](https://forum.onshape.com/discussion/9014/how-to-make-these-parts-interact-with-each-other-in-assembly)

**Foro, comunidad** —
[How do you use and animate mates?](https://forum.onshape.com/discussion/23139/how-do-you-use-and-animate-mates) ·
[Can't get pin to follow slot correctly at all](https://forum.onshape.com/discussion/19646/cant-get-pin-to-follow-slot-correctly-at-all) ·
[How can I get the cam to work the whole way round?](https://forum.onshape.com/discussion/23496/how-can-i-get-the-cam-to-work-the-whole-way-round) ·
[Mates: Geneva Mechanism](https://forum.onshape.com/discussion/18614/mates-geneva-mechanism) ·
[Slider mate limits from variables](https://forum.onshape.com/discussion/comment/118373) ·
[Motion diagram](https://forum.onshape.com/discussion/20256/motion-diagram) ·
[Subassembly in top level has errors](https://forum.onshape.com/discussion/30482/subassembly-in-top-level-has-errors-but-at-the-subassembly-there-are-none-how-do-i-diagnose)
