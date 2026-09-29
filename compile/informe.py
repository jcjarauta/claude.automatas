"""El informe del pedido: qué salió, qué no, y qué hay que hacer con ello.

Un veredicto negativo es un resultado, no un fallo del programa, así que el
informe se escribe igual cuando la frase no cabe: entonces es cuando más
falta hace. Va en markdown porque se lee en el terminal, en el navegador y
pegado en un correo sin convertir nada.
"""

from __future__ import annotations

from pathlib import Path

from compile.escribiente import Compilacion, Escribiente
from core.units import Radianes, a_grados, a_mm
from core.verdict import Incidencia


def _incidencias(titulo: str, incidencias: tuple[Incidencia, ...]) -> list[str]:
    if not incidencias:
        return []
    lineas = [f"### {titulo}", ""]
    for i in incidencias:
        donde = f" (θ = {a_grados(Radianes(i.theta)):.1f}°)" if i.theta is not None else ""
        lineas.append(f"- **{i.codigo}**{donde} — {i.mensaje.rstrip('.')}.")
        if i.sugerencia:
            lineas.append(f"  - Qué hacer: {i.sugerencia.rstrip('.')}.")
    lineas.append("")
    return lineas


def informe(compilacion: Compilacion, maquina: Escribiente) -> str:
    """El informe completo, en markdown."""
    v = compilacion.veredicto
    escritura = compilacion.escritura
    lineas = [
        f"# Pedido «{escritura.nombre}»",
        "",
        f"**Veredicto: {'APTO' if v.apto else 'NO APTO'}**",
        "",
        "## La escritura",
        "",
        f"- Trazos: {len(escritura.trazos)}",
        f"- Tamaño en el papel: {a_mm(escritura.ancho):.1f} × {a_mm(escritura.alto):.1f} mm",
        f"- Recorrido escrito: {v.metricas.get('longitud_trazada', 0.0) * 1000:.0f} mm",
        f"- Recorrido volado: {v.metricas.get('longitud_volada', 0.0) * 1000:.0f} mm",
        "",
        "## Las levas",
        "",
    ]

    if compilacion.perfiles:
        lineas += [
            "| Leva | Ø máximo | Ángulo de presión | Calaje del brazo |",
            "| --- | --- | --- | --- |",
        ]
        for nombre, perfil in compilacion.perfiles.items():
            presion = v.metricas.get(f"angulo_presion_max_{nombre}")
            grados_presion = f"{a_grados(Radianes(presion)):.1f}°" if presion else "—"
            calaje = a_grados(Radianes(compilacion.calajes[nombre]))
            lineas.append(
                f"| {nombre} | {perfil.radio_maximo * 2000:.1f} mm | {grados_presion} "
                f"| {calaje:+.1f}° |"
            )
        lineas += [
            "",
            f"Relación seguidor → brazo: **{maquina.relacion:g}:1**. El varillaje "
            f"amplifica por ese mismo factor el error del perfil y el juego.",
            "",
            "El calaje es a qué ángulo va montado cada brazo sobre el eje de su "
            "seguidor, medido desde la marca de fase. Montarlo mal escribe basura.",
            "",
        ]
    else:
        lineas += ["No se sintetizó ninguna leva: mira las incidencias.", ""]

    if compilacion.simulacion is not None:
        simulacion = compilacion.simulacion
        lineas += [
            "## Simulación",
            "",
            "Se recorren las levas ya sintetizadas y se mira dónde pasa la punta.",
            "",
            f"- Error máximo del trazo: **{simulacion.error_maximo * 1000:.3f} mm**",
            f"- Error medio: {simulacion.error_medio * 1000:.3f} mm",
            "",
            "No incluye el kerf ni el desgaste, que se miden en el banco (E4).",
            "",
        ]

    lineas += _incidencias("Errores", v.errores)
    lineas += _incidencias("Avisos", v.avisos)
    if v.apto and not v.incidencias:
        lineas += ["Sin incidencias.", ""]

    return "\n".join(lineas)


def escribir_informe(compilacion: Compilacion, maquina: Escribiente, destino: Path | str) -> Path:
    ruta = Path(destino)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(informe(compilacion, maquina), encoding="utf-8")
    return ruta


def resumen(compilacion: Compilacion) -> str:
    """Una línea para el terminal."""
    v = compilacion.veredicto
    estado = "APTO" if v.apto else "NO APTO"
    error = v.metricas.get("error_trazo_maximo")
    cola = f", error de trazo {error * 1000:.3f} mm" if error is not None else ""
    return (
        f"{estado}: {len(compilacion.escritura.trazos)} trazos, "
        f"{len(compilacion.piezas)} levas, {len(v.errores)} errores, "
        f"{len(v.avisos)} avisos{cola}"
    )


__all__ = ["escribir_informe", "informe", "resumen"]
