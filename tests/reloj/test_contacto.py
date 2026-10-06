"""C12c · el contacto del escape, en función de θ: lo que la dinámica necesita.

`core/reloj/graham.py` dice si el escape funciona girando el áncora y dejando
avanzar la rueda. La dinámica necesita más: **dónde** se tocan diente y
paleta, **en qué dirección** empuja uno al otro y con qué brazo sobre cada
eje. Aquí se comprueba que esa geometría dice lo mismo que la marcha por un
camino distinto: la ligadura φ(θ) sale de buscar el contacto, y su pendiente
tiene que coincidir con la relación de brazos que sale de la normal.

Todo es función de θ (regla 1): ni un segundo.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from compile.escape_r2 import geometria
from core.reloj.contacto import TablaDeContacto, brazos, tabla_de_contacto
from core.reloj.graham import marcha
from core.units import grados

pytestmark = pytest.mark.core

AMPLITUD = grados(3.0)


@pytest.fixture(scope="module")
def tablas() -> dict[str, TablaDeContacto]:
    rueda, ancora = geometria()
    return {
        lado: tabla_de_contacto(rueda, ancora, lado, amplitud=grados(6.0), paso=grados(0.02))
        for lado in ("entrada", "salida")
    }


def _tramos(t: TablaDeContacto) -> tuple[np.ndarray, np.ndarray]:
    """(en reposo, en impulso): máscaras sobre la rejilla."""
    pendiente = np.gradient(t.phi, t.theta)
    definido = np.isfinite(t.phi)
    reposo = definido & (np.abs(pendiente) < 1e-3)
    impulso = definido & (np.abs(pendiente) > 0.05)
    return reposo, impulso


@pytest.mark.parametrize("lado", ["entrada", "salida"])
def test_cada_paleta_tiene_reposo_e_impulso(tablas, lado):
    reposo, impulso = _tramos(tablas[lado])
    assert reposo.sum() > 50
    assert impulso.sum() > 20


@pytest.mark.parametrize("lado", ["entrada", "salida"])
def test_en_reposo_la_normal_pasa_por_el_eje_del_ancora(tablas, lado):
    """Lo que hace de Graham un escape de reposo: el arco tiene el centro en el
    eje del áncora, así que la fuerza del diente no da par sobre el péndulo.
    Solo el rozamiento lo frena."""
    t = tablas[lado]
    reposo, _ = _tramos(t)
    _, h_an = brazos(t, t.eje_ancora)
    assert np.max(np.abs(h_an[reposo])) < 1e-6  # m: un micrómetro de brazo


@pytest.mark.parametrize("lado", ["entrada", "salida"])
def test_la_ligadura_es_la_relacion_de_brazos(tablas, lado):
    """Dos caminos al mismo número. La pendiente de φ(θ), buscando el contacto,
    y la que sale de la normal: la velocidad normal del diente y la de la
    paleta en el punto de contacto son la misma, así que
    dφ/dθ = -h_áncora / h_rueda. Si no coinciden, la normal está mal."""
    t = tablas[lado]
    _, impulso = _tramos(t)
    # Lejos de los bordes del tramo, donde la pendiente numérica no vale.
    nucleo = impulso & np.roll(impulso, 3) & np.roll(impulso, -3)
    h_wn, h_an = brazos(t, t.eje_ancora)
    por_brazos = -h_an[nucleo] / h_wn[nucleo]
    por_busqueda = np.gradient(t.phi, t.theta)[nucleo]
    assert por_brazos == pytest.approx(por_busqueda, rel=0.03)


@pytest.mark.parametrize("lado", ["entrada", "salida"])
def test_en_impulso_la_rueda_empuja_al_ancora_hacia_donde_va(tablas, lado):
    """En el impulso la rueda avanza (φ crece) y el diente empuja la paleta
    para fuera: el áncora gira hacia el lado que suelta el diente."""
    t = tablas[lado]
    _, impulso = _tramos(t)
    pendiente = np.gradient(t.phi, t.theta)[impulso]
    signo = 1.0 if lado == "salida" else -1.0
    assert np.all(np.sign(pendiente) == signo)


def test_la_rueda_avanza_medio_diente_por_golpe(tablas):
    """Lo que avanza la rueda entre que un diente apoya en la entrada y el
    siguiente en la salida: medio paso, 6°, como en la marcha."""
    rueda, _ = geometria()
    entrada, salida = tablas["entrada"], tablas["salida"]
    golpe = abs(float(np.nanmin(salida.phi) - np.nanmin(entrada.phi)))
    medio = rueda.paso / 2
    resto = (golpe - medio) % rueda.paso
    assert min(resto, rueda.paso - resto) < grados(0.05)


def test_la_tabla_dice_lo_mismo_que_la_marcha(tablas):
    """El reposo de la marcha a ±3° es el mismo φ que el de la tabla, salvo
    el diente de referencia: la cinemática y el contacto son dos programas."""
    rueda, ancora = geometria()
    m = marcha(rueda, ancora, AMPLITUD, oscilaciones=1)
    paso = rueda.paso
    for t in tablas.values():
        reposo, _ = _tramos(t)
        nivel = float(np.median(t.phi[reposo]))
        distancias = [((float(p) - nivel) / paso) % 1.0 for p in np.unique(np.round(m.phi, 5))]
        assert min(min(d, 1 - d) for d in distancias) < grados(0.05) / paso


def test_no_hay_tiempo_en_la_tabla(tablas):
    """Regla 1: la tabla es función de θ y nada más."""
    t = tablas["entrada"]
    nombres = {f for f in t.__dataclass_fields__}
    assert not any(n in nombres for n in ("t", "tiempo", "dt"))
    assert math.isfinite(float(np.nanmax(t.phi)))
