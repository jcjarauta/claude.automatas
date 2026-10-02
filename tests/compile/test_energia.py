"""¿Puede una persona girar el escribiente, y sale la letra limpia?"""

from __future__ import annotations

import numpy as np
import pytest

from compile.conjunto import montar
from compile.contratos import cargar
from compile.energia import MARGEN_DE_PAR, Accionamiento, analizar, inercia_del_volante
from compile.escribiente import Escribiente, compilar
from core.energy.budget import CargaSeguidor
from core.energy.humano import Manivela, Transmision
from core.escritura import Escritura, Trazo
from core.units import KgM2, NewtonMetro, mm

pytestmark = pytest.mark.core


def trazo(*puntos: tuple[float, float]) -> Trazo:
    return Trazo(puntos=[(mm(x), mm(y)) for x, y in puntos])


def hola() -> Escritura:
    return Escritura(
        nombre="hola",
        trazos=[
            trazo((0.0, 0.0), (0.0, 20.0)),
            trazo((0.0, 10.0), (8.0, 10.0), (8.0, 0.0)),
            trazo((14.0, 0.0), (14.0, 12.0), (20.0, 12.0), (20.0, 0.0), (14.0, 0.0)),
            trazo((26.0, 0.0), (26.0, 20.0)),
        ],
    )


def analisis(accionamiento: Accionamiento | None = None):
    maquina = Escribiente()
    compilacion = compilar(hola(), maquina)
    montaje, _ = montar(compilacion, maquina)
    return analizar(compilacion, montaje.inercia, accionamiento)


def desnudo(**kw) -> Accionamiento:
    """Un accionamiento **sin volante**, para medir el modelo y no la máquina.

    `Accionamiento()` trae por defecto el volante del contrato, que es lo
    correcto para el informe de un pedido —si no, pediría uno que ya está
    dibujado— y lo que no vale aquí: con él puesto, «¿cuánto volante hace
    falta?» responde cero y la pregunta deja de medir nada. Los tests que
    preguntan por el modelo lo dicen quitándolo, no heredándolo.
    """
    return Accionamiento(inercia_en_la_manivela=KgM2(0.0), **kw)


# ---------------------------------------------------------------------------
# El par
# ---------------------------------------------------------------------------


def test_una_mano_mueve_esto_de_sobra():
    """El resultado que decide la arquitectura: el par no es el problema."""
    energia, veredicto = analisis()
    assert "par_insuficiente" not in [i.codigo for i in veredicto.errores]
    assert energia.relacion_minima == 1.0
    assert energia.par_maximo < 0.2


def test_el_trabajo_de_una_vuelta_es_poco():
    """Menos de un julio: veinte frases no cansan a nadie."""
    energia, _ = analisis()
    assert 0.0 < float(energia.trabajo_por_vuelta) < 1.0


def test_un_muelle_desmedido_agota_el_par_y_pide_reductor():
    """Y entonces el informe tiene que decir de cuánto, no solo que falta."""
    accionamiento = Accionamiento(
        carga=CargaSeguidor(par_muelle=NewtonMetro(30.0), rozamiento=NewtonMetro(5.0))
    )
    energia, veredicto = analisis(accionamiento)
    assert "par_insuficiente" in [i.codigo for i in veredicto.errores]
    assert energia.relacion_minima is not None
    assert energia.relacion_minima > 1.0
    assert "reductor" in veredicto.errores[0].sugerencia


def test_el_reductor_arregla_lo_que_prometia_arreglar():
    carga = CargaSeguidor(par_muelle=NewtonMetro(30.0), rozamiento=NewtonMetro(5.0))
    energia, _ = analisis(Accionamiento(carga=carga))
    assert energia.relacion_minima is not None
    con_reductor = Accionamiento(
        carga=carga, transmision=Transmision(relacion=energia.relacion_minima)
    )
    _, veredicto = analisis(con_reductor)
    assert "par_insuficiente" not in [i.codigo for i in veredicto.errores]


def test_el_par_disponible_cubre_al_pedido_con_margen():
    energia, _ = analisis()
    pedido = energia.presupuesto.total(Accionamiento().omega)
    assert float(np.min(energia.disponible)) >= MARGEN_DE_PAR * float(np.max(pedido))


# ---------------------------------------------------------------------------
# El volante
# ---------------------------------------------------------------------------


def test_a_treinta_vueltas_por_minuto_hace_falta_volante():
    """El hallazgo de la etapa: lo que aprieta no es el par, es la suavidad.
    El cartucho por sí solo no llega ni de lejos."""
    energia, veredicto = analisis(desnudo(vueltas_por_minuto=30.0))
    assert "volante_necesario" in [i.codigo for i in veredicto.avisos]
    assert float(energia.inercia_necesaria) > 5.0 * float(energia.inercia_del_cartucho)


def test_girar_al_doble_pide_casi_la_cuarta_parte_de_volante():
    """Casi, y el «casi» es real: la inercia necesaria va con 1/ω², pero el
    par pedido también tiene un término que crece con ω², así que la energía
    de fluctuación no es exactamente la misma. A estas velocidades la
    diferencia es de una parte en diez mil."""
    despacio, _ = analisis(desnudo(vueltas_por_minuto=30.0))
    deprisa, _ = analisis(desnudo(vueltas_por_minuto=60.0))
    assert float(deprisa.inercia_necesaria) == pytest.approx(
        float(despacio.inercia_necesaria) / 4.0, rel=1e-3
    )


def test_el_volante_en_la_manivela_es_el_del_arbol_entre_la_relacion_al_cuadrado():
    """Es la razón de poner reductor aunque el par sobre: en el eje rápido
    hace falta n² veces menos inercia."""
    energia, _ = analisis(desnudo(transmision=Transmision(relacion=3.0)))
    assert float(energia.volante_en_la_manivela) == pytest.approx(
        float(energia.volante_que_falta) / 9.0
    )


def test_un_reductor_de_tres_a_uno_deja_el_volante_en_algo_comprable():
    """Con un disco de acero de 50 mm de radio, J = ½·m·r²."""
    energia, _ = analisis(desnudo(transmision=Transmision(relacion=3.0), vueltas_por_minuto=60.0))
    masa = 2.0 * float(energia.volante_en_la_manivela) / 0.05**2
    assert masa < 0.2


def test_sin_reductor_y_despacio_el_volante_es_inaceptable():
    """Más de un kilo de disco en una pieza de sobremesa no es una opción.

    **Sin reductor se dice, no se hereda**: el valor por defecto de la
    relación es el del contrato, que son 3:1, y con él este test medía otra
    cosa y pasaba por casualidad."""
    energia, _ = analisis(desnudo(transmision=Transmision(relacion=1.0), vueltas_por_minuto=30.0))
    masa = 2.0 * float(energia.volante_en_la_manivela) / 0.05**2
    assert masa > 1.0


def test_el_cartucho_cuenta_como_parte_del_volante():
    energia, _ = analisis(desnudo())
    assert float(energia.volante_que_falta) == pytest.approx(
        float(energia.inercia_necesaria) - float(energia.inercia_del_cartucho)
    )


def test_admitir_mas_irregularidad_pide_menos_volante():
    fino, _ = analisis(Accionamiento(coeficiente_fluctuacion=0.05))
    basto, _ = analisis(Accionamiento(coeficiente_fluctuacion=0.30))
    assert float(basto.inercia_necesaria) < float(fino.inercia_necesaria)


# ---------------------------------------------------------------------------
# Bordes y consistencia
# ---------------------------------------------------------------------------


def test_sin_levas_no_hay_energia_que_calcular():
    maquina = Escribiente(caja_ancho=mm(600.0), caja_alto=mm(200.0))
    compilacion = compilar(hola(), maquina)
    with pytest.raises(ValueError, match="no hay levas"):
        analizar(compilacion, montar_inercia())


def montar_inercia():
    from core.units import KgM2

    return KgM2(1e-4)


def test_el_veredicto_lleva_los_numeros_para_decidir():
    _, veredicto = analisis()
    for clave in (
        "par_medio",
        "par_maximo",
        "trabajo_por_vuelta",
        "energia_de_fluctuacion",
        "inercia_necesaria",
        "volante_en_la_manivela",
    ):
        assert clave in veredicto.metricas


def test_una_manivela_mas_larga_da_mas_par():
    flojo, _ = analisis(Accionamiento(manivela=Manivela(par_maximo=NewtonMetro(1.0))))
    fuerte, _ = analisis(Accionamiento(manivela=Manivela(par_maximo=NewtonMetro(8.0))))
    assert float(np.max(fuerte.disponible)) > float(np.max(flojo.disponible))


def test_analizar_dos_veces_da_lo_mismo():
    uno, _ = analisis()
    otro, _ = analisis()
    assert uno.par_medio == otro.par_medio
    assert float(uno.inercia_necesaria) == float(otro.inercia_necesaria)


# ---------------------------------------------------------------------------
# Lo que ya gira cuenta
# ---------------------------------------------------------------------------


def test_la_rueda_grande_ayuda_pero_no_es_el_volante():
    """El engranaje grande va en el eje LENTO, así que su inercia cuenta tal
    cual. Aporta, pero para llegar solo haría falta un disco enorme."""
    from core.solido import densidad_de, inercia_de_disco

    rueda = inercia_de_disco(0.030, 0.006, densidad_de("latón"))
    sin_rueda, _ = analisis(desnudo(transmision=Transmision(relacion=3.0)))
    con_rueda, _ = analisis(
        desnudo(transmision=Transmision(relacion=3.0), inercia_en_el_arbol=rueda)
    )
    assert float(con_rueda.inercia_disponible) > float(sin_rueda.inercia_disponible)
    assert float(con_rueda.volante_que_falta) > 0.0


def test_la_misma_masa_en_la_manivela_rinde_la_relacion_al_cuadrado():
    from core.solido import densidad_de, inercia_de_disco

    disco = inercia_de_disco(0.030, 0.006, densidad_de("latón"))
    en_el_arbol, _ = analisis(
        desnudo(transmision=Transmision(relacion=3.0), inercia_en_el_arbol=disco)
    )
    en_la_manivela, _ = analisis(
        Accionamiento(transmision=Transmision(relacion=3.0), inercia_en_la_manivela=disco)
    )
    aporta_arbol = float(en_el_arbol.inercia_disponible) - float(en_el_arbol.inercia_del_cartucho)
    aporta_manivela = float(en_la_manivela.inercia_disponible) - float(
        en_la_manivela.inercia_del_cartucho
    )
    assert aporta_manivela == pytest.approx(9.0 * aporta_arbol)


def test_con_bastante_inercia_ya_no_se_pide_volante():
    from core.units import KgM2

    _, veredicto = analisis(Accionamiento(inercia_en_el_arbol=KgM2(1.0e-2)))
    assert "volante_necesario" not in [i.codigo for i in veredicto.avisos]


def test_el_volante_del_contrato_cubre_el_peor_caso_de_referencia():
    """**La cota que no es un encaje.** El diámetro del volante no lo decide
    ninguna pieza que lo toque: lo decide la inercia que hace falta para que
    la manivela no vaya a tirones, así que lo que hay que comprobar es eso y
    no un ajuste.

    Y se comprueba contra **todos** los casos de referencia, no contra el
    demo: «firma» —un trazo cursivo largo— pide 3,62 × 10⁻⁴ frente a los
    2,28 de «hola», un 59 % más. Dimensionado sobre el demo, el volante se
    habría quedado un tercio corto justo en el pedido más bonito.
    """
    from tests import casos

    c = cargar()
    relacion = c.valor("bastidor", "reductor_relacion").valor
    rpm = c.valor("accionamiento", "manivela_vueltas_por_minuto").valor
    acc = desnudo(transmision=Transmision(relacion=relacion), vueltas_por_minuto=rpm / relacion)
    tiene = float(inercia_del_volante())

    peor, de_quien = 0.0, ""
    for nombre in ("hola", "firma", "puntos"):
        compilacion = compilar(getattr(casos, nombre)())
        if not compilacion.perfiles:
            continue
        montaje, _ = montar(compilacion, Escribiente())
        e, _ = analizar(compilacion, montaje.inercia, acc)
        if float(e.volante_en_la_manivela) > peor:
            peor, de_quien = float(e.volante_en_la_manivela), nombre

    assert peor > 0.0, "ningún caso de referencia llegó a sintetizar levas"
    assert tiene >= peor, (
        f"el volante da {tiene * 1e4:.2f} × 10⁻⁴ kg·m² y «{de_quien}» pide "
        f"{peor * 1e4:.2f}: sube volante_diametro o baja el aligeramiento"
    )
    # Y que el margen no se infle sin que nadie lo note: 300 g de latón
    # colgando de un Ø10 tampoco son gratis.
    assert tiene <= 1.6 * peor, (
        f"el volante da {tiene / peor:.2f} veces lo que pide el peor caso: sobra latón"
    )


def test_el_demo_solo_no_habria_bastado_para_dimensionarlo():
    """La razón de que el test de arriba recorra los tres casos, escrita
    como test para que no se pierda: con «hola» el volante sale un tercio
    corto."""
    from tests import casos

    c = cargar()
    relacion = c.valor("bastidor", "reductor_relacion").valor
    rpm = c.valor("accionamiento", "manivela_vueltas_por_minuto").valor
    acc = desnudo(transmision=Transmision(relacion=relacion), vueltas_por_minuto=rpm / relacion)
    pide = {}
    for nombre in ("hola", "firma"):
        compilacion = compilar(getattr(casos, nombre)())
        montaje, _ = montar(compilacion, Escribiente())
        e, _ = analizar(compilacion, montaje.inercia, acc)
        pide[nombre] = float(e.volante_en_la_manivela)
    assert pide["firma"] > 1.4 * pide["hola"]
