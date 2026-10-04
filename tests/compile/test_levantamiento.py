"""La cadena del levantamiento contra el contrato.

Las cotas que se derivan de la geometría —la bieleta, la x del eje del
balancín— se recalculan aquí y se cruzan con lo que dice el contrato. Si
alguien mueve el seguidor, el poste o el tirante, esto avisa de que la
bieleta ya no es la que está en el contrato.
"""

from __future__ import annotations

import math

import pytest

from compile.contratos import cargar
from compile.escribiente import Escribiente
from compile.levantamiento import (
    apoyo_balancin_alto,
    bieleta_isogona,
    bieleta_pata_seguidor,
    calaje_elevador,
    eje_balancin_x,
    pila,
    tirante_largo,
)


@pytest.fixture(scope="module")
def contratos():
    return cargar()


@pytest.fixture(scope="module")
def bieleta(contratos):
    return bieleta_isogona(contratos, Escribiente())


def _valor(contratos, nombre):
    return float(contratos.variables()[nombre].valor)


def test_el_pasador_del_seguidor_3_no_esta_en_el_eje_de_simetria(bieleta):
    """Es el error que tumbó la bieleta de 25: se dio por hecho que el
    pasador caía en x = 0 del cinco barras, y el seguidor apunta a 9,3° en el
    marco de la leva, no a -90° en el del cinco barras."""
    assert bieleta.pasador[0] == pytest.approx(-0.02941, abs=1e-5)
    assert bieleta.pasador[1] == pytest.approx(0.014549, abs=1e-5)


def test_la_bieleta_es_isogona(bieleta):
    assert bieleta.factor == pytest.approx(1.0, abs=1e-12)


def test_el_contrato_lleva_la_bieleta_que_sale_de_la_geometria(contratos, bieleta):
    assert _valor(contratos, "bieleta_entre_centros") == pytest.approx(bieleta.largo, abs=1e-5)


def test_el_eje_del_balancin_pone_el_tirante_en_su_sitio(contratos):
    x = eje_balancin_x(contratos)
    assert _valor(contratos, "balancin_eje_x") == pytest.approx(x, abs=1e-6)
    palanca = _valor(contratos, "brazo_palanca")
    assert x + palanca * math.cos(calaje_elevador(contratos)) == pytest.approx(
        _valor(contratos, "tirante_x")
    )


def test_el_calaje_del_contrato_es_el_de_media_altura(contratos):
    """El de la cadena es el mismo número que el congelado del compilador."""
    assert calaje_elevador(contratos) == pytest.approx(
        _valor(contratos, "calaje_elevador"), abs=1e-9
    )


def test_la_mesa_baja_lo_que_la_leva_manda(contratos, bieleta):
    """Cinemática exacta, no lineal: el seguidor recorre los 0,475 mm de su
    pasador y la palanca tiene que bajar el tirante los 3 mm de
    altura_levantamiento, no los 2,45 que daba la bieleta de 25."""
    r = _valor(contratos, "levantamiento_pasador_al_pivote")
    e = _valor(contratos, "balancin_entrada")
    palanca = _valor(contratos, "brazo_palanca")
    relacion = Escribiente().relacion
    calaje = calaje_elevador(contratos)
    medio_giro = calaje / relacion  # lo que se desvía el seguidor a cada lado
    psi0 = math.atan2(
        bieleta.pasador[1] - bieleta.pivote[1], bieleta.pasador[0] - bieleta.pivote[0]
    )

    def giro_del_eje(dpsi):
        sx = bieleta.pivote[0] + r * math.cos(psi0 + dpsi)
        sy = bieleta.pivote[1] + r * math.sin(psi0 + dpsi)

        def resto(g):
            ox = bieleta.ojo[0] + e * math.sin(g)
            return math.hypot(ox - sx, bieleta.ojo[1] - sy) - bieleta.largo

        a, b = -0.5, 0.5
        for _ in range(100):
            g = (a + b) / 2
            a, b = (g, b) if (resto(g) > 0) == (resto(a) > 0) else (a, g)
        return (a + b) / 2

    baja = palanca * (math.sin(giro_del_eje(medio_giro)) - math.sin(giro_del_eje(-medio_giro)))
    assert baja == pytest.approx(0.003, abs=2e-6)


@pytest.mark.parametrize(
    ("nombre", "derivada"),
    [
        ("apoyo_balancin_alto", apoyo_balancin_alto),
        ("bieleta_pata_seguidor", bieleta_pata_seguidor),
        ("tirante_largo", tirante_largo),
    ],
)
def test_las_cotas_derivadas_de_la_pila_son_las_del_contrato(contratos, nombre, derivada):
    """Las tres cruzan la pila de alturas: si alguien mueve un plato o un
    seguidor, esto dice cuál ya no vale."""
    assert _valor(contratos, nombre) == pytest.approx(derivada(contratos), abs=2e-6)


def test_el_balancin_libra_los_seguidores(contratos):
    """Apunta hacia arriba: lo que baja por debajo del eje es su cubo, y
    tiene que quedar a holgura_minima de la cara alta de los seguidores."""
    p = pila(contratos)
    cubo_abajo = p.eje_balancin - _valor(contratos, "balancin_cubo_diametro") / 2
    seguidores_arriba = p.seguidores + _valor(contratos, "seguidor_espesor")
    assert cubo_abajo - seguidores_arriba == pytest.approx(_valor(contratos, "holgura_minima"))


def test_los_apoyos_no_alcanzan_los_sectores_en_planta(contratos):
    """En altura sí coinciden —el apoyo baja hasta 5 bajo el eje y el sector
    sube 5 sobre los seguidores—, así que lo que los separa es la planta: los
    sectores giran sobre los postes 1 y 2, y su canto no llega a los apoyos."""
    from compile.levantamiento import al_cinco_barras

    maquina = Escribiente()
    radio_sector = _valor(contratos, "amplificador_sector_radio_mecanizado")
    medio_apoyo = math.hypot(
        _valor(contratos, "apoyo_balancin_ancho") / 2, _valor(contratos, "apoyo_balancin_fondo") / 2
    )
    x = _valor(contratos, "balancin_eje_x")
    for i in (0, 1):
        pivote = maquina.seguidor(i).pivote
        centro = al_cinco_barras(contratos, float(pivote[0]), float(pivote[1]))
        for nombre in ("apoyo_balancin_trasero_y", "apoyo_balancin_delantero_y"):
            hueco = math.dist(centro, (x, _valor(contratos, nombre))) - radio_sector - medio_apoyo
            assert hueco > _valor(contratos, "holgura_minima"), (i, nombre, hueco)


def test_la_cadena_baja_la_mesa_lo_que_el_compilador_levanta(contratos):
    """El lazo cerrado de verdad, en todo el ciclo: la desviación del seguidor
    3 que da la leva sintetizada → la bieleta → el eje → la palanca → la mesa,
    contra la altura que el compilador manda con su modelo de palanca. Y en
    el mismo SENTIDO: con el balancín colgando, la mesa subía al levantar."""
    from pathlib import Path

    import numpy as np

    from compile.conjunto import estados
    from compile.escribiente import compilar
    from scripts.exportar_para_cad import leer

    maquina = Escribiente()
    compilacion = compilar(leer(Path(__file__).resolve().parents[2] / "demo" / "hola.json"))
    thetas = np.linspace(0.0, 2.0 * np.pi, 72, endpoint=False)
    palanca = _valor(contratos, "brazo_palanca")
    calaje = calaje_elevador(contratos)
    peor = 0.0
    for e in estados(compilacion, maquina, thetas):
        manda = palanca * math.sin(e.desviaciones[2] * maquina.relacion + calaje)
        peor = max(peor, abs(e.caida_mesa - manda))
    assert peor < 5e-6, f"la mesa se separa {peor * 1e6:.1f} µm de lo que manda el compilador"


def test_el_largo_del_eje_del_balancin_es_el_que_sale_de_la_cadena(contratos):
    """Del codo de la bieleta, cuya pata atraviesa el balancín, al bulón del
    tirante, que tiene que caer en tirante_y; y 2 de margen a cada punta."""
    from compile.levantamiento import eje_balancin

    eje = eje_balancin(contratos)
    assert _valor(contratos, "balancin_eje_largo") == pytest.approx(eje.largo, abs=1e-6)


def test_el_contrato_lleva_el_ojo_de_la_bieleta(contratos, bieleta):
    """El montaje no importa el compilador: coloca el eje del balancín con
    este número, así que tiene que ser el que sale de la bieleta isógona."""
    assert _valor(contratos, "balancin_ojo_y") == pytest.approx(bieleta.ojo[1], abs=1e-9)
