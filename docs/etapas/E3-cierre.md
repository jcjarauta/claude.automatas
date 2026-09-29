# Cierre de etapa E3 · Plantilla en papel
Fecha: 2026-09-29

## Entregable
El primer recorrido completo de digital a físico, por la vía más barata: un
PDF a escala 1:1 que se imprime en una copistería, se pega sobre el tablero y
se corta a mano o con sierra de cinta. Sin láser en el camino crítico.

- `emit/pieza.py` — `Pieza` con sus siete metadatos obligatorios, taladros,
  referencias y marca de fase. La comparten los tres emisores.
- `emit/layout.py` — maquetación en milímetros: cuadro de calibración,
  cabecera, colocación, troceado con solape y marcas de registro, y modo de
  hoja única para plóter.
- `emit/template.py` — escritura del PDF. Capa fina: recibe milímetros ya
  resueltos y solo los pasa a puntos.
- `scripts/plantillas_demo.py`, `scripts/regenerar_golden.py`.

## Verificación automática
Comando: `uv run ruff check . && uv run ruff format --check . && uv run mypy core compile && uv run pytest`
Resultado: VERDE — **232 tests** (166 en E2), mypy estricto sin errores, lint y
formato limpios.

| Requisito del ROADMAP | Dónde |
| --- | --- |
| El PDF declara tamaño de página y unidades correctas | Medido sobre el `MediaBox` en A4, A3 y A0, más que la página empieza en el origen |
| El cuadro mide exactamente 100 mm en coordenadas del documento | Dos veces: sobre la lámina en los cinco formatos, y **extrayendo el camino cerrado del flujo del PDF real** |
| Cada pieza lleva sus siete metadatos; falta uno y falla | Uno por uno, más un test de que son exactamente siete |
| Las teselas solapan lo declarado y las marcas coinciden | Desplazamiento medido entre teselas contiguas y coincidencia de las cuatro cruces |
| Comparación contra PDF de referencia | `tests/golden/plantilla_leva_a4.pdf`, byte a byte |

Exactitud medida sobre el documento: el cuadro sale de 99,99999 × 100,00008 mm.
El error de 10 y 82 nanómetros es el redondeo de coordenadas de la biblioteca,
unas mil ochocientas veces menor que el kerf del láser. El riesgo real no está
en el PDF sino en la impresora, y para eso está el cuadro.

## Verificación humana
Criterio fijado antes: imprimir de verdad, en la copistería que se vaya a
usar, y medir el cuadro con un calibre o una regla metálica. Después cortar
una pieza siguiendo la plantilla y comprobar que encaja.

Archivos a imprimir:
- `plantilla_leva_A4.pdf` — una leva real en una hoja.
- `plantilla_bastidor_troceado_A4.pdf` — nueve hojas, para el solape.

Medida obtenida: PENDIENTE — se anota aquí, con número
Quién lo comprobó: PENDIENTE
Encaje de la pieza cortada: PENDIENTE

## Decisiones tomadas
1. **La maquetación está separada del PDF.** Una `Lamina` es una lista de
   primitivas con coordenadas exactas, así que los invariantes se comprueban
   sobre datos y no abriendo un PDF. La misma lámina podrá salir a SVG.
2. **El cuadro es un cuadro y no una regla.** Una regla solo delata el
   escalado en un eje, y hay impresoras que escalan distinto en x y en y.
3. **La cabecera reserva 118 mm en cada hoja.** Cuesta espacio y es el precio
   de poder comprobar la escala en cualquier tesela.
4. **El origen es la esquina superior izquierda del área útil.** La fila 0
   enseña la banda de arriba de la pieza y las siguientes bajan, que es como
   se leen y como se pegan.
5. **Lo que no toca la página se descarta.** Al trocear, la pieza entera se
   dibuja en cada tesela; las líneas las recorta el PDF sin daño, pero un
   rótulo a medio cortar es peor que ninguno. Aparecen enteros en la vecina.
6. **El lienzo se abre en modo invariante.** Sin eso el PDF lleva fecha de
   creación e identificador aleatorio y no habría referencia que comparar.
7. **`Espesor` entra en `core/units.py`** con rango propio de 0 a 100 mm.

## Hallazgos
**El rango genérico no cazaba el error de magnitud.** `Longitud` admite hasta
diez metros, así que un espesor de 5 —escrito pensando en milímetros— pasaba
como cinco metros de tablero. La defensa de dos capas solo funciona si el
rango es el más estrecho que sea plausible; de ahí `Espesor`.

**La advertencia de impresión se salía de la hoja en A4.** En una sola línea
ocupaba 93 mm y la columna tiene 90. Un aviso cortado no avisa. Ahora va en
dos líneas, y hay un test que mide el ancho real de cada rótulo con las
métricas de la fuente y comprueba que ninguno se sale.

**Una sustitución de texto falló en silencio.** `ruff format` había recolocado
el bloque que intentaba cambiar, la cadena no coincidió y el script no dijo
nada: parecía aplicado y no lo estaba. Lo detectó el test de rótulos, no yo.
Anotado en las trampas de `CLAUDE.md`.

**Un test mío no comprobaba nada.** Llevaba un `and False` que lo dejaba
siempre vacío. Reescrito para distinguir las marcas de registro de las
esquinas de la marca de fase, que usan el mismo tipo de trazo.

## Deuda aceptada
- No hay anidado de varias piezas en una hoja: una pieza por documento. El
  aprovechamiento de plancha es de E5 en adelante.
- El troceado reparte en rejilla, sin optimizar el número de hojas.
- `pymupdf` y `cairosvg` se usaron solo para mirar los resultados durante el
  desarrollo. No son dependencias del proyecto.

## Puerta
Automática: CERRADA.
Humana (imprimir y medir): PENDIENTE de firma, con la medida escrita.
