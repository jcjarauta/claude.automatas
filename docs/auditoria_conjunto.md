# Auditoría de conjunto y desarrollo

Abierta el 2026-10-04. Es el punto de partida, no un cierre. Se audita **por
subsistemas**. Los subsistemas están en `emit/montaje.py` (`GRUPOS`), y un
test exige que toda pieza colocada caiga en exactamente uno.

## Cómo mirarla

```bash
uv run --group cad python scripts/ver.py --conjunto                         # isométrica, por grupos
uv run --group cad python scripts/ver.py --conjunto --vista planta
uv run --group cad python scripts/ver.py --conjunto --sacado 90 --vista atras   # cambio de cartucho
uv run --group cad python scripts/ver.py --conjunto --grupos cartucho,entre_puntos,seguidores
```

- La máquina se ve **a escuadra con la base**: la mesa delante (−Y) y la
  salida del cartucho detrás (+Y).
- Cada grupo tiene un color y el bastidor va translúcido.
- En el árbol del visor cada grupo es un nodo con sus piezas dentro.
- El script imprime esta tabla.

| Grupo | Color | Piezas | Móviles | Objetivo |
| --- | --- | ---: | ---: | --- |
| bastidor | gris translúcido | 12 | 0 | Lo que no se mueve: base, postes, platos y rodamientos |
| cartucho | naranja | 8 | 8 | Lo que se cambia en cada pedido: las levas y lo que las enhebra |
| entre_puntos | azul | 6 | 6 | Lo que sujeta, arrastra y pone en fase el cartucho |
| accionamiento | morado | 6 | 6 | La manivela, el volante y el reductor 3:1 |
| seguidores | verde | 21 | 12 | Lo que lee las levas: seguidores, rodillos, sus ejes, topes y muelles |
| amplificador | amarillo | 6 | 6 | El cabestrante 6:1: sectores, tambores y ejes de pivote |
| cinco_barras | rojo | 4 | 4 | El brazo que lleva la punta por el papel |
| levantamiento | cian | 26 | 16 | Del seguidor 3 a la mesa: balancín, bieleta, tirante y mesa |
| portalapiz | rosa | 7 | 7 | La punta: tubo, horquilla, pinza, láminas y portaminas |
| **total** | | **96** | **65** | |

## Hallazgos

Estado: **abierto**, **en curso** o **cerrado**. La fase es la de
`docs/propuesta_cartucho.md` donde toca resolverlo.

### De conjunto

| # | Grupo | Hallazgo | Evidencia | Estado |
| --- | --- | --- | --- | --- |
| A1 | amplificador | **Los sectores se salían de la base 14,5 mm por cada lado.** Son discos enteros de R48 y la base medía 190. El test que tenía que verlo comparaba cajas en el marco de la leva, con la base girada, y pasaba. **Resuelto: la base pasa a 240.** La regla de los 10 mm de nogal alrededor de todo se había aplicado al plato, y lo que manda a los lados son los sectores. De paso, el pomo de la manivela, que se salía 19 mm, queda 6 mm dentro. Coste: +5,08 € de nogal (estimado). | `test_la_caja_envolvente_del_montaje_cabe_en_la_base`, a escuadra y sin `xfail`; `test_la_base_deja_diez_milimetros_de_nogal_alrededor_de_todo` mide contra el sector | **cerrado** 2026-10-04 |
| A2 | amplificador | **¿Recortar los sectores? No se hace** (y ya lo decía `docs/contratos.md`: «la muesca de 80° en el lado libre no compraba nada»). La cinta es una correa abierta con una sola mordaza en el sector, y lo abraza **252° por detrás**, de una tangencia (+54° desde el tambor) a la otra (−54°). Lo único que no toca es una cuña de ±40° **mirando al tambor**, y en esa cuña van los dos tornillos al seguidor (a 22 y 38 sobre el brazo, que queda a 24,8° y a −15,7° del tambor).<br>• **Lo que ganaría:** quitando todo lo que se puede, 8,8 g de POM por sector y un 19,5 % de su inercia; en la dinámica, unos 0,4 mN·m frente a los 50 de precarga del muelle.<br>• **Lo que costaría:** los dos sectores dejarían de ser la misma pieza (×2), porque el tambor cae a un lado distinto del brazo en cada uno, y el recorte quedaría partido en dos por la tira de los tornillos.<br>(Corrige lo que se dijo al cerrar A1, que «sobraba el arco de detrás de los 140°»: los 140° se cuentan desde atrás, y lo de detrás trabaja entero.) | cálculo con la geometría del contrato: tangencia `amplificador_tangencia`, abrazado 252,06° (`docs/contratos.md`, cabestrante) | **cerrado: no se hace** 2026-10-04 |
| A3 | cinco_barras / entre_puntos | El proximal 1 pasa a **3,1 mm** del pie del muñón; la holgura mínima es 3. Es lo primero que tocará si el varillaje tiene juego vertical. | barrido de la máquina | abierto, a medir en banco |
| A4 | seguidores | En el ciclo, el seguidor queda a **0,6 mm** de su pasador de tope. Al orientar el collar a mano, cada grado de error mueve el tope 0,3 mm. **Resuelto con el cartucho de calibrar**: tres discos redondos al radio de diseño que dejan cada seguidor en su punto de diseño. Con él puesto, se gira el collar hasta que entra justa una **galga de 1,20** (`tope_galga`, derivada del hueco en reposo, 1,205) y se aprieta. El mismo cartucho sirve para calar los brazos. | `compile/calibrar.py`, `tests/compile/test_calibrar.py`, `docs/procedimientos.md` | **cerrado** 2026-10-04 |
| A5 | entre_puntos | El muelle de la garra estaba sin especificar, y su fuerza es la que hace rozar la lengüeta al deslizar el cartucho. **Especificado blando**: compresión de 0,8 × Di 11,6 × L0 20, k = 0,61 N/mm, 4,9 N montado y 7,9 N con la garra levantada. Tensión 530 MPa. De catálogo o a medida, sin presupuesto todavía. | `docs/piezas/muelle_garra.json`, `bench/precios.json` | **cerrado** 2026-10-04 (falta el precio: D3) |
| A6 | amplificador | **La cinta y sus mordazas no estaban en el 3D.** Ahora entran, con la trayectoria recalculada en cada estado: tangentes exteriores, 252° abrazados al sector y el lado lejano del tambor. **Al meterlas aparecieron tres cosas:**<br>• la tuerca del eje del rodillo izquierdo cortaba la cinta (−0,69): su seguidor es el más largo y asoma bajo el tramo recto;<br>• la cinta rozaba los seguidores que cruza (holgura 0), porque el sector iba directo sobre el seguidor;<br>• en el tambor no cabía una mordaza, y el contrato dejaba ese anclaje «por cerrar».<br>**Resuelto:** calzo de latón de 3 bajo el sector; ejes de rodillo avellanados desde arriba con la tuerca debajo; los dos extremos de la cinta solapados bajo un M2 radial en el tambor; una mordaza por sector (eran 4, son 2). | barrido: cada cinta toca su sector y su tambor en todo el ciclo y nada más; sin solapes nuevos | **cerrado** 2026-10-04 |
| A7 | todos | **La tornillería no estaba en el 3D ni en la lista de compra**, salvo los ejes de rodillo. Ahora:<br>• En el 3D, la de la zona que se mueve: los dos M3 sector–calzo–seguidor con sus tuercas, y el M4 de la mordaza.<br>• **El sector no tenía agujero para la mordaza.** Ahora lleva dos, uno por canal (r 43,08 a −151,18° y +168,26°, derivados y atados por su test), y sigue siendo la misma pieza ×2.<br>• **Nada fijaba los platos a su altura en los postes.** Ahora van apretados entre collares con prisionero, la misma pieza que sostiene los seguidores (18 en total). El plato 3 no lleva collar encima porque ahí está el volante: lo sujeta un M3 avellanado en la punta roscada del poste.<br>• La lista de tornillería y retención, por norma y medida, sale de las cantidades del listado: 79 piezas, frente a las 20 genéricas que contaba el precio. | `emit/materiales.py` (`tornilleria()`), `docs/materiales.md`; tests: el montaje coloca lo que dice el listado, y el precio cuenta lo que dice la lista | **cerrado** 2026-10-04 |
| A8 | portalapiz | El portaminas y `base_al_plato` siguen **ESTIMADOS**, a la espera del ejemplar real. | `scripts/medir_portaminas.py` | abierto |
| A9 | levas | **Capacidad de tinta por vuelta.** «Hola Mundo» con florituras (`demo/hola_mundo.json`, generado por `scripts/escritura_hola_mundo.py`) **no es fabricable**: la leva izquierda se socava.<br>• La exigencia sobre la leva crece con el **cuadrado de la tinta por grado** y con la **inversa del radio de cada giro** de la letra.<br>• Los pedidos que caben llevan de 60 a 141 mm de tinta, con giros de 1 mm o más. «Hola Mundo» en cursiva lleva unos 450 mm, con giros de 0,2–0,5 mm, porque la caja de 80 la escala a una x de 7,6 mm. Hasta una sola palabra cursiva (unos 310 mm) queda en el límite.<br>• **Lo agrava la pila escalonada**: el canal izquierdo se socava cuando la segunda derivada del giro supera radio base / brazo = 39,6 / 59 = 0,67, frente a 1,22 del elevador. Es casi el doble de sensible.<br>• Probado sin éxito: redondear esquinas (de 1 a 4 mm), suavizar el trazo (σ hasta 3 mm), caja más pequeña (hasta 32 × 12), rodillo R2,5 y relación 8 y 10. La relación 8 mejora el radio un 30 %, a costa de un peor caso en la punta un 25 % mayor.<br>**Decisión pendiente:** una palabra por cartucho («un párrafo son varios cartuchos») en una cursiva redondilla de giros amplios y florituras grandes y suaves; o una cota de tamaño de letra en el pedido; o una máquina con más capacidad. | `tests/compile/test_hola_mundo.py` fija que hoy se rechaza | abierto |

### De desarrollo y fabricación

| # | Hallazgo | Evidencia | Estado |
| --- | --- | --- | --- |
| D1 | **41 piezas fabricadas y 26 materiales.** Bajan a **22**: unificada la barra W10, las pletinas de latón pasan a chapa del mismo espesor (cortada a láser junto con lo demás) y el collar se tornea de la barra de Ø16 de tambor y garra. Quedan 4 espesores de chapa de latón (2, 3, 4 y 6). Bajar el de 4 (soporte de mesa y poste de horquilla) a 3 o a 6 obliga a recalcular sus piezas, y se deja para cuando se dibujen. | `emit/materiales.py`, `docs/materiales.md` (generado, con test) | en curso |
| D2 | La barra W10 h6 aparecía con **dos nombres**. Resuelto: cada pieza remite a una entrada de `STOCK`, y un test lo exige. | `tests/emit/test_materiales.py` | **cerrado** 2026-10-04 |
| D3 | Siguen **sin precio**:<br>• el cubo, la garra y su muelle;<br>• los collares y la placa de tope;<br>• los muelles de torsión (estimado);<br>• los separadores (estimado). | `bench/precios.json` | abierto, fase 5 |
| D4 | **No existía el dossier de montaje.** Ahora es `emit/dossier.py` y se genera con `scripts/dossier.py` en `build/fab/dossier.pdf`: 13 páginas en A4.<br>• Portada con la isométrica por subsistemas y su leyenda.<br>• Planta, frente y perfil.<br>• Despiece: fabricadas, comerciales y tornillería.<br>• Secuencia de montaje en 9 pasos: cada uno dibuja la máquina hasta ahí con lo nuevo en su color, y lleva el texto de montaje de sus fichas.<br>• Procedimientos, leídos de `docs/procedimientos.md`.<br>• Hoja de comprobación final.<br>Es vectorial y sale igual byte a byte. **Primera versión**: se irá afinando. Al leerlo apareció un texto viejo (la platina hablaba de «separadores de la base»), corregido. | `tests/emit/test_dossier.py` | **cerrado** (v1) 2026-10-04 |
| D5 | El gemelo de Onshape va por detrás, por decisión de proyecto: se valorará al final. | memoria del proyecto | aplazado |

## Cómo seguir

Cada hallazgo se cierra con un **test que lo habría cazado**, no solo con el
arreglo. El caso de A1 lo muestra: el test existía y miraba mal.
