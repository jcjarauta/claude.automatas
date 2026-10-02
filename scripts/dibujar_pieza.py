"""La hoja de una pieza de la plataforma: vistas, cotas y tabla de variables.

    uv run python scripts/dibujar_pieza.py mordaza eje_pivote --out build/

Es el tercero de los tres artefactos que `docs/metodologia.md` §2d pide por
pieza —el DXF, la tabla y el boceto— y **se genera desde el mismo perfil que
escribe el DXF**. Escribir una hoja a mano por pieza era lo que había, y con
tres ya empezaban a divergir: un contorno dibujado y otro cortado es la forma
más cara de descubrir una cota.

Lo que dibuja sale de dos sitios y de ninguno más:

- la **forma**, de `emit.plataforma`, que es la que va al DXF;
- **qué acotar**, de `FICHAS` en `scripts/comparar_dxf.py`, que es lo que el
  comparador va a mirar después.

Esa segunda procedencia es la que importa: **la hoja enseña exactamente lo que
se va a verificar**. Si una cota no está en la ficha no aparece en el dibujo, y
entonces se ve que falta antes de cortar nada.
"""

from __future__ import annotations

import argparse
import math
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emit.plataforma import (
    LISTADO,
    Arco,
    Perfil,
    Segmento,
    base,
    contrato_mm,
    eje_pivote,
    mordaza,
    platina_levas,
    sector,
    seguidor,
    tambor,
    volante,
)
from emit.plataforma import _numero as numero
from emit.plataforma import brazo as brazo_de
from scripts.acotar import ESTILO, FLECHA, auxiliar, cota_h, cota_v, radial
from scripts.comparar_dxf import FICHAS, cotas_en_mm
from scripts.listado_piezas import tabla_markdown  # noqa: F401  (se usa en el test)

CABECERA, PIE = 60.0, 112.0

PERFIL_DE = {
    "brazo_proximal": lambda c: brazo_de("brazo_proximal", c),
    "brazo_distal": lambda c: brazo_de("brazo_distal", c),
    "palanca_lapiz": lambda c: brazo_de("palanca_lapiz", c),
    "manivela": lambda c: brazo_de("manivela", c),
    "mordaza": mordaza,
    "eje_pivote": eje_pivote,
    "sector": sector,
    "tambor": tambor,
    "seguidor": seguidor,
    "platina_levas": platina_levas,
    "volante": volante,
    "base": base,
}
"""De dónde sale la forma de cada pieza.

El sector y el tambor estuvieron fuera «porque son discos y su hoja es
`dibujar_plano_cabestrante.py`». Fuera del bucle salieron las dos a la mitad:
esa hoja rotulaba el canto como radio y el campo del CAD pide diámetro, y sin
ficha en el generador nadie emparejaba las dos cosas."""


def caja(perfil: Perfil) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for e in perfil:
        if isinstance(e, Segmento):
            xs += [e.a[0], e.b[0]]
            ys += [e.a[1], e.b[1]]
        else:
            xs += [e.centro[0] - e.radio, e.centro[0] + e.radio]
            ys += [e.centro[1] - e.radio, e.centro[1] + e.radio]
    return min(xs), min(ys), max(xs), max(ys)


def camino(perfil: Perfil, k: float, ox: float, oy: float) -> list[str]:
    """El perfil en coordenadas de hoja. Cada entidad por separado: así un
    agujero se ve como agujero y no como parte del contorno."""

    def p(x: float, y: float) -> tuple[float, float]:
        return ox + x * k, oy - y * k

    d = []
    for e in perfil:
        if isinstance(e, Segmento):
            a, b = p(*e.a), p(*e.b)
            d.append(
                f'<line class="contorno" x1="{a[0]:.2f}" y1="{a[1]:.2f}" '
                f'x2="{b[0]:.2f}" y2="{b[1]:.2f}"/>'
            )
        elif abs(e.hasta - e.desde - 2 * math.pi) < 1e-9:
            cx, cy = p(*e.centro)
            d.append(
                f'<circle class="contorno" cx="{cx:.2f}" cy="{cy:.2f}" r="{e.radio * k:.2f}"/>'
            )
        else:
            # La Y se invierte al pasar a pantalla, así que el arco
            # antihorario del perfil se dibuja horario en el SVG.
            ini = p(
                e.centro[0] + e.radio * math.cos(e.desde),
                e.centro[1] + e.radio * math.sin(e.desde),
            )
            fin = p(
                e.centro[0] + e.radio * math.cos(e.hasta),
                e.centro[1] + e.radio * math.sin(e.hasta),
            )
            grande = 1 if (e.hasta - e.desde) % (2 * math.pi) > math.pi else 0
            d.append(
                f'<path class="contorno" d="M {ini[0]:.2f},{ini[1]:.2f} '
                f'A {e.radio * k:.2f},{e.radio * k:.2f} 0 {grande} 0 {fin[0]:.2f},{fin[1]:.2f}"/>'
            )
    return d


def _nombre_del_radio(ficha, cotas: dict[str, float], radio: float, tol: float = 1e-6) -> str:
    for nombre in ficha.radios:
        if abs(cotas[nombre] - radio) <= tol:
            return nombre
    return ""


def _horizontales(perfil: Perfil, largo: float, tol: float = 1e-6):
    """Segmentos horizontales de esa longitud, de abajo arriba."""
    return sorted(
        (
            e
            for e in perfil
            if isinstance(e, Segmento)
            and abs(e.a[1] - e.b[1]) <= tol
            and abs(abs(e.a[0] - e.b[0]) - largo) <= tol
        ),
        key=lambda e: e.a[1],
    )


def _verticales(perfil: Perfil, largo: float, tol: float = 1e-6):
    return sorted(
        (
            e
            for e in perfil
            if isinstance(e, Segmento)
            and abs(e.a[0] - e.b[0]) <= tol
            and abs(abs(e.a[1] - e.b[1]) - largo) <= tol
        ),
        key=lambda e: e.a[0],
    )


def _polares(ficha, c: dict[str, float]) -> list[tuple[str, str, list[tuple[float, float]]]]:
    """Los centros de cada grupo polar, con las dos cotas que los sitúan.

    Misma cuenta que hace el perfil, y a propósito: si el dibujo situara los
    agujeros por su cuenta podría enseñar una pieza que el DXF no tiene. Los
    ángulos de `contrato_mm` siguen en radianes —la regla 3— así que aquí no
    se divide por nada.
    """
    salida = []
    for radio, angulo, cuantos in ficha.polares:
        r = c[radio]
        centros = [
            (r * math.cos(c[angulo] * i), r * math.sin(c[angulo] * i))
            if cuantos > 1
            else (r * math.cos(c[angulo]), r * math.sin(c[angulo]))
            for i in range(cuantos)
        ]
        salida.append((radio, angulo, centros))
    return salida


def alto_de_pila(nombre: str, c: dict[str, float]) -> float:
    """Lo que ocupan las cotas horizontales bajo la pieza.

    **El panel sale de aquí, no al revés.** Cada cota come 15 px, y una pieza
    con siete —la mordaza— no cabe en el alto que le sobraba a una con tres.
    Con el alto fijo, las últimas se metían en el porqué, que es texto largo y
    no se puede recortar.
    """
    ficha, cotas, perfil = FICHAS[nombre], cotas_en_mm(), PERFIL_DE[nombre](c)
    cuantas = (
        bool(ficha.voladizo)
        + len(ficha.entre_centros)
        + len(ficha.desde_datum)
        + bool(ficha.ranura)
        + bool(ficha.cara_plana)
        + sum(1 for cota in ficha.segmentos if _horizontales(perfil, cotas[cota]))
    )
    return 16 + 15 * cuantas + (10 if ficha.ranura else 0) + (12 if ficha.simetrico else 0)


def alto_de_leyenda(nombre: str, c: dict[str, float]) -> float:
    """Lo que hay que reservar ENCIMA de la planta, y que empuja el dibujo abajo.

    Son dos cosas y no una: la leyenda que empareja cada Ø con su variable, y
    la banda libre donde aterrizan los rótulos de radio. Si se reserva solo la
    primera los rótulos caen sobre ella —el «R5» del brazo acababa escrito
    encima del nombre de la variable de al lado— y dos rótulos superpuestos
    mienten sin avisar, que es de donde salió un Ø4 dibujado en el datum.
    """
    ficha, cotas, perfil = FICHAS[nombre], cotas_en_mm(), PERFIL_DE[nombre](c)
    vistos = {_nombre_del_radio(ficha, cotas, e.radio) for e in perfil if isinstance(e, Arco)}
    cuantas = len(vistos - {""}) + len(ficha.polares)
    return 7.0 * cuantas + 14.0 if cuantas else 0.0


def alto_de_vista(nombre: str, c: dict[str, float], ancho: float = 230.0) -> float:
    """Lo que la planta necesita de alto para salir a la escala que da el ancho.

    **El alto del panel lo decidía solo la pila de cotas**, y una pieza con
    pocas cotas y mucha superficie se quedaba sin sitio: el sector, que es un
    disco de 96 mm, salía a 0,21:1 —veinte píxeles— porque sus cuatro cotas no
    pedían panel. Una vista a esa escala no sirve para dibujar nada.
    """
    x0, y0, x1, y1 = caja(PERFIL_DE[nombre](c))
    k = min(ancho * 0.46 / max(x1 - x0, 1e-6), 7.0)
    return (y1 - y0) * k


def planta(nombre: str, c: dict[str, float], x: float, y: float, ancho: float, alto: float):
    """La vista de frente, con TODAS las cotas que la ficha declara.

    Acotar solo algunas era el agujero de la primera versión: lo que no
    aparece dibujado se teclea leyéndolo de la tabla sin saber a qué rasgo
    corresponde, y entonces la hoja no sirve para dibujar, solo para
    recordar.
    """
    perfil = PERFIL_DE[nombre](c)
    ficha, cotas = FICHAS[nombre], cotas_en_mm()
    x0, y0, x1, y1 = caja(perfil)
    hueco = alto - CABECERA

    pila, leyenda_alto = alto_de_pila(nombre, c), alto_de_leyenda(nombre, c)
    k = min(
        ancho * 0.46 / max(x1 - x0, 1e-6),
        max(hueco - pila - leyenda_alto - 24, 20.0) / max(y1 - y0, 1e-6),
        7.0,
    )
    # `ox`, `oy` son el (0, 0) de la PIEZA en la hoja, no el centro de su
    # caja, y por eso el alto y el ancho se miden contra `y1`/`x1` y no
    # contra la semicaja. Mientras todas las piezas tuvieron el datum en el
    # centro las dos cuentas daban lo mismo —una barra, un disco y la
    # mordaza son simétricos respecto de su datum— y la diferencia no se
    # veía. La base es la primera que no lo es: su datum es un poste y queda
    # a 59 de un borde y a 216 del otro, así que la planta subía 43 mm sobre
    # su sitio, se metía debajo de la leyenda y dejaba un hueco igual de
    # grande por abajo.
    ox = x + ancho / 2 - ((x0 + x1) / 2) * k
    oy = y + CABECERA + 16 + leyenda_alto + y1 * k
    abajo, derecha = oy - y0 * k, ox + x1 * k

    d = [
        f'<text class="vista" x="{x + ancho / 2:.1f}" y="{y + 12:.1f}">'
        f"planta · escala {k:.2f}:1</text>"
    ]
    d += camino(perfil, k, ox, oy)
    d += [
        f'<line class="eje" x1="{ox - 13:.2f}" y1="{oy:.2f}" x2="{ox + 13:.2f}" y2="{oy:.2f}"/>',
        f'<line class="eje" x1="{ox:.2f}" y1="{oy - 13:.2f}" x2="{ox:.2f}" y2="{oy + 13:.2f}"/>',
        f'<text class="var" x="{ox:.2f}" y="{oy - 17:.2f}">DATUM</text>',
    ]

    # Los radios: la flecha lleva el número y la LEYENDA el nombre.
    #
    # Juntos no caben —un nombre de variable es más ancho que la pieza— y
    # separados hay que emparejarlos de cabeza, que es como se dibujó un Ø4
    # donde iba el Ø3: la tabla tiene dos diámetros y el dibujo solo decía
    # «Ø3». La leyenda los empareja sin que nada se monte.
    #
    # Y el nombre es el que pide el campo: **diámetro** si es un círculo
    # entero, que es como Onshape acota un agujero, y radio si es un arco de
    # contorno.
    #
    # Y el rótulo sale FUERA de la silueta, a una banda por ENCIMA de la
    # planta. Con la directriz de largo fijo el R2 de la ranura aterrizaba a
    # 18 px del Ø3 del datum, y más cerca del agujero que NO describe que del
    # que sí: así se dibujó un Ø4 donde va el Ø3. Arriba porque abajo está la
    # pila de cotas horizontales, y un rótulo de radio cruzándola se lee como
    # parte de ella.
    techo = min(oy - y1 * k, oy - 17.0) - 10.0
    # Clave por RADIO y no por nombre: dos cotas pueden valer lo mismo y
    # entonces son un solo rótulo con dos nombres en la leyenda.
    ocupado_a_la_derecha = 0.0
    """Hasta dónde llega por la derecha un rótulo de polares. La pila de
    cotas verticales empieza más allá: si no, el «Ø24 · 30» del volante
    aterriza encima de la cuerda de la chaveta."""
    puestos: dict[float, str] = {}
    rotulos: list[tuple[float, float, float]] = []
    """Caja de cada rótulo ya puesto: (nivel, x0, x1)."""

    def caja_del_rotulo(xk: float, ang: float, texto: str) -> tuple[float, float]:
        """Dónde cae de verdad el texto, con el mismo anclaje que `radial`.

        Comprobar la separación entre los finales de directriz no basta: con
        anclaje a un lado el texto se extiende hacia fuera, así que dos knees
        separados pueden solaparse igual. Esto mide lo que mide el test.
        """
        ux = math.cos(ang)
        ancho = len(texto) * 2.9
        if ux < -0.2:
            return xk - 2.0 - ancho, xk - 2.0
        if ux > 0.2:
            return xk + 2.0, xk + 2.0 + ancho
        return xk - ancho / 2, xk + ancho / 2

    inclinaciones = (-90.0, -68.0, -112.0, -78.0, -102.0, -60.0)
    for e in perfil:
        if not isinstance(e, Arco):
            continue
        cota = _nombre_del_radio(ficha, cotas, e.radio)
        clave = next((r for r in puestos if abs(r - e.radio) <= 1e-6), e.radio)
        if not cota or clave in puestos:
            continue
        ang = math.radians(inclinaciones[len(puestos) % len(inclinaciones)])
        cx, cy = ox + e.centro[0] * k, oy - e.centro[1] * k
        lleno = abs(e.hasta - e.desde - 2 * math.pi) < 1e-9
        # **Cuántos hay, en la propia flecha.** El seguidor tiene tres Ø3,2 y
        # la directriz solo señala uno: quien dibujaba acotaba ese y dejaba
        # los otros dos sueltos, que es lo que preguntó con un «Ø?» al lado.
        # Decir «3×» es además como se rotula un repetido en cualquier plano.
        cuantos = sum(
            1
            for o in perfil
            if isinstance(o, Arco)
            and abs(o.radio - e.radio) <= 1e-6
            and (abs(o.hasta - o.desde - 2 * math.pi) < 1e-9) == lleno
        )
        marca = f"{cuantos}× " if cuantos > 1 else ""
        texto = marca + (f"Ø{2 * e.radio:g}" if lleno else f"R{e.radio:g}")
        # La separación que hace falta la deciden los DOS textos, no un número
        # fijo: con 22 px valía para «R8» y no para «Ø95.95», que ya mide 20.
        meta = techo
        while True:
            xk = cx + ((meta - cy) / math.sin(ang)) * math.cos(ang)
            x0, x1 = caja_del_rotulo(xk, ang, texto)
            if all(
                x1 + 3.0 < a or b + 3.0 < x0 for nivel, a, b in rotulos if abs(nivel - meta) < 7.0
            ):
                break
            # 12 y no 8: `radial` sube el número 2,4 cuando la directriz es
            # vertical y lo baja 1,9 cuando sale de lado, así que dos niveles
            # separados 8 acaban con los textos a 3,7 y se tocan igual.
            meta -= 12.0
        d += radial(
            cx, cy, e.radio * k, ang, texto, largo=(meta - cy) / math.sin(ang) - e.radio * k
        )
        puestos[e.radio] = texto
        rotulos.append((meta, x0, x1))

    def _como_se_teclea(cota: str, texto: str) -> str:
        """El nombre que pide el campo: diámetro para un círculo entero.

        Se busca por VALOR y no por nombre. Quitar «_radio» funcionaba
        mientras el gemelo se llamara así; `amplificador_sector_radio_
        mecanizado` no lo lleva al final, se quedaba con el radio y el sector
        salió a la mitad.
        """
        # El texto puede venir con el recuento delante —«3× Ø3.2»—, así que
        # lo que decide es el símbolo, no el primer carácter.
        if "Ø" not in texto:
            return cota
        doble = 2.0 * cotas[cota]
        return next(
            (
                n
                for n in (cota.removesuffix("_radio"), f"{cota}_diametro")
                if n != cota and abs(cotas.get(n, 0.0) - doble) <= 1e-6
            ),
            cota,
        )

    # La leyenda agrupa POR VALOR y nombra TODAS las cotas que lo comparten.
    #
    # Dos rasgos distintos pueden medir lo mismo —en el seguidor, el paso del
    # rodillo y los dos del sector son los tres Ø3,2— y entonces la flecha no
    # puede decir cuál es: lo que los distingue es dónde están, y de eso se
    # encargan las cotas de abajo. Nombrando solo al primero, la otra cota
    # quedaba sin aparecer en la hoja y no había manera de saber que existía.
    leyenda = y + CABECERA - 4
    for radio, texto in puestos.items():
        cuales = [n for n in ficha.radios if abs(cotas[n] - radio) <= 1e-6]
        nombres = " · ".join(
            f"#cota.{_como_se_teclea(c, texto)}"
            + (f" ×{ficha.radios[c]}" if len(cuales) > 1 else "")
            for c in cuales
        )
        d.append(
            f'<text class="cotavar" x="{x + 10:.1f}" y="{leyenda:.1f}">{texto} → {nombres}</text>'
        )
        leyenda += 7

    # Los agujeros en POLARES: un rayo desde el datum a cada uno.
    #
    # **Un agujero que no está sobre +X no lo sitúa ninguna cota de la pila**,
    # que mide en horizontal desde el datum. La platina es la primera pieza
    # con agujeros repartidos, y sin esto sus dos números —la distancia y el
    # ángulo— vivían solo en la tabla: se teclean sin saber a qué agujero van,
    # que es justo lo que este bucle existe para evitar.
    #
    # El número va en el rayo y el nombre en la leyenda, igual que los radios.
    for cota_r, cota_a, centros in _polares(ficha, c):
        # **Lo que se rotula es lo que se teclea.** El campo de ángulo mide
        # una magnitud y no acepta el signo, así que un ángulo negativo se
        # escribe en positivo y el lado lo decide dónde cae el rasgo. El
        # gemelo trae ese número; aquí solo se elige cuál de los dos poner.
        teclea, grados = cota_a, math.degrees(c[cota_a])
        lado = ""
        if grados < 0.0:
            teclea, grados, lado = f"{cota_a}_positivo", -grados, " bajo +X"
        cuantos = len(centros)
        # **El diámetro va DELANTE del ángulo.** A 0,62:1 un Ø8 y un Ø10 se
        # distinguen en un píxel, y con los diámetros en una leyenda y las
        # polares en otra nada decía qué agujero era cada uno: la platina
        # volvió dos veces con el tercer poste y el pivote izquierdo
        # cambiados de sitio, cada uno con su radio correcto y el dibujo
        # perfecto. El rótulo que sitúa un agujero tiene que decir cuál es.
        cerca = min(
            (e for e in perfil if isinstance(e, Arco)),
            key=lambda e: math.dist(e.centro, centros[0]),
            default=None,
        )
        cual = f"Ø{2 * cerca.radio:g} · " if cerca else ""
        # **Un patrón se dibuja sobre una circunferencia, y esa se acota en
        # diámetro.** Con más de un agujero nadie los sitúa de uno en uno:
        # se traza una circunferencia de construcción y se repite sobre
        # ella. Ofrecer el radio ahí es el fallo del canto del sector con
        # otra cara, y faltó al dibujar el volante.
        donde, cota_donde = numero(c[cota_r]), cota_r
        if cuantos > 1:
            donde, cota_donde = f"en Ø{numero(2 * c[cota_r])}", f"{cota_r}_diametro"
        for cx_, cy_ in centros:
            d.append(
                f'<line class="eje" x1="{ox:.2f}" y1="{oy:.2f}" '
                f'x2="{ox + cx_ * k:.2f}" y2="{oy - cy_ * k:.2f}"/>'
            )
        # El número va FUERA del contorno, en la prolongación del primer rayo.
        #
        # A media distancia caía sobre el datum y sobre el número del grupo de
        # al lado —el del pivote derecho acababa pegado al de los postes, que
        # salen los dos casi en horizontal—, y dos rótulos superpuestos
        # mienten sin avisar. Fuera los separa el ángulo, que es lo único que
        # los distingue de verdad. Y solo el PRIMER rayo lo lleva: repetido en
        # los tres se lee como tres cotas distintas.
        marca = f"{cuantos}× " if cuantos > 1 else ""
        ang_r = math.atan2(centros[0][1], centros[0][0])
        # Fuera del CONTORNO, no fuera del agujero. Los del volante caen al
        # 58 % del radio, así que «el agujero más doce» dejaba el rótulo
        # dentro de la pieza y encima de la pila de cotas verticales.
        envolvente = max(
            [math.hypot(*e.centro) + e.radio for e in perfil if isinstance(e, Arco)]
            + [math.hypot(*centros[0])]
        )
        fuera = envolvente * k + 12.0
        ancla = "start" if math.cos(ang_r) > 0.3 else "end" if math.cos(ang_r) < -0.3 else "middle"
        # En DOS líneas: de una sola, el rótulo del pivote derecho medía 67 px
        # y se salía de la tarjeta por la izquierda. Partido por el «·» que
        # separa el agujero de su ángulo, ninguna pasa de 35.
        tx, ty = ox + math.cos(ang_r) * fuera, oy - math.sin(ang_r) * fuera
        # El primer rayo se prolonga hasta el número: un rótulo que no toca
        # lo que describe hay que emparejarlo de cabeza, y de ahí salen los
        # errores que este bucle existe para evitar.
        d.append(
            f'<line class="eje" x1="{ox + centros[0][0] * k:.2f}" '
            f'y1="{oy - centros[0][1] * k:.2f}" x2="{tx:.2f}" y2="{ty:.2f}"/>'
        )
        if ancla == "start":
            ocupado_a_la_derecha = max(
                ocupado_a_la_derecha,
                tx
                + 2.9
                * max(len(f"{cual}{numero(c[cota_r])}"), len(f"{marca}{numero(grados)}°{lado}")),
            )
        for i, linea in enumerate((f"{cual}{donde}", f"{marca}{numero(grados)}°{lado}")):
            d.append(
                f'<text class="cotatx" x="{tx:.2f}" y="{ty - 1.2 + 6.5 * i:.2f}" '
                f'style="text-anchor:{ancla}">{linea}</text>'
            )
        d.append(
            f'<text class="cotavar" x="{x + 10:.1f}" y="{leyenda:.1f}">'
            f"{cual}{donde} · {marca}{numero(grados)}°{lado} → "
            f"#cota.{cota_donde} · #angulo.{teclea}</text>"
        )
        leyenda += 7

    # Cotas horizontales, apiladas hacia abajo para que no se monten.
    nivel = abajo + 16
    centros = sorted({e.centro[0] for e in perfil if isinstance(e, Arco)})

    def horizontal(xa: float, xb: float, cota: str, desde_el_centro: bool = False):
        nonlocal nivel
        a, b = ox + xa * k, ox + xb * k
        d.extend([auxiliar(a, oy, a, nivel + 3), auxiliar(b, oy, b, nivel + 3)])
        d.extend(cota_h(a, b, nivel, f"{cotas[cota]:g}"))
        # **Acotar contra un círculo da el canto, no el centro.** La
        # herramienta de distancia del CAD mide lo más corto entre los dos
        # rasgos que se pinchan, así que un círculo contra una línea da la
        # pared y no el eje: la base volvió con el contorno 4 mm corrido,
        # exactamente el radio del agujero datum, con el dibujo impecable.
        # Hay que pinchar el PUNTO central, y la hoja lo dice donde se lee.
        aviso = " · al CENTRO del datum" if desde_el_centro else ""
        d.append(
            f'<text class="cotavar" x="{min(a, b):.2f}" y="{nivel + 9:.2f}">'
            f"#cota.{cota}{aviso}</text>"
        )
        nivel += 15

    if ficha.voladizo:
        # Del datum al borde: es lo único que sitúa el contorno, y sin ella
        # el que dibuja tiene que deducir dónde empieza el bloque.
        horizontal(-cotas[ficha.voladizo], 0.0, ficha.voladizo, desde_el_centro=True)
    for cota in ficha.entre_centros:
        if len(centros) >= 2:
            horizontal(centros[0], centros[-1], cota)
    for cota in ficha.desde_datum:
        horizontal(0.0, cotas[cota], cota, desde_el_centro=True)
    if ficha.ranura:
        radio = cotas[ficha.ranura[1]]
        extremos = sorted(
            e.centro[0] for e in perfil if isinstance(e, Arco) and abs(e.radio - radio) < 1e-6
        )
        if len(extremos) >= 2:
            horizontal(extremos[0], extremos[-1], ficha.ranura[0])
            medio = (extremos[0] + extremos[-1]) / 2
            d.append(
                f'<text class="cotavar" x="{ox + medio * k:.2f}" y="{nivel - 2:.2f}" '
                f'style="text-anchor:middle">CENTRADA en ese punto, '
                f"{(extremos[-1] - extremos[0]) / 2:g} a cada lado</text>"
            )
            nivel += 10
    if ficha.cara_plana:
        horizontal(0.0, cotas[ficha.cara_plana], ficha.cara_plana)
    for cota, _ in ficha.segmentos.items():
        iguales = _horizontales(perfil, cotas[cota])
        if iguales:
            e = iguales[0]
            horizontal(min(e.a[0], e.b[0]), max(e.a[0], e.b[0]), cota)

    if ficha.simetrico:
        # Al final de la pila: arriba choca con la leyenda, y es lo último que
        # se mira porque no es una cota, es una restricción.
        d += [
            f'<line class="eje" x1="{ox + (x0 - 3) * k:.2f}" y1="{oy:.2f}" '
            f'x2="{ox + (x1 + 3) * k:.2f}" y2="{oy:.2f}"/>',
            f'<text class="cotavar" x="{ox + x0 * k:.2f}" y="{nivel:.2f}">'
            "simétrico respecto del eje · el DATUM está sobre él</text>",
        ]
        nivel += 12

    # Y las verticales, a la derecha de todo lo demás.
    lado = max(derecha, ocupado_a_la_derecha) + 22
    for cota, _ in ficha.segmentos.items():
        iguales = _verticales(perfil, cotas[cota])
        if not iguales:
            continue
        e = iguales[-1]
        ya, yb = oy - e.a[1] * k, oy - e.b[1] * k
        d.extend(
            [
                auxiliar(ox + e.a[0] * k, ya, lado + 3, ya),
                auxiliar(ox + e.a[0] * k, yb, lado + 3, yb),
            ]
        )
        d.extend(cota_v(min(ya, yb), max(ya, yb), lado, f"{cotas[cota]:g}"))
        d.append(
            f'<text class="cotavar" x="{lado + 5:.2f}" y="{(ya + yb) / 2:.2f}" '
            f'transform="rotate(-90 {lado + 5:.2f} {(ya + yb) / 2:.2f})">#cota.{cota}</text>'
        )
        lado += 22

    if ficha.retranqueo:
        # Del datum al borde de atrás: es `voladizo` en el otro eje y va en
        # la columna vertical porque es una distancia en Y. Sin ella el
        # rectángulo se dibuja centrado entre los postes, que es lo natural,
        # y la máquina se va 23 mm hacia atrás sobre la tabla.
        ya, yb = oy, oy - y0 * k
        d.extend([auxiliar(ox, ya, lado + 3, ya), auxiliar(ox, yb, lado + 3, yb)])
        d.extend(cota_v(min(ya, yb), max(ya, yb), lado, f"{cotas[ficha.retranqueo]:g}"))
        d.append(
            f'<text class="cotavar" x="{lado + 5:.2f}" y="{(ya + yb) / 2:.2f}" '
            f'transform="rotate(-90 {lado + 5:.2f} {(ya + yb) / 2:.2f})">'
            f"#cota.{ficha.retranqueo} · al CENTRO del datum</text>"
        )
        lado += 22
    return d


def segunda_vista(nombre: str, c: dict[str, float], x: float, y: float, ancho: float, alto: float):
    """La tercera dimensión: sección si es plancha, alzado si es barra.

    Es lo que convierte un contorno en una pieza. Sin ella el espesor vive
    solo en la tabla, y un espesor que no se ve en el dibujo se extruye al
    que tenga puesto el CAD por defecto.
    """
    clase, cota = LISTADO[nombre].solido
    perfil = PERFIL_DE[nombre](c)
    x0, _, x1, y1 = caja(perfil)
    grueso = c[cota]
    largo = (x1 - x0) if clase == "plancha" else grueso
    altura = grueso if clase == "plancha" else 2 * y1
    k = min(ancho * 0.52 / max(largo, 1e-6), (alto - CABECERA) * 0.30 / max(altura, 1e-6), 7.0)
    cx, cy = x + ancho / 2, y + CABECERA + (alto - CABECERA) * 0.20

    titulo = "sección A-A" if clase == "plancha" else "alzado"
    d = [
        f'<text class="vista" x="{cx:.1f}" y="{y + 12:.1f}">{titulo} · escala {k:.2f}:1</text>',
        f'<text class="nota" x="{cx:.1f}" y="{y + 21:.1f}">'
        + (
            "se extruye el contorno: el espesor no está en el DXF"
            if clase == "plancha"
            else "barra de stock cortada a medida, la cara plana recorre todo el largo"
            if FICHAS[nombre].cara_plana
            else "barra de stock cortada a medida, el canto se tornea"
        )
        + "</text>",
    ]
    w, h = largo * k, altura * k
    d.append(
        f'<rect class="corte" x="{cx - w / 2:.2f}" y="{cy - h / 2:.2f}" '
        f'width="{w:.2f}" height="{h:.2f}"/>'
    )
    if clase == "plancha":
        # **Los agujeros que el corte atraviesa, dibujados.** Un rectángulo
        # liso dice el espesor y nada más, y para montar hace falta ver qué
        # pasa de parte a parte y por dónde: un Ø19 que aloja un rodamiento
        # y un Ø8 que recibe un poste se montan distinto y en el contorno se
        # ven igual de redondos.
        #
        # El corte va por y = 0, que es la fila del datum, así que lo que
        # aparece es lo que de verdad cruza esa línea. Lo demás no está, y
        # eso también es información.
        centro_x = (x0 + x1) / 2
        for e in perfil:
            if not isinstance(e, Arco) or abs(e.centro[1]) >= e.radio:
                continue
            media = math.sqrt(e.radio**2 - e.centro[1] ** 2)
            if media * 2 > largo * 0.97:
                continue  # el contorno, no un agujero
            for signo in (-1.0, 1.0):
                xx = cx + (e.centro[0] + signo * media - centro_x) * k
                d.append(
                    f'<line class="oculta" x1="{xx:.2f}" y1="{cy - h / 2:.2f}" '
                    f'x2="{xx:.2f}" y2="{cy + h / 2:.2f}"/>'
                )
        # El datum, para que la sección y la planta se lean en el mismo
        # sentido: sin él la sección se puede montar del revés.
        dx = cx + (0.0 - centro_x) * k
        d += [
            f'<line class="eje" x1="{dx:.2f}" y1="{cy - h / 2 - 14:.2f}" '
            f'x2="{dx:.2f}" y2="{cy + h / 2 + 14:.2f}"/>',
            f'<text class="cotavar" x="{dx:.2f}" y="{cy - h / 2 - 16:.2f}" '
            f'style="text-anchor:middle">DATUM</text>',
            f'<text class="nota" x="{cx - w / 2 + 2:.2f}" y="{cy - h / 2 - 3:.2f}">arriba</text>',
            f'<text class="nota" x="{cx - w / 2 + 2:.2f}" y="{cy + h / 2 + 7:.2f}">abajo</text>',
        ]
    if clase == "barra" and FICHAS[nombre].cara_plana:
        # La cara plana, que recorre el largo entero. **Solo si la pieza la
        # tiene**: el tambor es una barra sin cara plana, y el alzado le
        # dibujaba una con su rótulo, que es una pieza distinta.
        plano = cy - c["brazo_chaveta"] * k
        d.append(
            f'<line class="contorno" x1="{cx - w / 2:.2f}" y1="{plano:.2f}" '
            f'x2="{cx + w / 2:.2f}" y2="{plano:.2f}"/>'
        )
        d.append(f'<text class="cotatx" x="{cx:.2f}" y="{plano - 3:.2f}">cara plana</text>')
    borde = cx + w / 2
    d.append(auxiliar(borde, cy - h / 2, borde + 18, cy - h / 2))
    d.append(auxiliar(borde, cy + h / 2, borde + 18, cy + h / 2))
    if clase == "plancha":
        d += cota_v(cy - h / 2, cy + h / 2, borde + 14, f"{grueso:g}")
        d.append(
            f'<text class="cotavar" x="{borde + 19:.2f}" y="{cy:.2f}" '
            f'transform="rotate(-90 {borde + 19:.2f} {cy:.2f})">#cota.{cota}</text>'
        )
    else:
        d.append(auxiliar(cx - w / 2, cy + h / 2, cx - w / 2, cy + h / 2 + 18))
        d.append(auxiliar(cx + w / 2, cy + h / 2, cx + w / 2, cy + h / 2 + 18))
        d += cota_h(cx - w / 2, cx + w / 2, cy + h / 2 + 14, f"{grueso:g}")
        d.append(
            f'<text class="cotavar" x="{cx - w / 2:.2f}" '
            f'y="{cy + h / 2 + 23:.2f}">#cota.{cota}</text>'
        )
    return d


def alto_de_montaje(nombre: str) -> float:
    """Lo que ocupa la banda EN EL CONJUNTO."""
    montaje = LISTADO[nombre].montaje
    return 6.0 * len(textwrap.wrap(montaje, 84)) + 16.0 if montaje else 0.0


def alto_de_pie(nombre: str) -> float:
    """Lo que ocupa TODO el pie: porqué, montaje y tabla de variables.

    `PIE` era una constante de 112, y no lo es: el porqué tiene las líneas
    que tenga y la tabla, la mitad de las variables de la pieza. Con doce
    —el seguidor— pedía 126 y los dos últimos renglones salían por debajo
    del marco del panel, impresos sobre el borde. Llevaba así desde que la
    pieza entró en el bucle y nadie lo vio porque el panel sigue
    dibujándose entero: lo que se sale es el texto.

    Se reserva por pieza y no por hoja, y `PIE` se queda como suelo.
    """
    lista = LISTADO[nombre]
    porque = 6.0 * len(textwrap.wrap(lista.porque, 84)) + 9.0
    filas = (len(lista.variables) + 1) // 2
    return max(PIE, porque + alto_de_montaje(nombre) + 9.0 + filas * 11.0 + 14.0)


def pie(nombre: str, c: dict[str, float], x: float, y: float, ancho: float):
    """El porqué y la tabla de variables, que es lo que se teclea."""
    from emit.plataforma import _valor

    lista = LISTADO[nombre]
    d = []
    for i, linea in enumerate(textwrap.wrap(lista.porque, 84)):
        d.append(f'<text class="aviso" x="{x + 6:.1f}" y="{y + 6 * i:.1f}">{linea}</text>')
    y += 6 * len(textwrap.wrap(lista.porque, 84)) + 9
    # **El montaje, que no es el porqué.** El porqué justifica las cotas y se
    # lee antes de dibujar; esto dice con qué se junta la pieza y se lee con
    # ella ya cortada, en la mesa. Separados porque se usan en dos momentos
    # distintos y por dos personas distintas.
    if lista.montaje:
        d.append(
            f'<text class="nota" x="{x + 6:.1f}" y="{y:.1f}" '
            'style="text-anchor:start">EN EL CONJUNTO</text>'
        )
        y += 7
        for i, linea in enumerate(textwrap.wrap(lista.montaje, 84)):
            d.append(f'<text class="varl" x="{x + 6:.1f}" y="{y + 6 * i:.1f}">{linea}</text>')
        y += 6 * len(textwrap.wrap(lista.montaje, 84)) + 8
    d.append(
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y:.1f}">'
        "lo que se teclea en el croquis</text>"
    )
    filas = lista.variables
    mitad = (len(filas) + 1) // 2
    for i, v in enumerate(filas):
        col, fila = divmod(i, mitad)
        cx = x + 6 + col * (ancho - 12) / 2
        cy = y + 9 + fila * 11.0
        valor = _valor(c, v)
        unidad = "°" if v.mapa == "angulo" else ""
        marca = "" if v.en_el_perfil else "  (no está en el DXF)"
        d += [
            f'<text class="varl" x="{cx:.1f}" y="{cy:.1f}">#{v.mapa}.{v.nombre}</text>',
            f'<text class="cotatxi" x="{cx + 3:.1f}" y="{cy + 4.8:.1f}">'
            f"{valor}{unidad} · {v.etiqueta}{(' ' + v.sufijo) if v.sufijo else ''}{marca}</text>",
        ]
    return d


def hoja(piezas: list[str] | None = None) -> str:
    piezas = list(PERFIL_DE) if piezas is None else piezas
    c = contrato_mm()
    # Un panel por pieza y a lo ancho: lleva dos vistas, su porqué y su
    # tabla, y partido en dos columnas no cabe ninguna de las tres.
    vista_ancho, borde = 230.0, 12.0
    # Alto por pieza: la que más cotas lleva manda, para que todos los paneles
    # de una hoja midan lo mismo y no bailen.
    alto = (
        PIE
        + 30
        + CABECERA
        + 40
        + max(
            alto_de_pila(n, c) + alto_de_leyenda(n, c) + alto_de_vista(n, c) + alto_de_montaje(n)
            for n in piezas
        )
    )
    ancho = 2 * vista_ancho
    filas = len(piezas)
    w = borde * 2 + ancho
    h = 0.0  # se calcula tras envolver el encabezado
    partes = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w * 2:.0f}" height="{h * 2:.0f}" '
        f'viewBox="0 0 {w:.0f} {h:.0f}">',
        f"<style>{ESTILO}</style><defs>{FLECHA}</defs>",
        f'<rect width="{w:.0f}" height="{h:.0f}" fill="#fff"/>',
        f'<text class="h1" x="{borde}" y="20">Plataforma · {" · ".join(piezas)}</text>',
    ]
    # El encabezado se envuelve al ancho de la hoja: con una sola pieza la
    # hoja es la mitad de ancha y el texto se salía por la derecha. Recortar
    # un rótulo obligatorio no es una opción.
    encabezado = (
        "Cotas en mm, sacadas de docs/contratos.json. La forma es la misma que escribe "
        "el DXF y las cotas son las que mira scripts/comparar_dxf.py: lo que se dibuja "
        "aquí es lo que se verifica. El DXF llega con el rasgo DATUM en el origen: ancla "
        "con DOS coincidentes, acota con las variables de abajo y comprueba que Onshape "
        "diga «totalmente definida». Después exporta el croquis y pásalo por "
        "scripts/comparar_dxf.py. Si algo no cuadra se toca el CONTRATO y se regenera, "
        "nunca el croquis a mano."
    )
    anchura = int((w - 2 * borde) / 2.65)
    lineas = textwrap.wrap(encabezado, anchura)
    for i, linea in enumerate(lineas):
        partes.append(f'<text class="sub" x="{borde}" y="{30 + 8 * i}">{linea}</text>')
    cabecera = 30 + 8 * len(lineas) + 6

    for i, nombre in enumerate(piezas):
        px, py = borde, cabecera + i * alto
        lista = LISTADO[nombre]
        partes += [
            f'<rect class="marco" x="{px:.1f}" y="{py:.1f}" '
            f'width="{ancho:.1f}" height="{alto:.1f}" rx="3"/>',
            f'<text class="h1" x="{px + 8:.1f}" y="{py + 16:.1f}">'
            f"{nombre} · x{lista.cantidad}</text>",
            f'<text class="notal" x="{px + 8:.1f}" y="{py + 25:.1f}">{lista.forma}</text>',
        ]
        # +30 y no +14: el rótulo de la vista caía sobre el subtítulo de la
        # pieza, que es texto largo y no se puede recortar.
        # El alto que se les pasa descuenta el desplazamiento: si no, la vista
        # cree que llega hasta py+alto-PIE y en realidad empieza 30 más abajo,
        # así que la última cota se metía en el porqué.
        # El pie ya no mide siempre lo mismo: `PIE` cubría el porqué y la
        # tabla, y la banda del montaje es tan larga como vecinos tenga la
        # pieza. Reservarlo por pieza y no por hoja es lo que impide que la
        # tabla se salga por abajo del panel.
        suelo = alto_de_pie(nombre)
        partes += planta(nombre, c, px, py + 30, vista_ancho, alto - suelo - 30)
        partes += segunda_vista(
            nombre, c, px + vista_ancho, py + 30, vista_ancho, alto - suelo - 30
        )
        partes += pie(nombre, c, px, py + alto - suelo + 8, ancho)
    partes.append("</svg>")
    h = cabecera + filas * alto + borde
    partes[1] = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w * 2:.0f}" height="{h * 2:.0f}" '
        f'viewBox="0 0 {w:.0f} {h:.0f}">'
    )
    partes[3] = f'<rect width="{w:.0f}" height="{h:.0f}" fill="#fff"/>'
    return "\n".join(partes) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("piezas", nargs="*", choices=list(PERFIL_DE), metavar="pieza")
    p.add_argument("--out", type=Path, default=Path("build/pieza.svg"))
    op = p.parse_args(argv)
    op.out.parent.mkdir(parents=True, exist_ok=True)
    op.out.write_text(hoja(op.piezas or None), encoding="utf-8")
    print(f"hoja en {op.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
