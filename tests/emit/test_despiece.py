"""El despiece pieza a pieza: pilas derivadas de los ejes, números que se
leen sin pisarse ni tapar líneas, y cada número sobre una línea visible de
su pieza. Lo puro se prueba sin kernel; lo demás, con los grupos de verdad."""

from __future__ import annotations

import math

import pytest

from emit.despiece import (
    Cilindro,
    caja_de_texto,
    coaxiales,
    colocar_etiquetas,
    corta,
    ordenar_pila,
    texto_corto,
    texto_de,
)
from emit.numeracion import Marca

# ---------------------------------------------------------------------------
# Lo puro
# ---------------------------------------------------------------------------


def test_texto_corto_en_la_hoja_de_su_grupo_y_de_otro():
    assert texto_corto(Marca("amplificador", "AMP", "piezas", 3, "tambor"), "amplificador") == "3"
    assert (
        texto_corto(Marca("amplificador", "AMP", "comerciales", 1, "cinta"), "amplificador") == "C1"
    )
    assert texto_corto(Marca("amplificador", "AMP", "tornilleria", 7, "x"), "amplificador") == "T7"
    otra = Marca("cinco_barras", "CBR", "piezas", 5, "anillo_proximal")
    assert texto_corto(otra, "amplificador") == "CBR-5"
    assert texto_corto(otra, "cinco_barras") == "5"


def test_texto_de_una_pieza_colocada():
    from emit.materiales import tornilleria

    sector = [f for f in tornilleria() if f.en_3d in ("tornillo_sector_", "tuerca_sector_")]
    marcas = {
        ("piezas", "sector"): Marca("amplificador", "AMP", "piezas", 4, "sector"),
        ("piezas", "anillo_proximal"): Marca("cinco_barras", "CBR", "piezas", 5, "anillo_proximal"),
        ("comerciales", "cinta_amplificador"): Marca(
            "amplificador", "AMP", "comerciales", 1, "cinta_amplificador"
        ),
    }
    for i, f in enumerate(sector, start=1):
        marcas[("tornilleria", f.clave)] = Marca("amplificador", "AMP", "tornilleria", i, f.clave)
    colocados = {"cinta_amplificador": "cinta_"}
    assert texto_de("sector_2", "amplificador", marcas, colocados) == "4"
    assert texto_de("anillo_proximal_1", "amplificador", marcas, colocados) == "CBR-5"
    assert texto_de("cinta_1", "amplificador", marcas, colocados) == "C1"
    # El tornillo y su tuerca son dos piezas, con su marca cada una.
    assert len(sector) == 2
    assert texto_de("tornillo_sector_1_1", "amplificador", marcas, colocados) == "T1"
    assert texto_de("tuerca_sector_1_2", "amplificador", marcas, colocados) == "T2"
    assert texto_de("leva_x_1", "levas", marcas, colocados) == ""


@pytest.mark.parametrize(
    ("a", "b", "esperado"),
    [
        ((-1.0, 0.5), (2.0, 0.5), True),  # la atraviesa
        ((0.2, 0.2), (0.8, 0.8), True),  # dentro entera
        ((-1.0, -1.0), (-0.5, 2.0), False),  # pasa al lado
        ((-1.0, 2.0), (2.0, 2.0), False),  # paralela, por encima
        ((-1.0, 0.0), (1.0, 2.0), True),  # toca la esquina
        ((-1.0, 1.5), (1.5, -1.0), True),  # corta una esquina
        ((-1.0, 3.5), (3.5, -1.0), False),  # pasa la esquina sin tocarla
    ],
)
def test_corta_segmento_y_caja(a, b, esperado):
    assert corta(a, b, (0.0, 0.0, 1.0, 1.0)) is esperado
    assert corta(b, a, (0.0, 0.0, 1.0, 1.0)) is esperado


def test_pila_con_eje_saca_arriba_y_abajo_en_orden():
    tramos = {"eje": (0.0, 70.0), "tambor": (60.0, 66.0), "circlip": (66.0, 67.0), "bajo": (2, 4)}
    d = ordenar_pila(tramos, "eje", hueco=7.0)
    assert d["eje"] == 0.0
    assert 60.0 + d["tambor"] == pytest.approx(77.0)
    assert 66.0 + d["circlip"] == pytest.approx(66.0 + d["tambor"] + 7.0)
    assert 4.0 + d["bajo"] == pytest.approx(-7.0)


def test_pila_sin_eje_deja_la_mas_baja():
    tramos = {"sector": (108.0, 113.0), "calzo": (105.0, 108.0), "mordaza": (113.0, 119.0)}
    d = ordenar_pila(tramos, None, hueco=7.0)
    assert d["calzo"] == 0.0
    assert 108.0 + d["sector"] == pytest.approx(115.0)
    assert 113.0 + d["mordaza"] == pytest.approx(113.0 + d["sector"] + 7.0)


def test_pila_sigue_saliendo_hasta_despejar():
    """Si la posición no vale (taparía a la de debajo), sale de paso en paso."""
    tramos = {"calzo": (0.0, 3.0), "disco": (3.0, 8.0)}
    d = ordenar_pila(tramos, None, hueco=7.0, despejado=lambda n, s, _: s >= 30.0, paso=2.0)
    # Empieza a 7 (el hueco) y sube de 2 en 2: el primero que vale es 31.
    assert d["disco"] == pytest.approx(31.0)


def test_coaxiales():
    z = (0.0, 0.0, 1.0)
    a = Cilindro(10.0, (1.0, 2.0, 0.0), z, 0.0, 5.0)
    assert coaxiales(a, Cilindro(3.0, (1.1, 2.0, 0.0), z, 9.0, 12.0))
    assert not coaxiales(a, Cilindro(3.0, (1.5, 2.0, 0.0), z, 0.0, 5.0))
    inclinado = (math.sin(math.radians(2)), 0.0, math.cos(math.radians(2)))
    assert not coaxiales(a, Cilindro(10.0, (1.0, 2.0, 0.0), inclinado, 0.0, 5.0))


def test_etiquetas_no_se_pisan_ni_cortan_lineas():
    # Una rejilla de líneas y anclas juntas: todas tienen que encontrar sitio.
    lineas = [((float(x), 0.0), (float(x), 40.0)) for x in range(0, 41, 10)]
    lineas += [((0.0, float(y)), (40.0, float(y))) for y in range(0, 41, 10)]
    anclas = [(f"p{i}", str(i), (20.0 + i * 0.5, 20.0)) for i in range(6)]
    etiquetas = colocar_etiquetas(anclas, lineas, letra=3.0)
    assert sorted(e.texto for e in etiquetas) == [str(i) for i in range(6)]
    for i, e in enumerate(etiquetas):
        assert e.caja == caja_de_texto(e.texto, e.posicion, 3.0)
        assert not any(corta(a, b, e.caja) for a, b in lineas)
        for o in etiquetas[i + 1 :]:
            assert not (
                e.caja[0] < o.caja[2]
                and o.caja[0] < e.caja[2]
                and e.caja[1] < o.caja[3]
                and o.caja[1] < e.caja[3]
            )
    assert colocar_etiquetas(anclas, lineas, letra=3.0) == etiquetas


# ---------------------------------------------------------------------------
# Con el kernel, los grupos de verdad
# ---------------------------------------------------------------------------

GRUPOS = ("amplificador", "cinco_barras", "seguidores")


@pytest.fixture(scope="module", params=GRUPOS)
def caso(request):
    pytest.importorskip("build123d", reason="hace falta el kernel: uv sync --group cad")
    from emit.despiece import despiece
    from emit.numeracion import cargar, marcas
    from scripts.fichas import preparar
    from scripts.numeracion import COMERCIALES_COLOCADOS

    g = preparar(request.param)
    todas = marcas(cargar())
    d = despiece(g.contexto, request.param, todas, COMERCIALES_COLOCADOS)
    return request.param, g, todas, d


def _esperadas(grupo, contexto, todas):
    """Lo que el registro dice que lleva cada pieza colocada del grupo, leído
    por su camino propio: la clave del LISTADO, la línea de tornillería que
    la dibuja o el comercial que se coloca con ese nombre."""
    from emit.fichas import base_de
    from emit.materiales import tornilleria
    from emit.montaje import grupo_de
    from scripts.numeracion import COMERCIALES_COLOCADOS

    salida = {}
    for n, _ in contexto:
        if grupo_de(n).nombre != grupo:
            continue
        ms = []
        if ("piezas", base_de(n)) in todas:
            ms = [todas[("piezas", base_de(n))]]
        if not ms:
            ms = sorted(
                {
                    todas[("tornilleria", f.clave)]
                    for f in tornilleria()
                    if f.en_3d and n.startswith(f.en_3d)
                },
                key=lambda m: m.numero,
            )
        if not ms:
            ms = [
                todas[("comerciales", c)]
                for c, pre in COMERCIALES_COLOCADOS.items()
                if n.startswith(pre) and ("comerciales", c) in todas
            ]
        if ms:
            letra = {"piezas": "", "comerciales": "C", "tornilleria": "T"}
            salida[n] = ", ".join(
                f"{letra[m.serie]}{m.numero}"
                if m.grupo == grupo
                else f"{m.sigla}-{letra[m.serie]}{m.numero}"
                for m in ms
            )
    return salida


def _solapan(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


@pytest.mark.slow
def test_cada_pieza_con_marca_lleva_su_numero(caso):
    grupo, g, todas, d = caso
    esperadas = _esperadas(grupo, g.contexto, todas)
    assert esperadas, "el grupo no tiene nada con marca"
    assert d.ocultas == [], f"piezas tapadas en el despiece de {grupo}: {d.ocultas}"
    assert {e.nombre: e.texto for e in d.etiquetas} == esperadas
    # Lo fabricado del grupo, al menos, está todo.
    numeros = {e.texto for e in d.etiquetas}
    assert {str(p.marca) for p in g.piezas} <= numeros


@pytest.mark.slow
def test_numeros_sin_pisarse_ni_cortar_lineas(caso):
    from shapely.geometry import LineString, box

    _, _, _, d = caso
    lineas = [LineString(p) for p in d.lineas if len(p) > 1]
    for i, e in enumerate(d.etiquetas):
        caja = box(*e.caja)
        assert not any(caja.intersects(linea) for linea in lineas), f"{e.texto} corta una línea"
        for o in d.etiquetas[i + 1 :]:
            assert not _solapan(e.caja, o.caja), f"{e.texto} pisa a {o.texto}"


@pytest.mark.slow
def test_cada_ancla_esta_sobre_una_linea_visible_de_su_pieza(caso):
    from shapely.geometry import MultiLineString, Point

    _, _, _, d = caso
    visibles = MultiLineString([p for p in d.lineas if len(p) > 1])
    for e in d.etiquetas:
        assert visibles.distance(Point(e.ancla)) < 0.06, e.texto
        x0, y0, x1, y1 = d.cajas[e.nombre]
        assert x0 - 0.01 <= e.ancla[0] <= x1 + 0.01
        assert y0 - 0.01 <= e.ancla[1] <= y1 + 0.01


@pytest.mark.slow
def test_cada_pieza_movida_tiene_una_linea_de_montaje(caso):
    _, _, _, d = caso
    nombres = [n for n, _, _ in d.montaje]
    assert len(nombres) == len(set(nombres))
    for n, a, b in d.montaje:
        assert math.dist(a, b) > 1.0, n
    for p in d.pilas:
        queda = p.eje if p.eje is not None else p.orden[0]
        movidas = [n for n in p.todas if n != queda]
        assert set(movidas) <= set(nombres), set(movidas) - set(nombres)


@pytest.mark.slow
def test_pilas_sin_solapes(caso):
    from emit.despiece import HUECO

    _, _, _, d = caso
    for p in d.pilas:
        for a, b in zip(p.orden, p.orden[1:], strict=False):
            assert p.tramos[b][0] >= p.tramos[a][1] + HUECO - 0.05, (a, b)
    cajas = []
    for p in d.pilas:
        suyas = [d.cajas[n] for n in p.todas]
        cajas.append(
            (
                min(c[0] for c in suyas),
                min(c[1] for c in suyas),
                max(c[2] for c in suyas),
                max(c[3] for c in suyas),
            )
        )
    for i, a in enumerate(cajas):
        for b in cajas[i + 1 :]:
            assert not _solapan(a, b), (d.pilas[cajas.index(a)].todas, b)


@pytest.mark.slow
def test_las_pilas_salen_de_los_ejes(caso):
    """Las pilas no se declaran: el eje de pivote enhebra su tambor, el
    perno del codo sus dos brazos."""
    grupo, _, _, d = caso
    por_eje = {p.eje: set(p.piezas) for p in d.pilas if p.eje}
    if grupo == "amplificador":
        assert {"tambor_1", "circlip_tambor_1"} <= por_eje["eje_pivote_1"]
        sector = next(p for p in d.pilas if "sector_1" in p.piezas)
        assert {"calzo_sector_1", "mordaza_1"} <= set(sector.piezas)
        assert {"tornillo_sector_1_1", "tornillo_sector_1_2"} <= set(sector.tornillos)
        # La tuerca sale por el otro lado: también es de la pila.
        assert {"tuerca_sector_1_1", "tuerca_sector_1_2"} <= set(sector.tornillos)
    elif grupo == "cinco_barras":
        assert {"proximal_1", "distal_1", "arandela_codo_1"} <= por_eje["perno_codo_1"]
    else:
        rodillo = next(p for p in d.pilas if "rodillo_1" in p.piezas)
        assert "casquillo_rodillo_1" in rodillo.piezas
        assert "tuerca_rodillo_1" in rodillo.tornillos


@pytest.mark.slow
def test_determinista(caso):
    from emit.despiece import despiece
    from scripts.numeracion import COMERCIALES_COLOCADOS

    grupo, g, todas, d = caso
    assert despiece(g.contexto, grupo, todas, COMERCIALES_COLOCADOS) == d


@pytest.mark.slow
def test_encajar_en_la_hoja(caso):
    from emit.despiece import encajar, extension

    _, _, _, d = caso
    e = encajar(d, 10.0, 10.0, 277.0, 190.0, letra=3.5)
    x0, y0, x1, y1 = extension(e)
    assert x0 >= 10.0 - 1e-6
    assert y0 >= 10.0 - 1e-6
    assert x1 <= 287.0 + 1e-6
    assert y1 <= 200.0 + 1e-6
    assert e.letra <= 3.5 + 1e-9
    assert e.letra > 2.5
    for i, a in enumerate(e.etiquetas):
        for b in e.etiquetas[i + 1 :]:
            assert not _solapan(a.caja, b.caja)
    assert [x.texto for x in e.etiquetas] == [x.texto for x in d.etiquetas]


def test_lado_de_la_cabeza():
    pytest.importorskip("build123d", reason="hace falta el kernel: uv sync --group cad")
    from build123d import Pos, Rot

    from emit.despiece import _principal, cilindros_de, lado_de_la_cabeza
    from emit.fijaciones import allen, avellanado, prisionero, tuerca

    def lado(s):
        return lado_de_la_cabeza(s, _principal(cilindros_de(s)))

    assert lado(allen(3.0, 16.0)) == 1.0
    assert lado(avellanado(3.0, 12.0)) == 1.0
    # Boca abajo y en otro sitio: la cabeza, abajo.
    assert lado(Pos(5, 7, 30) * Rot(X=180) * allen(3.0, 16.0)) == -1.0
    assert lado(tuerca(3.0)) == 0.0
    assert lado(prisionero(3.0, 6.0)) == 0.0


def _relativo(d, p, n):
    """Lo que sale n de su sitio dentro de su pila, a lo largo del eje."""
    total = d.desplazamientos[n]
    return sum((total[i] - p.empuje[i]) * p.direccion[i] for i in range(3))


@pytest.mark.slow
def test_tornillos_por_su_cabeza_y_tuercas_al_otro_lado(caso):
    """Un tornillo sale por el lado de su cabeza, que es por donde entró;
    su tuerca, por el contrario. La cabeza se mira aquí por su cuenta: el
    cilindro más gordo, a qué lado del centro del tornillo está."""
    from emit.despiece import cilindros_de, coaxiales, paralelos

    _, g, _, d = caso
    solidos = dict(g.contexto)
    vistos = 0
    for p in d.pilas:
        for t in p.tornillos:
            if not t.startswith("tornillo_"):
                continue
            cs = cilindros_de(solidos[t])
            gordo = max(cs, key=lambda c: (c.diametro, c.desde))
            if not paralelos(gordo.direccion, p.direccion):
                continue
            b = solidos[t].bounding_box().center()
            centro = b.X * p.direccion[0] + b.Y * p.direccion[1] + b.Z * p.direccion[2]
            signo = 1.0 if sum(gordo.direccion[i] * p.direccion[i] for i in range(3)) > 0 else -1.0
            cabeza = signo * ((gordo.desde + gordo.hasta) / 2) - centro
            assert _relativo(d, p, t) * cabeza > 0, t
            vistos += 1
            for n in p.tornillos:
                if n.startswith("tuerca_") and any(
                    coaxiales(x, y) for x in cilindros_de(solidos[n]) for y in cs
                ):
                    assert _relativo(d, p, n) * cabeza < 0, n
    if any(n.startswith("tornillo_sector_") for n, _ in g.contexto if n in d.desplazamientos):
        assert vistos >= 4
    # Toda tuerca del grupo está en una pila y se ha movido.
    for p in d.pilas:
        for n in p.tornillos:
            if n.startswith("tuerca_"):
                assert abs(_relativo(d, p, n)) > 1.0, n


@pytest.mark.slow
def test_proporcion_cerca_de_la_del_hueco(caso):
    """Las pilas que se pisan se apartan también de lado: el despiece no
    queda en una columna alta y estrecha en un hueco casi cuadrado."""
    from emit.despiece import extension

    grupo, _, _, d = caso
    x0, y0, x1, y1 = extension(d)
    proporcion = (x1 - x0) / (y1 - y0)
    assert 0.5 < proporcion < 2.0
    if grupo == "amplificador":
        # Solo por el eje del grupo salía una columna de 0,45; de lado, ~0,9.
        assert proporcion > 0.75
    # En el cinco barras, poner los dos canales uno al lado del otro saldría
    # más ancho que alto de lo que gana: se quedan uno encima del otro.
