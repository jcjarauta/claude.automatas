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
| A6 | amplificador | **La cinta y sus cuatro mordazas no están en el 3D**, así que el barrido no las ve. | docstring de `colocar` | abierto |
| A7 | todos | **La tornillería no está modelada**, salvo los ejes de los rodillos. | — | abierto |
| A8 | portalapiz | El portaminas y `base_al_plato` siguen **ESTIMADOS**, a la espera del ejemplar real. | `scripts/medir_portaminas.py` | abierto |

### De desarrollo y fabricación

| # | Hallazgo | Evidencia | Estado |
| --- | --- | --- | --- |
| D1 | **41 piezas fabricadas y 26 materiales.** Bajan a **22**: unificada la barra W10, las pletinas de latón pasan a chapa del mismo espesor (cortada a láser junto con lo demás) y el collar se tornea de la barra de Ø16 de tambor y garra. Quedan 4 espesores de chapa de latón (2, 3, 4 y 6). Bajar el de 4 (soporte de mesa y poste de horquilla) a 3 o a 6 obliga a recalcular sus piezas, y se deja para cuando se dibujen. | `emit/materiales.py`, `docs/materiales.md` (generado, con test) | en curso |
| D2 | La barra W10 h6 aparecía con **dos nombres**. Resuelto: cada pieza remite a una entrada de `STOCK`, y un test lo exige. | `tests/emit/test_materiales.py` | **cerrado** 2026-10-04 |
| D3 | Siguen **sin precio**:<br>• el cubo, la garra y su muelle;<br>• los collares y la placa de tope;<br>• los muelles de torsión (estimado);<br>• los separadores (estimado). | `bench/precios.json` | abierto, fase 5 |
| D4 | **No existe el dossier de montaje**. Ya están escritos los procedimientos que tiene que llevar: orientar los collares, calar los brazos, cambiar el cartucho y comprobar la fase cero. Falta el PDF con sus vistas. | `docs/procedimientos.md`; `emit/dossier.py` sigue vacío | en curso |
| D5 | El gemelo de Onshape va por detrás, por decisión de proyecto: se valorará al final. | memoria del proyecto | aplazado |

## Cómo seguir

Cada hallazgo se cierra con un **test que lo habría cazado**, no solo con el
arreglo. El caso de A1 lo muestra: el test existía y miraba mal.
