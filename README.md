# Escribano

Herramienta para diseñar y fabricar **máquinas mecánicas programables**: autómatas
de levas, cajas de música, telares y máquinas de trabajo impulsadas por personas.

El primer producto es el **escribiente**: alguien escribe una frase a mano y el
sistema genera las tres levas que la reproducen, más todo lo necesario para
fabricarla — corte digital, plantilla en papel a escala 1:1 y dossier de montaje.

---

## Puesta en marcha

Requisitos: **git** y **[uv](https://docs.astral.sh/uv/)**. Nada más.
`uv` descarga por su cuenta la versión de Python que haga falta.

> **Haz los pasos de uno en uno y comprueba cada uno antes de seguir.**
> Si pegas todo el bloque de golpe, un fallo a mitad se pierde entre la
> salida de los comandos siguientes.

### Paso 1 · Instalar uv

```bash
# macOS y Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```powershell
# Windows — en PowerShell, no en Git Bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Si ya tienes Python instalado, esta alternativa también sirve en cualquier
sistema: `pipx install uv` (o `pip install --user uv`).

### Paso 2 · Cerrar el terminal y abrir uno nuevo

**Este paso no es opcional.** El instalador añade `uv` al PATH, y un terminal ya
abierto no ve ese cambio. En Windows afecta especialmente a Git Bash.

### Paso 3 · Comprobar que uv responde

```bash
uv --version
```

Tiene que imprimir un número de versión. Si dice `uv: command not found`, **no
sigas**: ve a [Si uv no aparece](#si-uv-no-aparece) más abajo.

### Paso 4 · Clonar e instalar

```bash
git clone https://github.com/jcjarauta/claude.automatas
cd claude.automatas
uv sync
```

### Paso 5 · Comprobar que todo está en orden

```bash
uv run python scripts/check.py
```

Debe terminar en **VERDE**. Es el equivalente a:

```bash
uv run ruff check . && uv run mypy core compile && uv run pytest
```

Si sale ROJO, algo del entorno está mal y no tiene sentido seguir.

---

### Si uv no aparece

`uv: command not found` después de instalarlo casi siempre es el PATH, no la
instalación.

**Windows, Git Bash.** El instalador deja `uv.exe` en
`C:\Users\<TU-USUARIO>\.local\bin`. Comprueba si está:

```bash
ls ~/.local/bin/uv.exe
```

Si está pero no responde, añádelo al PATH de esta sesión:

```bash
export PATH="$HOME/.local/bin:$PATH"
uv --version
```

Para que persista, añade esa línea a `~/.bashrc`:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

**Windows, PowerShell o CMD.** Reinicia el terminal. Si sigue sin verse, añade
`%USERPROFILE%\.local\bin` al PATH del usuario desde *Editar las variables de
entorno del sistema*, y vuelve a abrir el terminal.

**macOS y Linux.** El instalador deja `uv` en `~/.local/bin`. Mismo arreglo:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

**Salida de emergencia.** Si nada de esto funciona y tienes Python a mano,
`pipx install uv` lo instala en un sitio que ya suele estar en el PATH.

---

## Comandos del día a día

| Qué quieres | Comando |
| --- | --- |
| Instalar o actualizar dependencias | `uv sync` |
| Todos los tests | `uv run pytest` |
| Solo el núcleo, rápido | `uv run pytest -m core` |
| Corregir lint automáticamente | `uv run ruff check --fix .` |
| Formatear | `uv run ruff format .` |
| Comprobar tipos | `uv run mypy core compile` |
| Las tres comprobaciones | `uv run python scripts/check.py` |
| Añadir una dependencia | `uv add <paquete>` |
| Añadir una de desarrollo | `uv add --dev <paquete>` |

---

## Estructura

```
core/       Núcleo puro: geometría, cinemática, energía. Sin E/S, sin red.
  cam/        Síntesis de perfiles y envolvente geométrica
  actors/     Cinemáticas inversas de los actuadores
  energy/     Par, volante, acumulación
compile/    Orquesta: intención -> núcleo -> envolvente -> emisores
emit/       Salidas: DXF, plantilla 1:1, dossier, 3D
api/        API HTTP (llega en E8)
bench/      Datos medidos en el banco de ensayo
docs/       Documentación del proyecto
tests/      Tests, incluidos los de arquitectura
scripts/    Utilidades de desarrollo
```

La dependencia va en un solo sentido: **`core` ← `compile` ← `emit`/`api`**.
El núcleo no conoce a nadie. Hay un test que lo comprueba en cada ejecución.

---

## Las reglas

Están en [`CLAUDE.md`](CLAUDE.md) y son cortas. Las dos que más se incumplen:

1. **Todo programa es función de θ**, el ángulo del eje maestro, nunca del tiempo.
2. **SI dentro, milímetros fuera.** Metros, radianes y newtons en `core/`;
   la conversión ocurre solo en `emit/` y `api/`.

`tests/test_arquitectura.py` protege las que se pueden comprobar solas.

---

## Documentación

| Documento | Qué contiene |
| --- | --- |
| [`CLAUDE.md`](CLAUDE.md) | Reglas técnicas, stack, convenciones, trampas conocidas |
| [`ROADMAP.md`](ROADMAP.md) | Las diez etapas, con verificación automática y humana |
| `docs/baseline.md` | Principios, ontología de la máquina, módulos, negocio |
| `docs/contratos.md` | Contratos congelados: eje, bastidor, fase |
| `docs/etapas/` | Cierre de cada etapa, con la evidencia |

---

## Estado

**Etapa E0 · Andamiaje.** El repositorio existe y las tres comprobaciones pasan
sobre un proyecto vacío. Los paquetes están creados pero sin contenido: el
modelo de datos llega en E1 y el núcleo geométrico en E2.
