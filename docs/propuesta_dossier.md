# Propuesta · la documentación completa: numeración, explosión, índice, estilo y fichas dibujables

2026-10-05 · estado: **aprobada; fases 1 a 6 hechas**; de la 6 quedan seis decisiones de diseño en `propuesta_tornilleria.md`

Dos encargos que se juntan aquí: el bloque B del dossier (numeración única,
explosión de conjunto, índice, escala y estilo) y que **cada ficha de pieza
sirva para dibujarla desde cero en cualquier CAD**. El bloque A ya está hecho
(commit 0810a59) y el codo también (este mismo turno).

La documentación completa es un **conjunto**, con una numeración y un estilo:

| Documento | Qué lleva | Escala |
| --- | --- | --- |
| `dossier.pdf` | índice, explosión de conjunto, despiece numerado, secuencia de montaje | libre |
| `fichas_<grupo>.pdf` | hoja de grupo + ficha de cada pieza, con su marca | normalizada, por hoja |
| `plantillas.pdf` | 1:1, aparte, intocable | 1:1 |
| `patron.pdf` | 1:1, aparte, intocable | 1:1 |

Plantillas y patrón no se funden con nada: `escribir_pdf` ya se niega a un
documento con dos escalas.

---

## 1. La numeración: una declaración, un registro, un golden

**De dónde sale.** De un archivo versionado, `docs/numeracion.json`, que es la
**única** fuente. No se calcula al generar: se lee.

```json
{"grupos": {
  "amplificador": {"sigla": "AMP", "piezas": {"1": "eje_pivote", "2": "calzo_sector",
     "3": "tambor", "4": "sector", "5": "mordaza"},
   "comerciales": {"1": "DIN 912 M3 × 16", "...": "..."}},
  ...}}
```

- **Dos niveles**: grupo (sigla declarada, no `nombre[:3]`: `levas` y
  `levantamiento` darían las dos «LEV») y marca dentro del grupo.
- Códigos derivados del registro y de nada más: plano `P-AMP-03`, comercial
  `C-AMP-02`, hoja de grupo `G-AMP`.
- **Las marcas no se reutilizan ni se reordenan.** Una pieza nueva entra con
  la siguiente marca libre de su grupo; una que se va deja su número dado de
  baja (`"7": null`). Así meter una pieza no renumera a las demás, y un
  dossier renumerado no es un dossier reimpreso.
- Lo leen **todos**: la explosión, las tablas de fabricadas, comerciales y
  tornillería (columnas de marca y plano en las tres), el índice y las fichas.

**El golden** (`tests/golden/test_numeracion.py`): se comparan las piezas
que existen (`LISTADO`, catálogo comercial, tornillería) con el registro.

- Una pieza sin número falla con **«ALTA: grupo, pieza → marca libre n»**, y
  `scripts/numeracion.py --alta` la añade al registro, que se revisa en el
  diff como cualquier dato.
- Un número que cambia de pieza falla diciendo **cuál**.
- Una pieza del registro que ya no existe falla con «BAJA».

## 2. La explosión: declarada, no ajustada a ojo

**De cada grupo.** Cada `Grupo` declara en `emit/montaje.py`:

```python
explosion = Explosion(eje=(0, 0, 1), separacion=14.0, orden="montaje")
```

- `eje`: la dirección en que se monta el grupo. Es un dato del montaje (los
  seguidores, el amplificador y el cartucho se enhebran en vertical; el
  levantamiento, hacia la mesa).
- `separacion`: mm entre una pieza y la siguiente.
- `orden`: el de la secuencia de montaje, que sale de la marca (§1).

El desplazamiento de cada pieza es `orden × separacion × eje`: no hay ningún
número puesto mirando. Hoy la del amplificador ya es así, con su orden por
altura; se generaliza a los diez grupos y se comprueba que existe en todos.

**De conjunto** (página nueva del dossier). Cada grupo se desplaza como un
bloque, de su centro hacia fuera del centro de la máquina, con
`separacion_conjunto` declarada por grupo; color y código de grupo.

> **Hecho así (fase 4).** Las declaraciones viven en `emit/explosion.py`
> (`EXPLOSIONES`), no en `Grupo`: el montaje no tiene por qué saber de
> dibujo. De conjunto se declara solo la **dirección** (`eje_conjunto`); la
> distancia se deriva: la menor, en pasos de 2 mm, a la que la caja del
> bloque en la isométrica queda a 12 mm de los ya colocados. Se imprime en
> una tabla al pie de la página. En la hoja de grupo, el globo apunta al
> punto dibujado de la pieza más cercano al centro de su caja (el centro a
> secas cae en el hueco de una U). Tests en `tests/emit/test_explosion.py`.

**Que no se pisen.** Se mide, como
`test_dos_rotulos_de_la_banda_de_arriba_no_se_tapan`: cajas de los bloques
explosionados que no se solapan, y globos que no se solapan entre sí ni tapan
la pieza que describen (caja del globo contra la caja de la proyección de su
pieza). Mirar el dibujo no lo caza.

## 3. El índice

Una página al principio del dossier: marca, nombre, grupo, cantidad,
material o designación, paso de montaje y **en qué documento y página** está
su ficha. Ordenado por marca, y una segunda tabla alfabética que remite a la
primera. Los números de página salen de cómo se escriben las fichas (cada
`escribir_fichas` devuelve el mapa pieza → página), no se cuentan aparte.

> **Hecho así (fase 5).** `emit.numeracion.paginas(registro)` da documento
> y hoja de cada marca, en el mismo orden en que escribe
> `emit.fichas.escribir_fichas` (`hojas_de`): hoja 1 la de grupo, con
> comerciales y tornillería; después una por pieza, por marca; una baja no
> deja hoja vacía. Un test lo cruza con lo que de verdad lleva escrito cada
> hoja de los nueve grupos con piezas. El índice va en la página 2 del
> dossier. Remite a `fichas_levas.pdf` para la plancha de POM: esa hoja de
> grupo la escribe la fase 6.

## 4. Escala y medida

En el cajetín de toda hoja a escala libre o normalizada, junto a la escala:
**«No medir sobre esta hoja: para cortar, plantillas.pdf»**. Las isométricas
siguen «sin escala». La hoja de grupo deja de decir «Escala -»: dice «varias,
sin escala».

## 5. Un solo estilo

`emit/estilo.py`: grosores, colores de subsistema (hoy en `GRUPOS`),
tipografía y cuerpos, cajetín y pie. Lo leen el dossier, las fichas y las
hojas SVG de `scripts/`. **Los nombres de variable salen del dibujo y se
quedan en la tabla**, que es donde se leen para teclear: a 4,6 pt no se leen
impresos y cruzan las líneas de cota. En el dibujo cada cota lleva una
**referencia corta**, el número de fila de la tabla de variables
(«22 ⑤»), que se lee y no estorba.

## 6. Fichas dibujables

### La causa raíz, comprobada

`scripts/acotar.py` tiene `cota_h`, `cota_v`, `radial`, `arco` y `auxiliar`, y
ninguna cota angular. Y `emit/fichas.py` tiene la misma carencia, por su
cuenta: son **dos sistemas de acotado**, uno en SVG y otro en PDF. Se propone
uno solo (§5): las primitivas de cota como **dato** (líneas, arcos, flechas y
textos en mm de la hoja), y dos salidas, SVG y PDF.

### Lo que contabas, comprobado

| Punto | ¿Es así? |
| --- | --- |
| 1. La cara plana no se dibuja | **No del todo:** se dibuja (la planta del tambor enseña el agujero en D), pero **no se acota**: ni la distancia de 4, ni la cuerda de 6, ni de qué lado. Lo que dices de la cuerda es exacto: no sitúa la cara. |
| 2. Cotas del dibujo sin variable | Sí. El 53,5 del calzo no tiene variable; el 22 sí desde el bloque A (`calzo_sector_cubo_diametro`). |
| 3. Entre-centros por coincidencia | Sí: el centro del R4,5 del calzo solo se sitúa porque coincide con el taladro C. |
| 4. No se dice cómo se construye el contorno | Sí: nada dice «tangente». |
| 5. El eje no dice en qué tramo va la cara plana | Sí: solo se deduce del alzado. |

### El cruce, ya medido

`scripts/dibujable.py` cruza el perfil de cada pieza (la lista de `Arco` y
`Segmento` que va al DXF) con lo que su ficha acota hoy. **68 faltas** en las
44 piezas con perfil (las dos nuevas del codo, el perno y el casquillo, salen sin faltas):

| Grupo | Faltas | Piezas con faltas |
| --- | ---: | --- |
| levantamiento | 19 | palanca_lapiz 6, balancin 6, biela_mesa 5, eje_balancin 2 |
| amplificador | 11 | mordaza 4, calzo_sector 4, eje_pivote 2, tambor 1 |
| cinco_barras | 11 | brazo_proximal 6, brazo_distal 5 |
| accionamiento | 9 | manivela 6, eje_manivela 2, volante 1 |
| seguidores | 8 | seguidor 4, placa_tope 4 |
| cartucho | 5 | eje_cartucho 5 |
| portalapiz | 5 | brazo_horquilla 5 |
| bastidor, entre_puntos | 0 | |

Por clase: 20 tramos rectos sin longitud ni tangencia, 17 arcos con el centro
sin situar o situado por coincidencia, 22 cotas del dibujo sin variable y 9
caras planas sin sus tres datos. La lista completa del amplificador:

- mordaza: los dos arcos R2 de la ranura sin su centro situado (7 y 13 del datum); sus dos tramos de 6 sin longitud.
- eje_pivote: la cara plana sin sus tres datos; el ancho de 9 sin variable.
- tambor: la cara plana sin sus tres datos.
- calzo_sector: los dos tramos tangentes de 37,4 sin declarar; el centro del R4,5 situado por coincidencia; el 53,5 sin variable.

(El bastidor y entre_puntos salen a cero porque sus piezas son discos y
anillos concéntricos: lo que acota la ficha basta.)

### El plan para cerrarlo

1. **El perfil dice cómo se construye.** Los generadores (`barra`,
   `agujero_en_d`, `ranura`…) ya lo saben; que lo dejen escrito: `Segmento`
   con `tangente_a=(arco, arco)` y `Arco` con la variable que sitúa su
   centro. El perfil pasa a ser la fuente de las cotas, no solo del contorno.
2. **Primitiva de cota angular**, en el acotado único: dos líneas de
   referencia, el arco de cota, la flecha y el rótulo en grados, con su
   variable y el gemelo en positivo cuando el ángulo es negativo.
3. **Cada rasgo con su cota, de su variable:** entre-centros acotado como tal
   aunque coincida con otro número; caras planas con distancia, cuerda y
   ángulo con signo (o el lado, rotulado); el tramo de la cara plana en los
   ejes, en el alzado.
4. **Las cotas derivadas, de referencia.** El 53,5 es 11 + 38 + 4,5: se
   dibuja entre paréntesis, «(53,5)», que en dibujo técnico es una cota de
   referencia que no se fabrica, y queda fuera del cruce con el CSV.
5. **El test que lo cierra**: el cruce de `scripts/dibujable.py` pasa a test
   leyendo la ficha generada, no las variables que la generan, y entra en el
   cruce hoja–CSV junto a las hojas de bocetos. Cero faltas en los diez
   grupos.

---

## Lo hecho

- **Fase 1** (5f2c98c): `docs/numeracion.json`, 84 marcas, golden de altas y bajas; marca y plano en las tres tablas del dossier y en las fichas.
- **Fase 2** (853024b): `emit/acotado.py` con cota angular, `emit/estilo.py`, «no medir sobre esta hoja», referencias numeradas en vez de nombres en el dibujo.
- **Fase 3**: `emit/dibujable.py` lee del perfil cómo se construye la pieza (tangentes, caras planas, tramos libres) y la ficha rotula lo que falta: centros de arco con su propia cota, caras planas con distancia, cuerda y lado, longitudes de tramos libres, cotas derivadas de referencia entre paréntesis y la nota de extrusión. **De 68 faltas a 0** en los nueve grupos con piezas; `tests/emit/test_dibujable.py` lo cruza y busca cada cota en el PDF.

## Fases

| Fase | Qué | Toca |
| --- | --- | --- |
| **1** | `docs/numeracion.json` + golden de altas y bajas + columnas de marca y plano en las tres tablas del dossier | dossier, fichas |
| **2** | Acotado único con cota angular (SVG y PDF) + `emit/estilo.py` + «no medir sobre esta hoja» + variables fuera del dibujo | todas las hojas |
| **3** | Perfiles que dicen cómo se construyen + fichas dibujables + el cruce como test, primero el amplificador y luego los diez grupos | fichas, plataforma |
| **4** | `Explosion` declarada por grupo + explosión de conjunto + test de globos y bloques | dossier, montaje |
| **5** | Índice con documento y página | dossier |
| **6** | Fichas de los diez grupos, y la tornillería dibujada que quedó del codo | todo |

> **Hecho así (fase 6).** `scripts/dossier_completo.py` escribe en
> `dossier/`, en la raíz, el dossier, las fichas de los diez grupos (las
> levas, con su hoja de grupo sin despiece: son de cada pedido), los
> informes de numeración y de fichas dibujables, y `INDICE.md` con cada
> comando y lo que produce. La tornillería, las 26 líneas y 72 piezas,
> está en 3D (`emit/fijaciones.py`, `emit.montaje`); cada línea dice qué
> pieza la dibuja y un test lo cuenta. Lo que no cabe espera decisión en
> `propuesta_tornilleria.md`.

Cada fase acaba con lint, mypy, `uv run --group cad pytest`, commit y push, y
los PDF idénticos byte a byte con la misma entrada.

**Lo que decido yo si no se dice otra cosa:** las marcas se asignan una vez,
por el orden de montaje de hoy, y se congelan en el registro; la referencia
corta bajo cada cota es el número de fila de la tabla de variables.
