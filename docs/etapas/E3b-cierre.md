# Cierre de etapa E3b · Calibración de impresión y juego de plantillas
Fecha: 2026-09-29

## Entregable
La escala deja de depender de una copistería concreta, y el paquete de papel
pasa a ser utilizable en un taller de verdad.

- `emit/calibracion.py` — `PerfilImpresora`, hoja patrón, veredicto de la
  impresora y corrección de la lámina.
- `emit/paquete.py` — qué archivos salen y qué lleva cada uno.
- `emit/layout.py` — agrupación de varias piezas en una hoja, elección de
  formato para un juego y el campo `escala` de la lámina.
- `emit/template.py` — se niega a escribir un documento con dos escalas.
- `bench/impresoras/` con el protocolo de medida.
- `scripts/plantillas_demo.py` genera las tres hojas de la copistería, más una
  cuarta opcional con piezas agrupadas, y admite un perfil para reimprimirlas
  corregidas.

## Verificación automática
Comando: `uv run python scripts/check.py`
Resultado: VERDE — **319 tests** (232 al cerrar E3), mypy estricto sin errores
—ahora también sobre `emit/`—, lint y formato limpios.
Commit: `a5cda92` (primera mitad) y el de esta etapa.

| Requisito del ROADMAP | Dónde |
| --- | --- |
| Aplicar factor 1,0 deja el PDF byte a byte idéntico al golden | Comparación de huella contra `tests/golden/plantilla_leva_a4.pdf`, y otra vez a través del paquete |
| Con un factor conocido, la distancia cambia en esa proporción **y el cuadro también** | Dos tests separados; el del cuadro lleva escrito por qué importa |
| Un perfil con error no uniforme produce veredicto negativo con motivo | `escala_no_uniforme`, con sugerencia |
| Ninguna pieza agrupada se solapa ni pierde su rótulo | Cajas envolventes cruzadas dos a dos, separación mínima medida, y los seis metadatos buscados uno por uno |
| Sin perfil, el sistema emite igual | La advertencia del cuadro ya avisa; un perfil neutro devuelve la lámina intacta |

Además, la vuelta completa simulada: se encoge la geometría como lo haría la
impresora, se mide lo encogido, se aplica el factor y se vuelve a encoger. El
cuadro sale a 100,000 mm.

## Verificación humana
Criterio fijado antes: imprimir la hoja patrón, medir, cargar los factores,
reimprimir y comprobar que el cuadro entra en tolerancia. Repetirlo en una
segunda copistería.

Medida sin corregir: PENDIENTE
Medida tras cargar el perfil: PENDIENTE
Segunda impresora: PENDIENTE
Quién lo comprobó: PENDIENTE

Instrumentos declarados por el usuario: pie de rey y cinta métrica.

## Desviaciones
**El rótulo de una pieza agrupada no cabía al lado de la pieza.** El primer
diseño recortaba el texto que se salía, y con eso una pieza colocada a la
derecha de la hoja perdía el espesor y la cantidad. Un metadato obligatorio no
se puede recortar, así que ahora el rótulo se envuelve en varias líneas y el
reparto reserva de antemano el ancho que va a necesitar. Lo cazó el test que
busca los seis metadatos de cada pieza, no la vista del PDF.

**Las bandas del medio no están en el medio.** Caen al 55 %. La mitad de 200
son 100, justo donde va una marca rotulada de la hoja patrón, y la banda le
pasaba por encima. Ninguna longitud de `PATRONES` cae en un múltiplo de 50 al
55 %.

**El alto del patrón no se puede rotular junto a su eje.** Esta capa no gira
texto, y en A2 el hueco de la izquierda se queda en 10 mm. Las dos medidas van
juntas y centradas sobre el rectángulo. Lo cazó el test de desbordamiento, que
recorre los cinco formatos.

## Decisiones tomadas
1. **Dos factores, `x` e `y`.** El arrastre del papel deforma más en la
   dirección de avance; un factor único repartiría el error del eje malo
   sobre el bueno.
2. **El perfil guarda la medida cruda, no solo el factor.** `factor_x` y
   `factor_y` se calculan y se descartan al deserializar, igual que
   `Veredicto.apto`. Así no hay forma de guardar un perfil que se contradiga,
   y cualquier número se puede recalcular.
3. **El cuadro se escala con la corrección.** Si no, mediría 100 mm sobre una
   hoja que ya no está a escala: el instrumento mintiendo de la forma más
   convincente posible.
4. **Un perfil neutro devuelve la lámina intacta y sin sello.** Nada que
   corregir, nada que anotar, y el PDF sale byte a byte como estaba.
5. **Una impresora se puede rechazar.** Error no uniforme entre bandas es
   veredicto negativo, no un factor promediado: compensar la media dejaría los
   extremos mal y el centro bien, que es peor porque parece correcta.
6. **`escala` es un campo de la lámina y `escribir_pdf` no mezcla escalas.**
   La separación entre plantillas y documentación deja de ser una convención
   de nombres de archivo y pasa a estar comprobada.
7. **El formato lo elige el pedido.** Por defecto, la hoja más pequeña donde
   todo cabe entero: trocear y pegar es lo que de verdad estropea una
   plantilla, y una hoja grande de más solo cuesta dinero.
8. **El conjunto va en la cabecera y los otros seis metadatos junto a su
   pieza.** Una cabecera que hablara de cinco piezas a la vez no diría de
   cuál. La cabecera lleva además la lista de números, que es la hoja de
   recuento al terminar de cortar.

## Deuda aceptada
- El reparto es por estantes, de más alta a más baja. **No resuelve el
  empaquetado óptimo**, que es un problema en sí: aquí solo se trata de no
  gastar una hoja por cada arandela. El aprovechamiento de plancha sigue
  siendo de E5 en adelante.
- `Paquete.dossier` es `None`: el dossier se construye en E6. La separación ya
  está hecha; lo que falta es el contenido.
- El ancho de los rótulos se estima por número de caracteres y no con las
  métricas de la fuente, para no meter reportlab dentro de `emit/layout.py`.
  La estimación es generosa a propósito, y hay tests que miden el ancho real.
- La hoja patrón no rota texto, así que el alto no se rotula junto a su eje.

## Puerta
Automática: CERRADA.
Humana: PENDIENTE de las impresiones. Absorbe la puerta pausada de E3.
