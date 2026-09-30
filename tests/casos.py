"""Los casos de referencia del golden compilado.

**Por qué son fórmulas y no listas de puntos.** Un caso de referencia tiene
que poder leerse y discutirse: «una sinusoide amortiguada de tres ciclos» se
revisa de un vistazo y doscientos pares de coordenadas no. Y así nadie tiene
que fiarse de que el montón de números diga lo que el nombre promete.

Cada caso está para tensar una cosa distinta, porque un golden de un solo
caso vigila un solo camino:

- **`hola`** — el pedido del demo: un lazo cerrado y un salto corto al trazo
  anterior, que es donde se rompía la continuidad del vuelo.
- **`firma`** — un trazo único y largo, cursivo: casi todo θ en un tramo y un
  solo vuelo, el de regreso.
- **`puntos`** — muchos trazos cortos: el reparto de θ contra los mínimos.
- **`apretada`** — una frase que **no cabe**. Fija también el camino del
  veredicto negativo, que si no no lo vigila nadie.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import numpy as np

from compile.escribiente import SEGUIDORES
from core.escritura import Escritura, Trazo
from core.units import TAU, Metros, mm

DEMO = Path(__file__).resolve().parents[1] / "demo"


def _trazo(puntos: np.ndarray) -> Trazo:
    return Trazo(puntos=[(Metros(float(x)), Metros(float(y))) for x, y in puntos])


def hola() -> Escritura:
    """El pedido del repositorio, tal cual se compila desde el CLI."""
    datos = json.loads((DEMO / "hola.json").read_text(encoding="utf-8"))
    return Escritura(
        nombre=datos.get("nombre", "hola"),
        trazos=[Trazo(puntos=[(mm(x), mm(y)) for x, y in t]) for t in datos["trazos"]],
    )


def firma() -> Escritura:
    """Una cursiva de un solo trazo: sinusoide amortiguada de tres ciclos.

    Es el caso de la firma digital, que es de donde viene la mitad de los
    pedidos: un trazo continuo y largo que se lleva casi todos los grados, y
    un único vuelo, el de regreso al principio.
    """
    vueltas = 3.0 * TAU
    t = np.linspace(0.0, vueltas, 60)
    x = t / vueltas * 0.080
    y = 0.012 * np.sin(t) * np.exp(-t / 12.0)
    return Escritura(nombre="firma", trazos=[_trazo(np.column_stack([x, y]))])


def puntos() -> Escritura:
    """Ocho trazos cortos en rejilla: el reparto de θ contra los mínimos.

    Cada trazo pide su `arco_minimo_trazo` y cada vuelo el doble del arco de
    levantamiento, así que con ocho de cada los mínimos se comen buena parte
    de la vuelta y lo que sobra se reparte muy justo.
    """
    trazos = []
    for i in range(8):
        x0 = 0.006 + 0.009 * i
        y0 = 0.004 if i % 2 else 0.016
        trazos.append(_trazo(np.array([[x0, y0], [x0 + 0.005, y0 + 0.004]])))
    return Escritura(nombre="puntos", trazos=trazos)


def apretada() -> Escritura:
    """Una frase que no cabe: veinte trazos, más de lo que da la vuelta.

    Fija el camino del veredicto negativo. Sin un caso así, el golden solo
    vigila los pedidos que salen bien, que son la mitad de los caminos.
    """
    trazos = []
    for i in range(20):
        x0 = 0.002 + 0.004 * i
        trazos.append(_trazo(np.array([[x0, 0.004], [x0 + 0.002, 0.014]])))
    return Escritura(nombre="apretada", trazos=trazos)


CASOS = {c.__name__: c for c in (hola, firma, puntos, apretada)}

__all__ = [
    "CASOS",
    "GOLDEN",
    "apretada",
    "escribir_manifiestos",
    "firma",
    "hola",
    "manifiesto",
    "puntos",
]


# ---------------------------------------------------------------------------
# El manifiesto: lo que el golden guarda de cada caso
# ---------------------------------------------------------------------------

GOLDEN = Path(__file__).resolve().parent / "golden" / "compilado"


def manifiesto(nombre: str) -> dict:
    """Lo que hay que guardar de un pedido compilado para detectar que ha
    cambiado, y para poder decir **en qué** ha cambiado.

    Guardar los DXF enteros costaría 150 kB por caso y haría ilegible
    cualquier diff: nadie revisa cincuenta mil líneas de DXF. Se guarda el
    sha256, que es la comparación byte a byte que pide la etapa, **y además
    los números de cabecera**, que son los que dicen qué se ha movido cuando
    el hash deja de cuadrar. Un golden que solo falla no sirve de nada: hay
    que poder distinguir «ha cambiado el rótulo del DXF» de «ha cambiado la
    geometría de la leva».
    """
    from compile.escribiente import compilar
    from core.cam.envelope import angulo_de_presion, radio_de_curvatura
    from emit.dxf import escribir_dxf

    compilacion = compilar(CASOS[nombre]())
    veredicto = compilacion.veredicto

    def redondo(x: float, cifras: int = 6) -> float:
        """En mm o grados, a nanómetro. Estrecho de sobra y sin ruido de
        último bit, que en otra máquina no tiene por qué coincidir."""
        return round(float(x), cifras)

    levas = []
    with tempfile.TemporaryDirectory() as tmp:
        for pieza, canal in zip(compilacion.piezas, SEGUIDORES, strict=True):
            ruta = escribir_dxf(pieza, Path(tmp) / f"{pieza.numero}.dxf")
            perfil = compilacion.perfiles[canal]
            curvatura = radio_de_curvatura(perfil)
            positivos = curvatura[np.isfinite(curvatura) & (curvatura > 0.0)]
            levas.append(
                {
                    "canal": canal,
                    "numero": pieza.numero,
                    "sha256": hashlib.sha256(ruta.read_bytes()).hexdigest(),
                    "puntos_del_contorno": len(pieza.contorno),
                    "radio_maximo_mm": redondo(perfil.radio_maximo * 1000.0),
                    "radio_minimo_mm": redondo(perfil.radio_minimo * 1000.0),
                    "curvatura_minima_mm": redondo(float(positivos.min()) * 1000.0),
                    "presion_maxima_grados": redondo(
                        float(np.max(np.abs(angulo_de_presion(perfil)))) * 180.0 / np.pi
                    ),
                }
            )

    return {
        "caso": nombre,
        "apto": veredicto.apto,
        "errores": sorted(i.codigo for i in veredicto.errores),
        "avisos": sorted(i.codigo for i in veredicto.avisos),
        "tramos": [f"{t.clase}{t.indice}" for t in compilacion.tramos],
        "calajes_grados": {k: redondo(v * 180.0 / np.pi) for k, v in compilacion.calajes.items()},
        "error_trazo_mm": redondo(
            (compilacion.simulacion.error_maximo if compilacion.simulacion else 0.0) * 1000.0
        ),
        "desviacion_de_lo_capturado_mm": redondo(
            veredicto.metricas.get("desviacion_de_lo_capturado", 0.0) * 1000.0
        ),
        "levas": levas,
    }


def escribir_manifiestos() -> list[Path]:
    """Regenera el golden compilado. Solo desde `scripts/regenerar_golden.py`."""
    GOLDEN.mkdir(parents=True, exist_ok=True)
    escritos = []
    for nombre in CASOS:
        ruta = GOLDEN / f"{nombre}.json"
        ruta.write_text(
            json.dumps(manifiesto(nombre), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        escritos.append(ruta)
    return escritos
