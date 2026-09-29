# Cierre de etapa E1 · Contrato de datos
Fecha: 2026-09-29

## Entregable
El modelo de datos del que depende todo lo demás:

- `core/units.py` — `NewType` por magnitud, constructores desde unidades
  humanas y alias validados con rangos de plausibilidad.
- `core/program.py` — `Programa`, `PistaContinua`, `PistaEvento`, `Evento`.
- `core/module.py` — `FichaModulo` y sus bloques, `ModuloMontado`, `Maquina`.
- `core/verdict.py` — `Veredicto` e `Incidencia`.
- `core/errors.py` — excepciones de dominio.
- `docs/schema/` — cuatro esquemas JSON versionados.
- `docs/modulos/` — cuatro fichas reales del catálogo.

## Verificación automática
Comando: `uv run ruff check . && uv run ruff format --check . && uv run mypy core compile && uv run pytest`
Resultado: VERDE — 0 avisos de lint, 28 ficheros formateados, mypy estricto sin
errores en 10 ficheros, **95 tests pasados** (16 en E0).

Lo exigido por el ROADMAP, punto por punto:

| Requisito | Dónde se comprueba |
| --- | --- |
| Ida y vuelta a JSON idéntica | `test_program.py`, `test_module.py`, `test_verdict.py` |
| Programa con canal continuo y de evento | `test_el_programa_admite_las_dos_clases_de_pista` |
| Valor con unidad equivocada rechazado | `test_units.py`, dos casos: mm sin convertir y grados sin convertir |
| `mypy --strict` limpio sobre `core/` | en el comando |

## Verificación humana
Criterio fijado antes: la ficha se puede rellenar para tres módulos muy
distintos sin que sobre ni falte ningún campo.

Resultado: hecho con **cuatro** módulos reales, que están en `docs/modulos/` y
que la suite valida en cada ejecución:

| Módulo | Familia | Canales | Cinemática | Ergonomía | Signo |
| --- | --- | --- | --- | --- | --- |
| `brazo_escribiente` | actuador | consume x, y | sí | — | consume |
| `leva_resistencia` | memoria | produce resistencia | — | — | consume |
| `seguidor_resistencia` | transmisión | consume resistencia | sí | — | consume |
| `estacion_pedal` | fuente humana | ninguno | — | sí | **aporta** |

Cada uno deja vacíos campos distintos y ninguno fuerza un campo inventado.
La estación de pedal, que no consume ningún canal ni tiene cinemática inversa,
encaja igual: es lo que demuestra que la ficha es de módulo y no de actuador.

Quién lo comprobó: PENDIENTE — firma de la puerta
Evidencia: `docs/modulos/*.json` y los tests del final de `tests/core/test_module.py`

## Desviaciones
- El roadmap describía las muestras como pares (θ, valor). Se guardan como dos
  listas paralelas: ocupa la mitad en JSON, convierte a numpy sin copiar y el
  invariante de longitud lo comprueba el validador.
- Se añadió `ModuloMontado`, que el roadmap no nombraba, para separar el
  catálogo del montaje.
- Se añadió el rol `produce`/`consume` en los canales, consecuencia de partir
  leva y seguidor en dos módulos.

## Decisiones tomadas
1. θ en [0, 2π), sin almacenar el extremo.
2. Pistas como muestras, no como splines.
3. Ficha (catálogo) separada de módulo montado (instalación).
4. Cinemática referenciada por clave a un registro, no incrustada.
5. Unidades en dos capas: `NewType` para mypy, rangos de plausibilidad para
   el error de magnitud.
6. `apto` es campo calculado; se serializa pero se descarta al deserializar.
7. Catálogo de módulos como JSON versionado, no como código.
8. **La leva de resistencia se parte en dos módulos**, leva y seguidor
   (decisión del usuario, opción c). Mejora la ontología —la leva es memoria,
   el seguidor es transmisión— y coloca el radio del rodillo donde le
   corresponde, que es la ficha del seguidor, que es donde C3 irá a buscarlo.

## Deuda aceptada
- `PistaEvento` existe pero nada la consume. Es deliberado: C5 es de E10.
- Los contratos de `docs/contratos.md` siguen en PENDIENTE; se cierran en E3.
- `core/errors.py` declara excepciones que todavía nadie lanza. Establecen el
  patrón para E2.

## Hallazgo
El test de ida y vuelta encontró un fallo real antes de que llegara a ningún
sitio: `extra="forbid"` junto a un campo calculado rompe la deserialización,
porque `apto` sale en el JSON y al volver se rechaza como campo extra. Se
resolvió descartando `apto` a la entrada, lo que además hace **imposible por
construcción** guardar un veredicto que se contradiga, en vez de solo
improbable.

## Puerta
Automática: CERRADA.
Humana (revisión del modelo en papel y de las cuatro fichas): PENDIENTE de firma.
