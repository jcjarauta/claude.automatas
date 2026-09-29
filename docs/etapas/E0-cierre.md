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
