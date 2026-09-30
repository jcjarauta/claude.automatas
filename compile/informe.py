"""El informe del pedido: qué salió, qué no, y qué hay que hacer con ello.

Un veredicto negativo es un resultado, no un fallo del programa, así que el
informe se escribe igual cuando la frase no cabe: entonces es cuando más
falta hace. Va en markdown porque se lee en el terminal, en el navegador y
pegado en un correo sin convertir nada.
"""

from __future__ import annotations

from pathlib import Path

from compile.conjunto import Montaje
from compile.coste import Valoracion
from compile.energia import Accionamiento, Energia
from compile.escribiente import Compilacion, Escribiente
from compile.tolerancias import Presupuesto, amplificacion_del_canto
from core.units import Radianes, a_grados, a_mm
from core.verdict import Incidencia, Veredicto


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


def informe(
    compilacion: Compilacion,
    maquina: Escribiente,
    montaje: Montaje | None = None,
    veredicto_montaje: Veredicto | None = None,
    energia: Energia | None = None,
    veredicto_energia: Veredicto | None = None,
    accionamiento: Accionamiento | None = None,
    valoracion: Valoracion | None = None,
    presupuesto: Presupuesto | None = None,
) -> str:
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
            "## Contacto",
            "",
            "Segunda opinión, por otro camino: se apoya el rodillo en el **perfil ya",
            "cortado**, sin usar la curva de paso. Caza los errores sistemáticos —un",
            "desplazamiento por radio de rodillo del revés, un signo cambiado— que a",
            "la simulación se le escapan porque comparte fórmulas con la síntesis.",
            "Del socavado se ocupa la envolvente, que lo calcula exacto.",
            "",
            f"- Desviación del seguidor: {v.metricas.get('error_contacto_rad', 0.0) * 1000:.3f}"
            " mrad",
            f"- Lo que eso vale en la punta, amplificado por el varillaje: "
            f"**{v.metricas.get('error_contacto_en_la_punta', 0.0) * 1000:.3f} mm**",
            "",
            "Viene del muestreo: la pieza que se corta es el polígono, no la curva.",
            "Subir las muestras por vuelta lo baja.",
            "",
            "Nada de esto incluye el kerf ni el desgaste, que se miden en el banco (E4).",
            "",
        ]

    if montaje is not None:
        lineas += [
            "## El cartucho montado",
            "",
            "Las levas por separado ya tienen quien las juzgue. Esto mira el",
            "conjunto: tres levas en el mismo árbol y tres postes de seguidor que",
            "atraviesan los tres planos.",
            "",
            f"- Altura de la pila: {float(montaje.altura_pila) * 1000:.0f} mm",
            f"- Masa de las tres levas: {float(montaje.masa) * 1000:.0f} g",
            f"- Momento de inercia respecto del árbol: "
            f"{float(montaje.inercia) * 1e7:.0f} × 10⁻⁷ kg·m²",
            f"- Energía a una vuelta por segundo: "
            f"{0.5 * float(montaje.inercia) * (2.0 * 3.141592653589793) ** 2 * 1000:.1f} mJ",
            f"- Radio máximo: {float(montaje.radio_maximo) * 1000:.1f} mm",
            f"- Hueco hasta el poste más cercano: "
            f"**{float(montaje.holgura_al_poste) * 1000:.1f} mm**",
            "",
            "Ese hueco encoge cuando la frase crece: una leva mayor es un barrido",
            "mayor del seguidor. Es el límite que decide qué frases caben.",
            "",
        ]

    if energia is not None and accionamiento is not None:
        volante = float(energia.volante_en_la_manivela)
        disco = 2.0 * volante / 0.05**2
        lineas += [
            "## Girarlo a mano",
            "",
            f"A {accionamiento.vueltas_por_minuto:.0f} vueltas por minuto, con una "
            f"relación de manivela de {accionamiento.transmision.relacion:g}:1.",
            "",
            f"- Par medio en el árbol: {energia.par_medio * 1000:.0f} mN·m",
            f"- Par máximo: {energia.par_maximo * 1000:.0f} mN·m",
            f"- Trabajo por vuelta: {float(energia.trabajo_por_vuelta) * 1000:.0f} mJ",
            f"- Energía de fluctuación: {float(energia.fluctuacion.energia) * 1000:.1f} mJ",
            "",
            "**El par no es el problema.** Una manivela da del orden de un newton·metro"
            " y aquí se piden centésimas.",
            "",
            "Lo que aprieta es la **suavidad**: lo que sobra en unos grados y falta en"
            " otros hay que guardarlo con inercia.",
            "",
            f"- Inercia necesaria en el árbol: "
            f"{float(energia.inercia_necesaria) * 1e4:.1f} × 10⁻⁴ kg·m²",
            f"- La aporta el cartucho: "
            f"{float(energia.inercia_del_cartucho) * 1e4:.1f} × 10⁻⁴ kg·m²",
            f"- **Volante que falta, puesto en el eje de la manivela: "
            f"{volante * 1e4:.1f} × 10⁻⁴ kg·m²** — un disco de acero de 50 mm de "
            f"radio y {disco * 1000:.0f} g",
            "",
            "Puesto en el árbol haría falta la relación al cuadrado veces más. Ahí está"
            " el motivo de llevar reductor aunque el par sobre.",
            "",
        ]

    if presupuesto is not None:
        lineas += [
            "## Cuánto error cabe esperar",
            "",
            f"El varillaje amplifica: un error radial en el canto de la leva llega a la"
            f" punta multiplicado por unas **{amplificacion_del_canto(maquina):.0f} veces**"
            f" de cuenta corta, y algo más según el jacobiano real del cinco barras. Por"
            f" eso lo que decide la precisión de esta máquina no es el compilador, es"
            f" quien corta la leva.",
            "",
            "| De dónde | Magnitud | Amplificación | En la punta |",
            "| --- | --- | --- | --- |",
        ]
        for contribucion in sorted(presupuesto.cadena.contribuciones, key=lambda c: -c.en_punta):
            lineas.append(
                f"| {contribucion.nombre} | {contribucion.magnitud * 1000:.3f} mm |"
                f" × {contribucion.amplificacion:.1f} |"
                f" **{contribucion.en_punta * 1000:.3f} mm** |"
            )
        lineas += [
            "",
            f"- **Peor caso: {presupuesto.peor_caso * 1000:.2f} mm** — todo conspirando en"
            f" el mismo sentido. Es lo que se puede prometer.",
            f"- Cuadrático: {presupuesto.cuadratica * 1000:.2f} mm — holguras"
            f" independientes, que es lo que se suele medir.",
            "",
            "**Dos de estas contribuciones no están medidas**: el error de perfil es la"
            " tolerancia que se le pide al taller, no la que da, y la holgura de pivote"
            " es una estimación de catálogo. Las mide E4. Hasta entonces esto sirve para"
            " decidir arquitectura, no para prometer una cota a un cliente.",
            "",
        ]

    if valoracion is not None:
        minutos = valoracion.segundos_de_maquina / 60.0
        lineas += [
            "## Lo que cuesta",
            "",
            "Precios de catálogo con IVA, de `bench/precios.json`. El corte de las"
            " levas está **externalizado a precio cerrado por bloque**: no depende de"
            " la frase, así que se puede presupuestar antes de compilar.",
            "",
            f"- Material de las tres levas: {valoracion.material_del_cartucho:.2f} €"
            f" — salen {valoracion.levas_por_plancha // 3} cartuchos de una plancha"
            f" de 1 × 1 m",
            f"- Corte del bloque: {valoracion.mecanizado:.2f} €"
            + ("" if valoracion.precio_cerrado else " *(previsión, sin presupuesto)*"),
            f"- **Cartucho, que se rehace en cada pedido: {valoracion.cartucho:.2f} €**",
            f"- Plataforma, que va a stock: {valoracion.plataforma:.2f} €",
            f"- **Total de material y compras: {valoracion.total:.2f} €**",
            "",
            f"Para juzgar ese precio: las tres levas son **{minutos:.1f} min de máquina**"
            f" y a 55 €/h con un amarre y un cuarto de hora de preparación saldrían a"
            f" {valoracion.mecanizado_por_tarifa:.2f} €. El corte es casi todo"
            f" preparación, así que lo que hay que cerrar con el taller no es la tarifa:"
            f" es que **las tres levas salgan de un solo amarre**.",
            "",
        ]
        if valoracion.sin_verificar:
            lineas += [
                "Sin precio verificado: " + ", ".join(valoracion.sin_verificar).rstrip(".") + ".",
                "",
            ]

    lineas += _incidencias("Errores", v.errores)
    if veredicto_energia is not None:
        lineas += _incidencias("Errores del accionamiento", veredicto_energia.errores)
        lineas += _incidencias("Avisos del accionamiento", veredicto_energia.avisos)
    if veredicto_montaje is not None:
        lineas += _incidencias("Errores del conjunto", veredicto_montaje.errores)
        lineas += _incidencias("Avisos del conjunto", veredicto_montaje.avisos)
    lineas += _incidencias("Avisos", v.avisos)
    if v.apto and not v.incidencias:
        lineas += ["Sin incidencias.", ""]

    return "\n".join(lineas)


def escribir_informe(
    compilacion: Compilacion,
    maquina: Escribiente,
    destino: Path | str,
    montaje: Montaje | None = None,
    veredicto_montaje: Veredicto | None = None,
    energia: Energia | None = None,
    veredicto_energia: Veredicto | None = None,
    accionamiento: Accionamiento | None = None,
    valoracion: Valoracion | None = None,
    presupuesto: Presupuesto | None = None,
) -> Path:
    ruta = Path(destino)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        informe(
            compilacion,
            maquina,
            montaje,
            veredicto_montaje,
            energia,
            veredicto_energia,
            accionamiento,
            valoracion,
            presupuesto,
        ),
        encoding="utf-8",
    )
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
