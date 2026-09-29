"""C1 · Cinemática inversa: el brazo de cinco barras y la palanca elevadora."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core.actors import BrazoCincoBarras, PalancaElevadora, claves, construir
from core.errors import ActuadorDesconocido, FueraDeAlcance
from core.units import mm

pytestmark = pytest.mark.core


def brazo() -> BrazoCincoBarras:
    return BrazoCincoBarras(separacion=mm(60.0), proximal=mm(55.0), distal=mm(70.0))


def puntos_de_trabajo() -> np.ndarray:
    """Una rejilla de puntos dentro de la zona útil del brazo."""
    x = np.linspace(-0.020, 0.020, 9)
    y = np.linspace(0.055, 0.085, 7)
    malla_x, malla_y = np.meshgrid(x, y)
    return np.column_stack((malla_x.ravel(), malla_y.ravel()))


# ---------------------------------------------------------------------------
# Ida y vuelta
# ---------------------------------------------------------------------------


def test_la_directa_deshace_la_inversa():
    """Si la ida y la vuelta no coinciden, una de las dos está mal."""
    objetivo = puntos_de_trabajo()
    recuperado = brazo().directa(brazo().inversa(objetivo))
    assert np.allclose(recuperado, objetivo, atol=1e-12)


@settings(max_examples=200, deadline=None)
@given(
    x=st.floats(min_value=-0.020, max_value=0.020),
    y=st.floats(min_value=0.055, max_value=0.085),
)
def test_la_ida_y_vuelta_aguanta_cualquier_punto_de_la_zona(x: float, y: float):
    objetivo = np.array([[x, y]])
    recuperado = brazo().directa(brazo().inversa(objetivo))
    assert np.allclose(recuperado, objetivo, atol=1e-9)


# ---------------------------------------------------------------------------
# Rama única
# ---------------------------------------------------------------------------


def test_la_rama_no_cambia_a_lo_largo_del_ciclo():
    """Un cambio de rama a media vuelta sale en la leva como un salto, y una
    leva con un salto no se puede fabricar."""
    t = np.linspace(0.0, 2.0 * np.pi, 720, endpoint=False)
    recorrido = np.column_stack((0.018 * np.cos(t), 0.070 + 0.012 * np.sin(t)))
    psi = brazo().inversa(recorrido)
    saltos = np.abs(np.diff(psi, axis=0))
    assert float(saltos.max()) < 0.05, "hay un salto: la inversa ha cambiado de rama"


def test_psi_vuelve_a_su_valor_al_cerrar_el_ciclo():
    """Una trayectoria cerrada deja el brazo donde estaba. Si ψ no vuelve, es
    que ha dado una vuelta neta y la leva no cerraría."""
    t = np.linspace(0.0, 2.0 * np.pi, 720, endpoint=False)
    recorrido = np.column_stack((0.018 * np.cos(t), 0.070 + 0.012 * np.sin(t)))
    psi = brazo().inversa(recorrido)
    cierre = np.abs(psi[-1] - psi[0])
    assert float(cierre.max()) < 0.05


def test_psi_sale_desenrollada_aunque_el_brazo_cruce_por_pi():
    """El salto de arctan2 en ±π no puede llegar al spline."""
    t = np.linspace(0.0, 2.0 * np.pi, 360, endpoint=False)
    # Recorrido amplio que hace pasar el eslabón izquierdo por el segundo
    # cuadrante y de vuelta.
    recorrido = np.column_stack((0.020 * np.cos(t), 0.068 + 0.016 * np.sin(t)))
    psi = brazo().inversa(recorrido)
    assert float(np.abs(np.diff(psi, axis=0)).max()) < 0.2


def test_las_dos_ramas_dan_soluciones_distintas_y_ambas_validas():
    objetivo = np.array([[0.0, 0.070]])
    normal = BrazoCincoBarras(separacion=mm(60.0), proximal=mm(55.0), distal=mm(70.0))
    volteado = BrazoCincoBarras(
        separacion=mm(60.0),
        proximal=mm(55.0),
        distal=mm(70.0),
        rama_izquierda=1,
        rama_derecha=-1,
    )
    assert not np.allclose(normal.inversa(objetivo), volteado.inversa(objetivo))


# ---------------------------------------------------------------------------
# Alcance
# ---------------------------------------------------------------------------


def test_un_punto_fuera_de_alcance_se_detecta_antes_de_calcular():
    lejos = np.array([[0.0, 0.500]])
    assert not brazo().alcanzable(lejos).any()


def test_pedir_un_punto_inalcanzable_falla_con_un_mensaje_util():
    with pytest.raises(FueraDeAlcance, match="fuera del alcance"):
        brazo().inversa(np.array([[0.0, 0.500]]))


def test_los_puntos_de_trabajo_estan_todos_dentro():
    assert brazo().alcanzable(puntos_de_trabajo()).all()


# ---------------------------------------------------------------------------
# Determinismo
# ---------------------------------------------------------------------------


def test_cien_ejecuciones_dan_exactamente_lo_mismo():
    objetivo = puntos_de_trabajo()
    primera = brazo().inversa(objetivo)
    for _ in range(100):
        assert brazo().inversa(objetivo).tobytes() == primera.tobytes()


# ---------------------------------------------------------------------------
# Parámetros
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("campo", "valor"),
    [("separacion", 0.0), ("proximal", -0.01), ("distal", 0.0)],
)
def test_las_longitudes_deben_ser_positivas(campo: str, valor: float):
    parametros = {"separacion": mm(60.0), "proximal": mm(55.0), "distal": mm(70.0)}
    parametros[campo] = valor
    with pytest.raises(ValueError, match="positivo"):
        BrazoCincoBarras(**parametros)  # type: ignore[arg-type]


def test_la_rama_solo_admite_mas_uno_o_menos_uno():
    with pytest.raises(ValueError, match="-1 o 1"):
        BrazoCincoBarras(separacion=mm(60.0), proximal=mm(55.0), distal=mm(70.0), rama_izquierda=0)


# ---------------------------------------------------------------------------
# La palanca elevadora
# ---------------------------------------------------------------------------


def test_la_palanca_va_y_vuelve():
    palanca = PalancaElevadora(brazo=mm(30.0))
    alturas = np.array([[0.0], [0.005], [-0.005], [0.020]])
    assert np.allclose(palanca.directa(palanca.inversa(alturas)), alturas, atol=1e-12)


def test_la_palanca_no_llega_mas_alla_de_su_longitud():
    palanca = PalancaElevadora(brazo=mm(30.0))
    with pytest.raises(FueraDeAlcance, match="pasa de la palanca"):
        palanca.inversa(np.array([[0.040]]))


def test_a_altura_cero_la_palanca_esta_horizontal():
    palanca = PalancaElevadora(brazo=mm(30.0))
    assert palanca.inversa(np.array([[0.0]]))[0, 0] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------


def test_el_registro_resuelve_las_claves_conocidas():
    actuador = construir(
        "brazo_cinco_barras_v1",
        {"separacion": mm(60.0), "proximal": mm(55.0), "distal": mm(70.0)},
    )
    assert actuador.canales == ("x", "y")
    assert actuador.seguidores == ("izquierdo", "derecho")


def test_una_clave_desconocida_falla_y_dice_cuales_hay():
    with pytest.raises(ActuadorDesconocido, match="brazo_cinco_barras_v1"):
        construir("brazo_inventado", {})


def test_unos_parametros_que_no_encajan_fallan_pronto():
    with pytest.raises(ActuadorDesconocido, match="no encajan"):
        construir("palanca_elevadora_v1", {"longitud": 0.03})


def test_las_claves_del_registro_son_estables():
    assert claves() == ("brazo_cinco_barras_v1", "palanca_elevadora_v1")
