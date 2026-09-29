# Cierre de etapa E0 · Andamiaje
Fecha: 2026-09-29

## Entregable
Repositorio con `uv`, ruff, mypy, pytest, la estructura de carpetas de CLAUDE.md,
CI en GitHub Actions y tres tests de arquitectura que protegen las reglas del
proyecto desde el primer día.

## Verificación automática
Comando: `uv sync && uv run ruff check . && uv run mypy core compile && uv run pytest`
Resultado: VERDE — ruff sin avisos, mypy estricto sin errores en 5 ficheros,
16 tests pasados.

Verificación del guardián: se introdujo a propósito un fichero en `core/` que
importaba `pathlib` y `ezdxf` y llamaba a `print()`. Los dos tests de
arquitectura fallaron y nombraron fichero y línea. Retirado el fichero, verde
otra vez. El guardián muerde.

## Verificación humana
Criterio fijado antes: clonar en otra máquina y dejarlo funcionando en menos de
cinco minutos siguiendo solo el README, sin preguntar nada.

### Intento 1 — 2026-09-29 — FALLIDO
Quién lo comprobó: Juan Carlos, en Windows con Git Bash (MINGW64).
Resultado: `uv sync` y `uv run` fallaron con `bash: uv: command not found`.
El clon funcionó. El README no llevaba a un estado funcionando.
Evidencia: captura del terminal.

Tres defectos del README, todos corregidos:

1. La instalación de `uv` estaba redactada como prosa condicional ("si no tienes
   uv") en lugar de como paso obligatorio con comprobación posterior.
2. No advertía de que, tras instalar `uv` en Windows, hay que **cerrar y volver
   a abrir el terminal**: Git Bash no ve el PATH nuevo hasta reiniciarse. Es la
   causa más probable de este fallo concreto.
3. Los comandos iban en un bloque pegable de varias líneas. Al fallar el tercero,
   los siguientes se ejecutaron igualmente y el error quedó enterrado. Ahora son
   pasos numerados de uno en uno, con una comprobación explícita
   (`uv --version`) antes de continuar.

Añadido además un apartado «Si uv no aparece» con el arreglo de PATH para Git
Bash, PowerShell, macOS y Linux, y la alternativa `pipx install uv`.

### Intento 2
Quién lo comprobó: PENDIENTE
Resultado: PENDIENTE
Evidencia: PENDIENTE

CI: verde sobre el push a `main` y sobre el PR #1 de prueba
(`docs: plantilla de cierre de etapa`). Check-run «lint, tipos y tests»
con conclusion=success en ambos eventos.
Repositorio: https://github.com/jcjarauta/claude.automatas

## Desviaciones
- Ninguna en la parte automática.

## Decisiones tomadas
- Disposición plana de paquetes (`core/`, `compile/`, `emit/`, `api/` en la raíz)
  en lugar de `src/`. Coincide con lo que declara CLAUDE.md y con el comando de
  verificación del roadmap.
- El paquete se llama `compile` aunque coincida con el nombre de una función
  incorporada de Python. Es legal, no hay módulo estándar con ese nombre, y
  cambiarlo desincronizaría CLAUDE.md y el ROADMAP.
- Dependencias pesadas (build123d, reportlab, pymupdf) fuera de E0: entran en la
  etapa que las necesita. `uv sync` tarda segundos.
- Tests de arquitectura como parte del andamiaje, no como añadido posterior.

## Deuda aceptada
- `bench/`, `docs/schema/` y `docs/etapas/` existen con `.gitkeep`.
- `web/` no existe todavía; llega en E7.

## Puerta
Automática: CERRADA — comando de verificación en verde en local y en CI.
Humana (prueba de los cinco minutos): ABIERTA.
