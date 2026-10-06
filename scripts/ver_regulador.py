"""El regulador del reloj moviéndose en el visor de VS Code, con la dinámica real.

    uv run --group cad python scripts/ver_regulador.py                    # régimen, tiempo real
    uv run --group cad python scripts/ver_regulador.py --lento 10         # cámara lenta ×10
    uv run --group cad python scripts/ver_regulador.py --tramo arranque   # los primeros 20 s
    uv run --group cad python scripts/ver_regulador.py --escala 2 --lento 10
    uv run --group cad python scripts/ver_regulador.py --gif build/regulador/regulador.gif
    uv run --group cad python scripts/ver_regulador.py --graficas         # PNG en build/regulador/

Hace falta el visor abierto: en VS Code, paleta de comandos (Ctrl+Mayús+P) →
«OCP CAD Viewer: Open viewer». O la tarea «Ver el regulador del reloj».

**Nada de lo que se ve está impuesto.** El movimiento sale de integrar la
dinámica (`compile/regulador.py`): el péndulo con el áncora y la rueda, el
bloqueo, el impulso, la caída y el choque. Las bolitas rojas se encienden
cuando una paleta toca (la de su lado) y cuando el diente cae (la de arriba).

`--tramo arranque` suelta el péndulo a 4° y enseña los primeros 20 s;
`--tramo regimen` (por defecto) lo pone ya en su amplitud estable. La subida
completa de la amplitud —cientos de oscilaciones con Q = 1.500— no se anima:
va en una gráfica (`--graficas`).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "build" / "regulador"
FPS = 25.0


# ---------------------------------------------------------------------------
# Simular
# ---------------------------------------------------------------------------


def simular(escala: float, tramo: str, par: float, segundos: float | None) -> tuple[Any, Any, Any]:
    from compile.regulador import Simulador, amplitud_estable, parametros, regulador
    from core.units import grados

    reg = regulador(escala)
    p = parametros(reg, par)
    if tramo == "arranque":
        theta0, duracion = grados(4.0), segundos or 20.0
    else:
        theta0 = amplitud_estable(reg, p)
        if not math.isfinite(theta0):
            raise SystemExit(f"con {par * 1e3:.1f} mN·m no hay amplitud estable: el reloj se para")
        duracion = segundos or 3 * reg.periodo_pequeno()
    h = Simulador(reg, p).simular(theta0, duracion, muestras_por_segundo=2000.0)
    return reg, p, h


def pistas(h: Any, lento: float) -> tuple[list[float], dict[str, tuple[str, list[float]]]]:
    """Las pistas del visor, remuestreadas a vídeo. Tiempo del visor = tiempo
    simulado × `lento`."""
    import numpy as np

    t = np.asarray(h.t)
    n = max(2, int(t[-1] * lento * FPS))
    tv = np.linspace(0.0, t[-1], n)
    theta = np.degrees(np.interp(tv, t, h.theta))
    phi = np.degrees(np.interp(tv, t, h.phi))
    idx = np.clip(np.searchsorted(t, tv), 0, len(t) - 1)
    modo = np.asarray(h.modo)[idx]
    lado = np.asarray(h.lado)[idx]
    escondido = -2000.0

    def testigo(mascara: Any) -> list[float]:
        return [0.0 if m else escondido for m in mascara]

    tiempos = [float(x * lento) for x in tv]
    return tiempos, {
        "/regulador/pendulo": ("rz", [float(x) for x in theta]),
        "/regulador/ancora": ("rz", [float(x) for x in theta]),
        "/regulador/rueda": ("rz", [float(-x) for x in phi]),
        "/regulador/testigos/contacto_entrada": ("tz", testigo(lado == "entrada")),
        "/regulador/testigos/contacto_salida": ("tz", testigo(lado == "salida")),
        "/regulador/testigos/caida": ("tz", testigo(modo == "caida")),
    }


def ver(reg: Any, h: Any, lento: float, gif: Path | None, detalle: bool = False) -> int:
    from build123d import Compound, Rot

    from emit.regulador_3d import ensamblaje

    try:
        from ocp_vscode import Animation, Camera, show
    except ImportError:
        print(
            "falta el visor: uv sync --group cad, y la extensión «OCP CAD Viewer».", file=sys.stderr
        )
        return 1
    conjunto = ensamblaje(reg)
    # El reloj se dibuja con y hacia arriba; el visor tiene z hacia arriba.
    raiz = Compound(children=list(conjunto.children), label="regulador").locate(Rot(X=90))
    try:
        camara: dict[str, Any] = {"reset_camera": Camera.FRONT}
        if detalle:
            # El escape de cerca: la rueda y las paletas, que es donde se ve
            # el bloqueo, el impulso y la caída. Tras el giro de la raíz, la y
            # del dibujo es la z del visor.
            alto = reg.ancora.eje_ancora[1] * 500.0
            camara = {
                "reset_camera": Camera.KEEP,
                "target": (0.0, 0.0, alto),
                "position": (0.0, -900.0, alto),
                "zoom": 6.0,
            }
        show(raiz, grid=(False, False, False), axes=False, **camara)
    except Exception as fallo:
        print(
            f"No hay visor OCP abierto ({type(fallo).__name__}). En VS Code: Ctrl+Mayús+P → "
            "«OCP CAD Viewer: Open viewer», y vuelve a lanzarlo.",
            file=sys.stderr,
        )
        return 1
    tiempos, todas = pistas(h, lento)
    animacion = Animation()
    for ruta, (accion, valores) in todas.items():
        animacion.add_track(ruta, accion, tiempos, valores)
    animacion.animate(1.0)
    if gif is not None:
        guardar_gif(animacion, gif, min(len(tiempos), 160), tiempos[-1])
        print(f"GIF en {gif}")
    return 0


def guardar_gif(animacion: Any, destino: Path, fotogramas: int, duracion: float) -> Path:
    """Una captura del visor por fotograma (como `scripts/animar.py` de la
    rama principal: `save_as_gif` deja el archivo abierto en Windows)."""
    import tempfile
    import time

    from ocp_vscode import save_screenshot
    from PIL import Image

    carpeta = Path(tempfile.mkdtemp(prefix="regulador_gif_"))
    imagenes = []
    for k in range(fotogramas):
        animacion.set_relative_time(k / fotogramas)
        time.sleep(0.6)
        ruta = carpeta / f"{k:04d}.png"
        save_screenshot(str(ruta))
        for _ in range(100):
            if ruta.exists() and ruta.stat().st_size > 0:
                break
            time.sleep(0.1)
        time.sleep(0.2)
        with Image.open(ruta) as img:
            fondo = Image.new("RGB", img.size, "white")
            fondo.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
            imagenes.append(fondo.resize((fondo.width // 2, fondo.height // 2)))
    destino.parent.mkdir(parents=True, exist_ok=True)
    imagenes[0].save(
        destino,
        save_all=True,
        append_images=imagenes[1:],
        duration=round(1000 * duracion / fotogramas),
        loop=0,
    )
    return destino


# ---------------------------------------------------------------------------
# Gráficas (Pillow: viene con ocp_vscode; matplotlib no está en el proyecto)
# ---------------------------------------------------------------------------


def grafica(
    destino: Path,
    titulo: str,
    eje_x: str,
    eje_y: str,
    series: list[tuple[str, list[float], list[float], str]],
    lineas_h: list[tuple[float, str]] | None = None,
    puntos: bool = False,
) -> Path:
    """Una gráfica de líneas en PNG, 1200 × 700."""
    from PIL import Image, ImageDraw, ImageFont

    w, h = 1200, 700
    m_izq, m_der, m_arr, m_aba = 110, 40, 70, 90
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    letra = chica = None
    # Una fuente con μ, θ, φ y tildes: la de por defecto de Pillow no las tiene.
    for nombre in ("arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        try:
            letra = ImageFont.truetype(nombre, 20)
            chica = ImageFont.truetype(nombre, 16)
            break
        except OSError:
            continue
    if letra is None or chica is None:
        letra = chica = ImageFont.load_default()
    xs = [x for _, sx, _, _ in series for x in sx]
    ys = [y for _, _, sy, _ in series for y in sy if math.isfinite(y)]
    ys += [v for v, _ in (lineas_h or [])]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    if y1 - y0 < 1e-12:
        y0, y1 = y0 - 1, y1 + 1
    pad = 0.06 * (y1 - y0)
    y0, y1 = y0 - pad, y1 + pad

    def px(x: float) -> float:
        return m_izq + (x - x0) / (x1 - x0) * (w - m_izq - m_der)

    def py(y: float) -> float:
        return h - m_aba - (y - y0) / (y1 - y0) * (h - m_arr - m_aba)

    d.rectangle([m_izq, m_arr, w - m_der, h - m_aba], outline="#41464d")
    for i in range(6):
        xv = x0 + (x1 - x0) * i / 5
        yv = y0 + (y1 - y0) * i / 5
        d.line([px(xv), h - m_aba, px(xv), h - m_aba + 6], fill="#41464d")
        d.text((px(xv), h - m_aba + 10), f"{xv:.3g}", fill="#41464d", font=chica, anchor="ma")
        d.line([m_izq - 6, py(yv), m_izq, py(yv)], fill="#41464d")
        d.text((m_izq - 10, py(yv)), f"{yv:.3g}", fill="#41464d", font=chica, anchor="rm")
        d.line([m_izq, py(yv), w - m_der, py(yv)], fill="#eceef1")
    for valor, nombre in lineas_h or []:
        d.line([m_izq, py(valor), w - m_der, py(valor)], fill="#d00000", width=2)
        d.text((w - m_der - 8, py(valor) - 4), nombre, fill="#d00000", font=chica, anchor="rd")
    for k, (nombre, sx, sy, color) in enumerate(series):
        tramo = [(px(x), py(y)) for x, y in zip(sx, sy, strict=True) if math.isfinite(y)]
        if len(tramo) > 1:
            d.line(tramo, fill=color, width=3)
        if puntos:
            for x, y in tramo:
                d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=color)
        d.rectangle([m_izq + 20, m_arr + 14 + 26 * k, m_izq + 44, m_arr + 26 + 26 * k], fill=color)
        d.text((m_izq + 52, m_arr + 20 + 26 * k), nombre, fill="#1c1f23", font=chica, anchor="lm")
    d.text((w / 2, 24), titulo, fill="#1c1f23", font=letra, anchor="mm")
    d.text((w / 2, h - 30), eje_x, fill="#1c1f23", font=chica, anchor="mm")
    d.text((22, h / 2), eje_y, fill="#1c1f23", font=chica, anchor="lm")
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino)
    return destino


def graficas(escala: float, par: float) -> int:
    """Las gráficas del informe, en `build/regulador/`. Tarda: la subida de
    la amplitud son cientos de oscilaciones."""
    import numpy as np

    from compile.regulador import (
        Simulador,
        amplitud_estable,
        extremos,
        parametros,
        regulador,
    )
    from core.units import grados

    reg = regulador(escala)
    sufijo = f"x{escala:g}"
    p = parametros(reg, par)

    # 1. Los primeros 20 s desde el arranque: θ y φ.
    h = Simulador(reg, p).simular(grados(4.0), 20.0, muestras_por_segundo=200.0)
    t = list(h.t)
    grafica(
        SALIDA / f"arranque_{sufijo}.png",
        f"Arranque, escala {escala:g}, {par * 1e3:.1f} mN·m: péndulo θ y rueda φ/10",
        "t (s)",
        "grados",
        [
            ("θ péndulo", t, [math.degrees(v) for v in h.theta], "#1f6fb2"),
            ("φ rueda / 10", t, [math.degrees(v) / 10 for v in h.phi], "#c8740a"),
        ],
    )

    # 2. La subida completa de la amplitud, desde 1,8° (sobre el arranque).
    h = Simulador(reg, p).simular(grados(1.8), 1200.0, muestras_por_segundo=40.0)
    ts, amps = extremos(h)
    estable = math.degrees(amplitud_estable(reg, p))
    grafica(
        SALIDA / f"amplitud_{sufijo}.png",
        f"Subida de la amplitud, escala {escala:g}, {par * 1e3:.1f} mN·m",
        "t (s)",
        "amplitud (°)",
        [("amplitud de cada oscilación", list(ts), [math.degrees(a) for a in amps], "#1f6fb2")],
        lineas_h=[(estable, f"estable {estable:.2f}°"), (3.0, "±3° del contrato")],
    )

    # 3. Amplitud estable frente al par, para los tres rozamientos.
    pares = [1e-3, 1.5e-3, 2e-3, 3e-3, 4e-3, 6.5e-3, 10e-3, 15e-3, 20e-3]
    series = []
    datos: dict[str, list[float]] = {}
    for mu, color in ((0.2, "#2e9d4f"), (0.3, "#1f6fb2"), (0.4, "#b23a3a")):
        a = [
            math.degrees(amplitud_estable(reg, parametros(reg, m, rozamiento_paleta=mu)))
            for m in pares
        ]
        datos[str(mu)] = a
        series.append((f"μ paleta = {mu}", [m * 1e3 for m in pares], a, color))
    grafica(
        SALIDA / f"amplitud_par_{sufijo}.png",
        f"Amplitud estable frente al par en el eje de la rueda, escala {escala:g}",
        "par en el eje de la rueda (mN·m)",
        "amplitud estable (°)",
        series,
        lineas_h=[(3.0, "±3°")],
        puntos=True,
    )
    from compile.regulador import amplitud_limite

    limite = math.degrees(amplitud_limite(reg))
    for mu, a in datos.items():
        for m, v in zip(pares, a, strict=True):
            if math.isfinite(v) and v > limite:
                print(
                    f"AVISO: μ {mu}, {m * 1e3:.1f} mN·m: {v:.2f}° pasa del límite ({limite:.2f}°)"
                )
    (SALIDA / f"amplitud_par_{sufijo}.json").write_text(
        json.dumps({"pares": pares, "amplitud": datos}, indent=1), encoding="utf-8"
    )
    del np
    print(f"gráficas en {SALIDA}")
    return 0


def informe(escala: float) -> int:
    """Los números que tiene que confirmar el banco R2, en
    `build/regulador/resultados_x{escala}.json`. Tarda unos minutos."""
    from compile.regulador import (
        amplitud_de_arranque,
        amplitud_estable,
        amplitud_limite,
        balance,
        en_regimen,
        par_de_parada,
        par_para_amplitud,
        parametros,
        regulador,
    )
    from core.units import grados

    reg = regulador(escala)
    r: dict[str, Any] = {
        "escala": escala,
        "inercia_rueda_kg_m2": reg.inercia_rueda,
        "masa_rueda_kg": reg.masa_rueda,
        "inercia_oscilante_kg_m2": reg.oscilante.inercia,
        "periodo_pequeno_s": reg.periodo_pequeno(),
    }
    destino = SALIDA / f"resultados_x{escala:g}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)

    def anota(clave: str, valor: Any) -> None:
        r[clave] = valor
        print(f"{clave} = {valor}", flush=True)
        destino.write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")

    limite = math.degrees(amplitud_limite(reg))
    anota("amplitud_limite_grados", limite)
    anota("par_de_parada_mNm", 1e3 * par_de_parada(reg, True))
    anota("par_de_parada_sin_eje_mNm", 1e3 * par_de_parada(reg, False))
    for mu in (0.2, 0.25, 0.3):
        for eje in (True, False):
            m = par_para_amplitud(reg, grados(3.0), eje, rozamiento_paleta=mu)
            anota(f"par_3g_mu{mu}_{'con' if eje else 'sin'}_eje_mNm", 1e3 * m)
    parada = r["par_de_parada_mNm"] * 1e-3
    for k in (1.5, 3.0):
        m = en_regimen(reg, parametros(reg, k * parada))
        anota(
            f"regimen_{k:g}x_parada",
            {
                "par_mNm": 1e3 * m.par,
                "amplitud_grados": math.degrees(m.amplitud),
                "periodo_s": m.periodo,
                "marcha_s_dia": m.marcha,
                "error_circular_s_dia": m.error_circular,
                "error_escape_s_dia": m.error_escape,
            },
        )
    anota("arranque_grados", math.degrees(amplitud_de_arranque(reg, parametros(reg, 3 * parada))))
    p = parametros(reg, 4e-3)
    a = amplitud_estable(reg, p)
    anota("balance_4mNm_J_por_oscilacion", balance(reg, p, a))
    maxima = math.degrees(amplitud_estable(reg, parametros(reg, 20e-3, rozamiento_paleta=0.2)))
    anota("amplitud_maxima_del_banco_grados", maxima)
    if maxima > limite:
        print(f"AVISO: {maxima:.2f}° pasa del límite de la geometría ({limite:.2f}°)", flush=True)
    print(f"informe en {destino}")
    return 0


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--escala", type=float, default=1.0, choices=(1.0, 2.0))
    p.add_argument("--lento", type=float, default=1.0, help="1 = tiempo real; 10 = cámara lenta")
    p.add_argument("--tramo", choices=("regimen", "arranque"), default="regimen")
    p.add_argument("--par", type=float, default=4.0, help="mN·m en el eje de la rueda")
    p.add_argument("--segundos", type=float, default=None, help="tiempo simulado")
    p.add_argument("--gif", type=Path, default=None)
    p.add_argument("--graficas", action="store_true", help="PNG en build/regulador/ (tarda)")
    p.add_argument("--detalle", action="store_true", help="la cámara, cerca del escape")
    p.add_argument("--informe", action="store_true", help="los números de R2 (tarda)")
    op = p.parse_args(argv)
    par = op.par * 1e-3
    if op.informe:
        return informe(op.escala)
    if op.graficas:
        return graficas(op.escala, par)
    reg, _, h = simular(op.escala, op.tramo, par, op.segundos)
    return ver(reg, h, op.lento, op.gif, op.detalle)


if __name__ == "__main__":
    raise SystemExit(main())
