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
| A2 | amplificador | **Recortar el sector no resolvía A1.** Hacia fuera de la base, cada sector apunta a unos 91° de la dirección de su tambor, que cae justo en el arco donde trabaja la cinta (de 54° a 140°). Ahí hace falta el R48 entero, porque la relación 6:1 es R48/R8. Lo que sí sobra es el arco de detrás de los 140° y el de delante de los 54°. Recortarlos quitaría inercia y latón, pero no ganaría planta. | cálculo de la dirección del tambor en `docs/auditoria_conjunto.md` | abierto, optimización (fase 5) |
| A3 | cinco_barras / entre_puntos | El proximal 1 pasa a **3,1 mm** del pie del muñón; la holgura mínima es 3. Es lo primero que tocará si el varillaje tiene juego vertical. | barrido de la máquina | abierto, a medir en banco |
| A4 | seguidores | En el ciclo, el seguidor queda a **0,6 mm** de su pasador de tope. Al orientar el collar a mano, cada grado de error mueve el tope 0,3 mm. **Hace falta una plantilla de orientación**. | barrido; `tope_angulo` | abierto, fase 5 |
| A5 | entre_puntos | Al deslizar el cartucho, el muelle de la garra aprieta la lengüeta contra el fondo de la ranura. **El muelle no está especificado**: hay que elegirlo blando, unos 5 N. | `muelle_garra` es un tubo modelado | abierto |
| A6 | amplificador | **La cinta y sus cuatro mordazas no están en el 3D**, así que el barrido no las ve. | docstring de `colocar` | abierto |
| A7 | todos | **La tornillería no está modelada**, salvo los ejes de los rodillos. | — | abierto |
| A8 | portalapiz | El portaminas y `base_al_plato` siguen **ESTIMADOS**, a la espera del ejemplar real. | `scripts/medir_portaminas.py` | abierto |

### De desarrollo y fabricación

| # | Hallazgo | Evidencia | Estado |
| --- | --- | --- | --- |
| D1 | **41 piezas fabricadas, 26 materiales y 30 procesos.**<br>• Latón en 4 espesores de chapa (2, 3, 4 y 6), 5 barras distintas y 3 tubos.<br>• Acero en 5 diámetros.<br>Cada espesor o diámetro de más es otro pedido y otra preparación de máquina. | `LISTADO` | abierto, fase 5 |
| D2 | La barra W10 h6 aparece con **dos nombres** («acero W10 h6 rectificado» y «barra W10 h6 rectificada»). Es el mismo material y tiene que salir en la lista de compra una vez. | `LISTADO` | abierto, fase 5 |
| D3 | Siguen **sin precio**:<br>• el cubo, la garra y su muelle;<br>• los collares y la placa de tope;<br>• los muelles de torsión (estimado);<br>• los separadores (estimado). | `bench/precios.json` | abierto, fase 5 |
| D4 | **No existe el dossier de montaje**. Debería traer el procedimiento de cambio de cartucho, la fase cero y la orientación de los collares. | `emit/dossier.py` vacío | abierto, fase 5 |
| D5 | El gemelo de Onshape va por detrás, por decisión de proyecto: se valorará al final. | memoria del proyecto | aplazado |

## Cómo seguir

Cada hallazgo se cierra con un **test que lo habría cazado**, no solo con el
arreglo. El caso de A1 lo muestra: el test existía y miraba mal.
