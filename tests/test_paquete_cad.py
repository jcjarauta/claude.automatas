"""El paquete de importación al CAD.

Lo que se comprueba no es que los archivos existan: es que **el paquete diga
en qué orden se usan**. Todo lo que lleva dentro existía ya, repartido en
tres comandos que escribían en tres sitios, y por eso nadie lo usaba. Un
montón de archivos sin orden no es un paquete de importación.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from emit.catalogo import cargar as cargar_piezas
from scripts.exportar_para_cad import MAPAS, main


@pytest.fixture
def paquete(tmp_path: Path) -> Path:
    assert main(["demo/hola.json", "--out", str(tmp_path)]) == 0
    return tmp_path


def test_lleva_las_cotas_que_comparten_el_compilador_y_el_cad(paquete: Path):
    fs = (paquete / "variables.fs").read_text(encoding="utf-8")
    assert "export const eje_diametro" in fs
    assert "NO EDITAR AQUI" in fs, "sin esto alguien las edita dentro del CAD"
    assert (paquete / "variables.csv").exists()


def test_los_bocetos_del_cartucho_van_sin_rotulo(paquete: Path):
    """El `TEXT` de DXF no es una entidad de boceto: el CAD importa bien la
    geometría y suelta un «no se ha podido importar la entidad desconocida».
    El aviso confunde, y el rótulo en el CAD no sirve para nada."""
    import ezdxf

    dxfs = sorted((paquete / "cartucho").glob("*.dxf"))
    assert len(dxfs) == 3
    for ruta in dxfs:
        tipos = {e.dxftype() for e in ezdxf.readfile(ruta).modelspace()}
        assert "TEXT" not in tipos, f"{ruta.name} lleva rótulo"
        assert tipos, f"{ruta.name} salió vacío"


def test_el_calaje_viaja_con_el_paquete(paquete: Path):
    """Montar un brazo al ángulo equivocado escribe basura, y es un error que
    no se ve hasta que la máquina dibuja."""
    calajes = (paquete / "calajes.md").read_text(encoding="utf-8")
    for brazo in ("izquierdo", "derecho", "elevador"):
        assert brazo in calajes


def test_la_hoja_de_ruta_dice_el_orden_y_de_quien_es_cada_pieza(paquete: Path):
    guia = (paquete / "README.md").read_text(encoding="utf-8")
    assert "1. **Monta la biblioteca de materiales**" in guia
    # Antes decía «Importa `variables.csv`», que es el que lleva cabecera y
    # rompe la variable entera al importarlo. El test la pinchaba tal cual.
    assert "2. **Importa los cinco CSV en un Variable Studio**" in guia
    assert "un solo sentido" in guia, "hay que decir que lo editado en el CAD se pierde"
    # La plataforma prismática ya no se dibuja a mano desde cero: sale en DXF
    # con su datum. Lo que sigue siendo de la persona es acotar y comprobar
    # que el croquis queda definido, y la hoja tiene que decirlo las dos cosas
    # o el DXF se extruye suelto.
    assert "plataforma/*.dxf" in guia
    assert "dos coincidentes" in guia
    assert "totalmente definida" in guia
    assert "andamio, no vínculo" in guia


def test_un_pedido_que_no_cabe_escribe_el_paquete_pero_avisa(tmp_path: Path):
    """Mismo criterio que el CLI: los archivos se escriben igual, porque un
    pedido que no cabe también hay que poder mirarlo, pero el código de
    salida dice que no se fabrica."""
    from tests.casos import apretada

    entrada = tmp_path / "apretada.json"
    entrada.write_text(
        json.dumps(
            {
                "nombre": "apretada",
                "trazos": [
                    [[x * 1000.0, y * 1000.0] for x, y in t.coordenadas] for t in apretada().trazos
                ],
            }
        ),
        encoding="utf-8",
    )
    salida = tmp_path / "fuera"
    assert main([str(entrada), "--out", str(salida)]) == 1
    assert (salida / "README.md").exists()


def test_la_tabla_de_materiales_sale_de_core(paquete: Path):
    """La misma tabla con la que el compilador calcula la masa. Si el CAD
    usara otras densidades, la masa del modelo y la del polígono discreparían
    y no habría forma de saber cuál miente."""
    from core.solido import DENSIDADES

    materiales = (paquete / "materiales.csv").read_text(encoding="utf-8")
    assert materiales.startswith("Category,Name,Density [kg/m^3]")
    for nombre, densidad in DENSIDADES.items():
        assert f",{nombre},{densidad:.0f}" in materiales


def test_las_cotas_comerciales_viajan_para_poder_dibujarlas(paquete: Path):
    """Sin esto, una pieza comercial solo puede entrar como STEP mudo: un
    cambio de referencia no movería nada."""
    piezas = (paquete / "piezas.csv").read_text(encoding="utf-8")
    assert "casquillo_pivote_valona,15.0000,mm" in piezas
    assert "rodillo_seguidor_exterior,6.0000,mm" in piezas
    assert piezas.count("\n") > 40


def test_los_dientes_van_en_el_paquete_y_sin_unidad(paquete: Path):
    """**El dato que el CAD pide y la ficha no guarda.**

    La ficha guarda el diámetro exterior porque es lo que se mide con el pie
    de rey sobre la pieza que llega; el FeatureScript de engranaje pide Z.
    Sin esta fila hay que despejarlo de cabeza rellenando un formulario, y
    así salió un piñón de 25 dientes en vez de 20: relación 2,4 en lugar de
    3 y entre-ejes de 29,75 en vez de 28, sin un solo aviso.

    Va al archivo sin unidad porque es un recuento. En el de milímetros
    serían veinte milímetros de dientes.
    """
    numero = (paquete / "piezas_num.csv").read_text(encoding="utf-8")
    cota = (paquete / "piezas_cota.csv").read_text(encoding="utf-8")
    assert "pinon_reductor_dientes,20" in numero
    assert "rueda_reductor_dientes,60" in numero
    assert "dientes" not in cota


def test_las_variables_van_partidas_por_unidad(paquete: Path):
    """**El CAD aplica un único factor de conversión a todo el archivo que
    importa.** Con las 29 cotas en un solo CSV, o los cinco ángulos entran
    como milímetros o las veinte longitudes como grados. Y un calaje leído
    como milímetros no da un aviso: da una máquina que escribe torcido.

    Quien sabe de qué unidad es cada cota es el contrato, no quien marca
    casillas en una interfaz."""
    cota = (paquete / "variables_cota.csv").read_text(encoding="utf-8")
    angulo = (paquete / "variables_angulo.csv").read_text(encoding="utf-8")
    numero = (paquete / "variables_num.csv").read_text(encoding="utf-8")

    assert "radio_base,55.0000,mm" in cota
    assert "calaje_izquierdo" in angulo
    assert "relacion_varillaje" in numero
    # y ninguna se cuela en el archivo de otra unidad
    assert "calaje_izquierdo" not in cota
    assert "radio_base" not in angulo


def test_una_circunferencia_de_taladros_tiene_su_diametro(paquete: Path):
    """**Un patrón circular se acota por su circunferencia, en diámetro.**

    Faltó dibujando el volante: `volante_aligeramiento_al_centro` vale 30 y
    no lleva «radio» ni «diametro» en el nombre, así que el exportador no le
    sacaba gemelo y en el campo del CAD —que pide Ø60— no había nada que
    teclear. Mismo fallo que el canto del sector, con otra cara.

    El nombre no se cambia: ya está entregado, y renombrar una cota
    entregada cuesta reteclear el croquis. Lo que sabe que esa distancia es
    una circunferencia es la **ficha**, que declara el patrón en `polares`.
    """
    import csv as _csv

    from scripts.comparar_dxf import circunferencias_de_taladros

    filas = _csv.reader((paquete / "variables_cota.csv").read_text(encoding="utf-8").splitlines())
    valores = {f[0]: float(f[1]) for f in filas if f}
    taladros = circunferencias_de_taladros()
    assert taladros, "ninguna ficha declara un patrón circular: el cruce no comprueba nada"
    for nombre in sorted(taladros):
        gemelo = nombre if nombre.endswith("_diametro") else f"{nombre}_diametro"
        assert gemelo in valores, f"{nombre} es una circunferencia de taladros y no tiene diámetro"
        assert valores[gemelo] == pytest.approx(2.0 * valores[nombre])


def test_ninguna_hoja_rotula_un_angulo_negativo(paquete: Path):
    """**El campo de ángulo no acepta el signo.** La herramienta de ángulo
    mide una magnitud: metido con el menos, el campo se pone en rojo, y
    quitándoselo a mano se acaba poniendo el rasgo al otro lado, que es la
    pieza espejada y se ve igual de bien.

    Es el mismo fallo que el radio de un círculo entero, con otra cara: la
    hoja ofrecía `#angulo.platina_pivote_angulo_izquierdo`, que vale
    -58,407. Para eso está el gemelo en positivo, y para eso se comprueba
    que es el que la hoja pone.

    **Vale para lo que va al croquis y no para lo demás.** Un calaje es
    negativo y se queda así: no se acota en un croquis, se monta, y el campo
    de ángulo de un emparejamiento sí acepta el signo. Darle la magnitud y
    una nota en prosa sería peor que darle el número. La línea es la misma
    que usa el cruce con el comparador: lo que el perfil resuelve.
    """
    import csv as _csv

    from emit.plataforma import LISTADO
    from scripts.dibujar_pieza import PERFIL_DE, hoja

    filas = _csv.reader((paquete / "variables_angulo.csv").read_text(encoding="utf-8").splitlines())
    grados = {f[0]: float(f[1]) for f in filas if f}
    fuera_del_croquis = {
        v.nombre for f in LISTADO.values() for v in f.variables if not v.en_el_perfil
    }
    for pieza in PERFIL_DE:
        for nombre in set(re.findall(r"#angulo\.([a-z0-9_]+)", hoja([pieza]))):
            assert nombre in grados, f"{pieza}: #angulo.{nombre} no está en el CSV"
            if nombre in fuera_del_croquis:
                continue
            assert grados[nombre] >= 0.0, (
                f"hoja de {pieza}: rotula #angulo.{nombre}, que vale "
                f"{grados[nombre]:g}. El campo no acepta el signo: pon "
                f"«{nombre}_positivo» y di de qué lado cae el rasgo"
            )


def test_toda_hoja_que_se_copia_rotula_variables_que_existen_en_los_csv(paquete: Path):
    """**El mismo cruce de la hoja de piezas, extendido a las otras cuatro.**

    Estaba cubierta solo la hoja de piezas comerciales. Las dos conceptuales
    y los dos planos comprobaban sus variables contra `docs/contratos.json`,
    que no es lo que se importa: lo que se importa son los CSV, y entre el
    contrato y el CSV hay un reparto por unidades que puede equivocar el
    PREFIJO sin equivocar el nombre. Un `#cota.calaje_izquierdo` existiría
    en el contrato y no en `variables_cota.csv`, y el que lo copia se entera
    cuando el campo se pone en rojo.

    Es literalmente lo que ya pasó con `#pieza.…_dientes`. Aquí se cruza
    cada hoja contra los CSV de verdad.
    """
    import csv as _csv

    from scripts import (
        dibujar_amplificador,
        dibujar_cinco_barras,
        dibujar_plano_brazos,
        dibujar_plano_cabestrante,
    )

    existentes: dict[str, set[str]] = {}
    for archivo, (variable, _) in MAPAS.items():
        ruta = paquete / f"{archivo}.csv"
        if ruta.exists():
            filas = _csv.reader(ruta.read_text(encoding="utf-8").splitlines())
            existentes.setdefault(variable, set()).update(f[0] for f in filas if f)

    hojas = {
        "amplificador": dibujar_amplificador.hoja(),
        "cinco_barras": dibujar_cinco_barras.hoja(),
        "plano_cabestrante": dibujar_plano_cabestrante.hoja(),
        "plano_brazos": dibujar_plano_brazos.hoja(),
    }
    vistas = 0
    for nombre_hoja, texto in hojas.items():
        for mapa, nombre in re.findall(r"#([a-z_]+)\.([a-z0-9_]+)", texto):
            assert mapa in existentes, f"{nombre_hoja}: no hay CSV para el mapa «{mapa}»"
            assert nombre in existentes[mapa], f"{nombre_hoja}: #{mapa}.{nombre}"
            vistas += 1
    assert vistas >= 30, f"esperaba muchas más variables rotuladas, vi {vistas}"


def test_la_hoja_de_ruta_dice_que_archivo_va_a_que_variable_y_con_que_factor(
    paquete: Path,
):
    """**Es el contrato entre el paquete y lo que alguien teclea.**

    Una importación de Onshape crea un mapa con un único factor para todas
    sus filas, así que el reparto no es un detalle de presentación: decide
    si `#pieza_num.pinon_reductor_dientes` existe o si los dientes entran
    como veinte milímetros. La tabla se genera desde `MAPAS`, y la hoja de
    bocetos imprime los prefijos desde el mismo sitio.
    """
    texto = (paquete / "README.md").read_text(encoding="utf-8")
    for archivo, (variable, factor) in MAPAS.items():
        assert (archivo + ".csv") in texto
        assert f"`#{variable}`" in texto
        assert (paquete / f"{archivo}.csv").exists(), archivo
        assert f"`{factor}`" in texto


def test_toda_variable_que_la_hoja_de_bocetos_rotula_existe_en_el_csv(paquete: Path):
    """**El test que cierra la familia de fallos.**

    La hoja de bocetos es lo que alguien tiene al lado mientras teclea en el
    CAD. Ya ha mandado tres veces a escribir algo que no existía: los
    dientes que no salían, los dientes en el mapa equivocado, y
    `#pieza.tornilleria_longitud`, que el perfil dibuja con un valor por
    defecto y la ficha no declara. Cada una se arregló sola y la siguiente
    apareció por otro lado.

    Esto cruza los dos artefactos de una vez: cada `#mapa.variable` de la
    hoja tiene que estar en el CSV de ese mapa. Si no está, no hace falta
    saber por qué: no se puede teclear.
    """
    import csv as _csv

    from scripts.dibujar_piezas import filas_de

    existentes: dict[str, set[str]] = {}
    for archivo, (variable, _) in MAPAS.items():
        ruta = paquete / f"{archivo}.csv"
        if not ruta.exists():
            continue
        filas = _csv.reader(ruta.read_text(encoding="utf-8").splitlines())
        existentes.setdefault(variable, set()).update(f[0] for f in filas if f)

    for pieza in cargar_piezas():
        for etiqueta, _ in filas_de(pieza):
            if not etiqueta.startswith("#"):
                continue  # un hueco rotulado, que a propósito no es variable
            mapa, _, nombre = etiqueta[1:].partition(".")
            assert mapa in existentes, f"{etiqueta}: no hay CSV para el mapa «{mapa}»"
            assert nombre in existentes[mapa], f"{etiqueta} no está en {mapa}"


def test_la_hoja_de_ruta_avisa_de_no_importar_los_que_llevan_cabecera(paquete: Path):
    """`variables.csv` y `piezas.csv` son para leer. Importados, la cabecera
    entra en el mapa como una clave cuyo valor es el texto «valor», y al
    multiplicarla por el factor falla la variable entera con un error que no
    la menciona. La hoja de ruta mandaba importarlos: así se rompió."""
    texto = (paquete / "README.md").read_text(encoding="utf-8")
    assert "no `variables.csv` ni `piezas.csv`" in texto
    for legible in ("variables.csv", "piezas.csv"):
        assert f"**Importa `{legible}`" not in texto


def test_un_csv_que_se_importa_no_lleva_cabecera_ni_comentarios(paquete: Path):
    """**Lo que rompía la importación en Onshape.**

    El Variable Studio lee «todos los valores» sin saber que la primera fila
    es un rótulo, así que la cabecera entra en el mapa como una clave
    `nombre` cuyo valor es el texto `valor`. Con el factor de conversión
    puesto, multiplicar ese texto por 1 mm **hace fallar la regeneración de
    toda la variable**, y el error que sale no menciona la cabecera.

    Un «#» al principio tampoco es un comentario para el CAD: es otra fila.
    """
    for nombre in ("variables_cota.csv", "variables_angulo.csv", "piezas_cota.csv"):
        primera = (paquete / nombre).read_text(encoding="utf-8").split("\n")[0]
        assert not primera.startswith("#"), f"{nombre} empieza por comentario"
        assert not primera.startswith("nombre,"), f"{nombre} lleva cabecera"
        assert primera.split(",")[2] in ("mm", "deg", ""), f"{nombre}: la fila 0 no es un dato"


def test_los_archivos_legibles_si_llevan_cabecera(paquete: Path):
    """Los que no se importan se leen, y sin cabecera no se entienden."""
    for nombre in ("variables.csv", "piezas.csv", "materiales.csv"):
        primera = (paquete / nombre).read_text(encoding="utf-8").split("\n")[0]
        assert primera.startswith(("nombre,", "Category,")), f"{nombre} sin cabecera"


def test_una_tolerancia_con_coma_no_parte_la_fila():
    """La del pasador de índice es «m6 en el plato metálico, deslizante en el
    POM». Sin comillas parte la fila en dos columnas de más, y no se veía
    porque las dos primeras —que son las que el CAD lee— quedaban en su
    sitio."""
    import csv as _csv
    import io

    from compile.contratos import cargar
    from scripts.exportar_variables import csv as exportar

    for fila in _csv.reader(io.StringIO(exportar(cargar()))):
        assert len(fila) == 7, f"fila con {len(fila)} columnas: {fila}"


def test_una_unidad_desconocida_se_queja_en_vez_de_colarse():
    """Si mañana un contrato trae newtons, tiene que saltar al exportar y no
    acabar en el archivo de los milímetros."""
    from scripts.exportar_para_cad import por_unidad

    with pytest.raises(ValueError, match="newton"):
        por_unidad("nombre,valor,unidad\nempuje,12,newton\n")


def test_cada_cota_circular_tiene_sus_dos_formas(paquete: Path):
    """**Onshape acota el diámetro por defecto.** Meter `#cota.radio_base` en
    una cota de diámetro da una leva de 27,5 mm en vez de 55: la mitad, y sin
    un solo aviso. Con las dos formas no hay nada que recordar ni nada que
    multiplicar — se escribe la que pida el campo.

    Mismo patrón que el pasador de índice: no hacer el error improbable,
    hacerlo imposible."""
    filas = dict((f[0], float(f[1])) for f in _leer(paquete / "variables_cota.csv"))
    assert filas["radio_base"] == pytest.approx(55.0)
    assert filas["radio_base_diametro"] == pytest.approx(110.0)
    assert filas["eje_diametro"] == pytest.approx(10.0)
    assert filas["eje_diametro_radio"] == pytest.approx(5.0)
    # Solo los gemelos: `eje_diametro` acaba en «_diametro» y es una cota
    # del contrato, no una derivada. Lo que distingue a un gemelo es que su
    # base existe.
    gemelos = 0
    for nombre, valor in filas.items():
        for sufijo, factor in (("_diametro", 2.0), ("_radio", 0.5)):
            base = nombre.removesuffix(sufijo)
            if nombre.endswith(sufijo) and base in filas:
                assert valor == pytest.approx(factor * filas[base]), nombre
                gemelos += 1
    # Diecinueve: las dieciséis de antes, los dos tornillos de la mordaza y
    # `cinta_radio_minimo`, que lleva «radio» en el nombre y por eso saca gemelo
    # aunque no sea una cota que se acote. No molesta —son dos filas— y el día
    # que alguien dibuje el radio de arrollado, está.
    # Que el número esté escrito a mano es a propósito: añadir una
    # cota circular sin enterarse de que le sale un gemelo es exactamente lo
    # que este test cuenta.
    #
    # **Dos han llegado por el mismo camino y tarde**: `brazo_ancho` y
    # `amplificador_sector_agujero` eran cotas circulares con un nombre que no
    # lo decía, así que el exportador no les sacaba gemelo y no había radio que
    # teclear. Son la misma familia que los dientes del piñón: el nombre decide
    # si la cota existe en la forma en que se usa.
    #
    # Y la platina las trajo por los dos lados a la vez: `platina_diametro` se
    # llama así —y no `platina_radio`— porque el contorno es un círculo entero
    # y lo que se teclea es el diámetro, y `platina_pivote_al_arbol` dejó de
    # llamarse radio porque es una DISTANCIA. La primera suma un gemelo, la
    # segunda quita uno que no servía para nada: 29 y no 30.
    #
    # Y 31 con el volante, que trae dos círculos enteros: su contorno y los
    # seis aligeramientos. El resto de sus cotas son las del brazo —cala con
    # la misma cara plana sobre la misma barra Ø10 h6—, así que no suman.
    #
    # Y 32 con la circunferencia de taladros del volante: un patrón se acota
    # por su circunferencia de construcción, y esa el CAD la pide en
    # diámetro. Lo sabe la ficha, que declara el patrón, no el nombre.
    #
    # Y 41 con la punta hueca del distal y el casquillo de la rueda: el cubo
    # de la punta (R9, un arco del contorno), el tubo y su interior, y el
    # exterior del casquillo. Se llaman `_diametro` a propósito: el
    # comparador mira los agujeros por su radio, y sin nombre no hay gemelo.
    #
    # Y 47 con la cadena del levantamiento: la varilla de la bieleta y su
    # casquillo, el ojo del tirante, el cubo y el eje de las bielas de la mesa
    # y la pinza del portaminas. Seis círculos, seis gemelos.
    assert gemelos == 47, f"esperaba 47 cotas circulares con gemelo, hay {gemelos}"


def test_el_gemelo_dice_que_es_derivado(paquete: Path):
    """Para que nadie lo corrija a mano creyendo que es una cota del
    contrato: si el radio cambia, el diámetro sale solo."""
    for fila in _leer(paquete / "variables_cota.csv"):
        if fila[0] == "radio_base_diametro":
            assert fila[-1].startswith("derivada de radio_base")
            return
    raise AssertionError("no está el gemelo de radio_base")


def _leer(ruta: Path) -> list[list[str]]:
    import csv as _csv

    return list(_csv.reader(ruta.read_text(encoding="utf-8").splitlines()))
