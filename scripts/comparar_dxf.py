"""Contrasta un DXF o un STEP contra `docs/contratos.json`, venga de donde venga.

    uv run python scripts/comparar_dxf.py pieza.dxf
    uv run python scripts/comparar_dxf.py pieza.step

**El nombre se queda**: está en CLAUDE.md, en la metodología y en la memoria
de quien lo teclea, y renombrarlo cuesta más de lo que aclara.

Los dos archivos dicen cosas distintas y por eso se miran los dos. El DXF es
el croquis, y llega antes: se comprueba ANTES de extruir, que es cuando
arreglarlo es gratis. El STEP es el sólido, llega después y trae una cosa que
el croquis no tiene, **el espesor**: un contorno correcto extruido a lo que
tuviera el CAD por defecto es una pieza que no entra en la pila.

Mide el archivo —radios, distancias entre centros, longitudes, tangencias— y
lo cruza contra la **ficha** de la pieza, que declara qué rasgos tiene que
tener y de qué cota sale cada uno.

**La ficha no es burocracia, es lo que hace que la comparación signifique
algo.** Buscar «alguna cota del contrato que valga 6» no comprueba nada: el
contrato tiene ochenta cotas y cualquier número redondo encuentra una. La
primera versión de este script daba por bueno un radio de 6 citando el ancho
del tambor del cabestrante, que no pinta nada en un brazo. Con ficha, un
rasgo sobrante y uno que falta son dos fallos distintos y los dos se ven.

**Funciona en los dos sentidos, y por eso existe.** El DXF puede ser el que
emita el compilador o el que exporte Onshape después de que alguien lo
dibuje; la comparación es la misma y es la única que detecta una deriva vaya
la geometría en la dirección que vaya. Sin esto, mandar la geometría por
archivo cambia un error de transcripción, que se ve, por uno silencioso.

**Lo que NO ve: las restricciones.** Un croquis puede tener la forma exacta y
estar completamente suelto, que es el peor estado porque se ve bien y se
mueve luego. Eso no viaja en un DXF. Quien dibuje tiene que comprobar en el
CAD que la pieza sale «totalmente definida»; aquí no hay manera.

Los gemelos cuentan: una cota de radio explica un diámetro y al revés, que es
como se tecleó.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import ezdxf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emit.plataforma import LISTADO
from scripts.acotar import CONTRATOS, MM

TOLERANCIA = 1e-3
"""En milímetros. Una micra: por debajo de eso es ruido del formato, por
encima es una cota distinta. El DXF guarda bastantes más decimales."""

CAPAS_DE_ADORNO = frozenset(
    {
        "TEXT",
        "CENTERLINES",
        "CENTERMARKS",
        "VIRTUAL_SHARPS",
        "ANNOTATION_LINES",
        "ANNOTATION_TEXT",
        "TABLES",
        "IMAGES",
        "DETAIL_VIEW_BORDER",
        "DETAIL_VIEW_PARENT_BORDER",
        "SECTION_CUTTING_LINE",
        "ROTULO",
    }
)
"""Lo que Onshape y nuestro emisor ponen que no es la pieza. Un eje de
simetría mide lo que le dé la gana y no hay cota que lo explique."""


@dataclass(frozen=True)
class Ficha:
    """Qué rasgos tiene que tener la pieza, y de qué cota sale cada uno.

    `radios` es {cota: cuántos arcos o círculos de ese radio}. Contarlos
    importa: el distal tiene DOS cubos de 6 porque sus dos extremos son
    iguales, y uno solo sería otra pieza.
    """

    que_es: str
    radios: dict[str, int]
    entre_centros: tuple[str, ...] = ()
    segmentos: dict[str, int] = field(default_factory=dict)
    tangentes: int = 0
    ranura: tuple[str, str] = ()
    """(cota del recorrido, cota del radio) de una ranura recta.

    Una ranura tiene **dos** centros de arco que no son dos rasgos: son los
    extremos de un rasgo. Sin declararla, el barrido de distancias entre
    centros saca tres huérfanas de una pieza que solo tiene dos agujeros.
    """
    desde_datum: tuple[str, ...] = ()
    """Cotas del datum al centro de un rasgo, sobre +X.

    Son **derivadas** y existen porque la herramienta que dibuja el rasgo pide
    esos puntos y no el par (centro, recorrido): restar la mitad de cabeza se
    falla. Mismo caso que la cuerda de la cara plana.
    """
    voladizo: str = ""
    """Del datum al borde más cercano del contorno, hacia -X.

    Sitúa el contorno respecto del datum, que es lo que ninguna otra cota
    hace: largo y ancho dicen cuánto mide el bloque y no dónde está. Sin
    ella el bloque se puede dibujar centrado entre los tornillos —que es lo
    natural y lo que estaba mal— y la ranura se sale por el extremo.
    """
    retranqueo: str = ""
    """Del datum al borde más lejano del contorno, hacia -Y.

    Es `voladizo` en el otro eje, y hace falta por lo mismo: la base es la
    primera pieza que no es simétrica respecto del eje X de su datum, así
    que el ancho y el fondo dicen cuánto mide la tabla y ninguna de las dos
    dice dónde cae el agujero dentro de ella. Con las dos, el rectángulo
    queda situado y el patrón de postes no se puede dibujar desplazado.
    """
    polares: tuple[tuple[str, str, int], ...] = ()
    """Agujeros situados en POLARES: (cota del radio, cota del ángulo, cuántos).

    Con `cuantos` > 1 el ángulo es un reparto y se repite desde 0: los tres
    postes de la platina son («poste_radio_al_arbol», «poste_reparto», 3).

    Hace falta porque `desde_datum` solo mira sobre +X, y la platina es la
    primera pieza cuyos agujeros no están en línea: dos de ellos caen a
    -58,407° y 178,407°, que es donde los pone la transformación del marco
    del cinco barras. Teclear catorce coordenadas cartesianas de tres
    decimales es justo donde se cuela un error que no se ve.
    """
    simetrico: bool = False
    """El contorno es simétrico respecto del eje X.

    Es lo que sitúa la pieza a lo alto, y no hay cota que lo diga: una
    simetría no es un número. Declararla deja que el comparador la mire y
    que la hoja la dibuje, en vez de que el que acota tenga que deducirla.
    """
    cara_plana: str = ""
    """La cota del desplazamiento del eje al plano de la cara, **con signo**.

    La cuerda sola no la sitúa: en un agujero de Ø10 una cuerda de 6 cae a 4
    del centro, pero puede caer a +4 o a -4, y la cara mirando al lado
    contrario cala el brazo media vuelta girado. Es la misma pieza vista en
    el croquis y otra distinta montada.
    """
    cara_plana_angulo: str = ""
    """Hacia dónde mira la normal de la cara plana, y la comprobación lo fija.

    La cuerda tiene que ser perpendicular a esa normal y la cara tiene que
    caer a `cara_plana` del eje medido sobre ella, con signo: entre las dos
    cosas el ángulo queda clavado sin que nadie lo teclee como número. En los
    brazos vale cero; en el balancín, 90°.
    """
    datum: str = ""
    """La cota del rasgo que va en el ORIGEN, y de ahí a +X el siguiente.

    Un croquis importado llega con la forma y **sin una sola restricción**:
    exacto y suelto, que es el peor estado porque se ve bien y se mueve en
    cuanto alguien lo roza. La geometría no puede traer restricciones —ningún
    DXF las lleva— pero sí puede traer el sitio, y con el sitio bien elegido
    quedan solo dos clics que matan los tres grados de libertad del plano:

      1. coincidente: centro del rasgo datum  ·  origen        (quita x e y)
      2. coincidente: el centro siguiente     ·  eje X         (quita el giro)

    Por eso el datum es un agujero y no el centro de la pieza: un agujero ya
    está en el dibujo y se engancha solo. Un punto medio habría que
    construirlo, y lo que hay que construir se olvida.

    No hay un tercer grado de libertad escondido en el volteo: la D del
    agujero es simétrica respecto de X —`brazo_chaveta_angulo` vale cero— así
    que la pieza espejada es la misma. La propiedad que ahorra el brazo
    derecho ahorra también un constraint.
    """


FICHAS: dict[str, Ficha] = {
    "brazo_proximal": Ficha(
        "barra de dos cubos, con el agujero del eje en D",
        {
            "brazo_cubo_diametro_radio": 1,
            "brazo_extremo_diametro_radio": 1,
            "brazo_eje_diametro_radio": 1,
            "brazo_perno_diametro_radio": 1,
        },
        entre_centros=("brazo_proximal",),
        segmentos={"brazo_chaveta_cuerda": 1},
        tangentes=4,
        cara_plana="brazo_chaveta",
        cara_plana_angulo="brazo_chaveta_angulo",
        datum="brazo_eje_diametro_radio",
    ),
    "brazo_distal": Ficha(
        "biela curva sin cara plana: perno en el codo, tubo hueco en la punta",
        {
            "brazo_extremo_diametro_radio": 1,
            "distal_punta_diametro_radio": 1,
            "brazo_perno_diametro_radio": 1,
            "punta_tubo_diametro_radio": 1,
            "distal_curva_interior_radio": 1,
            "distal_curva_exterior_radio": 1,
        },
        entre_centros=("brazo_distal",),
        polares=(("distal_curva_radio", "distal_curva_centro_angulo", 1),),
        datum="brazo_perno_diametro_radio",
    ),
    "palanca_lapiz": Ficha(
        "como el proximal pero más corta",
        {
            "balancin_cubo_diametro_radio": 1,
            "brazo_extremo_diametro_radio": 1,
            "balancin_eje_diametro_radio": 1,
            "brazo_perno_diametro_radio": 1,
        },
        entre_centros=("brazo_palanca",),
        segmentos={"balancin_chaveta_cuerda": 1},
        tangentes=4,
        cara_plana="balancin_chaveta",
        cara_plana_angulo="brazo_chaveta_angulo",
        datum="balancin_eje_diametro_radio",
    ),
    "manivela": Ficha(
        "como el proximal pero más larga: el pomo donde iría la biela",
        {
            "brazo_cubo_diametro_radio": 1,
            "brazo_extremo_diametro_radio": 1,
            "brazo_eje_diametro_radio": 1,
            "brazo_perno_diametro_radio": 1,
        },
        entre_centros=("manivela_entre_centros",),
        segmentos={"brazo_chaveta_cuerda": 1},
        tangentes=4,
        cara_plana="brazo_chaveta",
        cara_plana_angulo="brazo_chaveta_angulo",
        datum="brazo_eje_diametro_radio",
    ),
    "mordaza": Ficha(
        "bloque, tornillo de apriete y ranura: el calaje vive aquí",
        {
            "mordaza_tornillo_diametro_radio": 1,
            "mordaza_fijacion_diametro_radio": 2,
        },
        segmentos={"mordaza_largo": 2, "mordaza_ancho": 2},
        desde_datum=("mordaza_ranura_cerca", "mordaza_ranura_lejos"),
        voladizo="mordaza_voladizo",
        simetrico=True,
        ranura=("mordaza_recorrido", "mordaza_fijacion_diametro_radio"),
        entre_centros=("mordaza_entre_tornillos",),
        datum="mordaza_tornillo_diametro_radio",
    ),
    "eje_pivote": Ficha(
        "sección del eje: Ø10 con una cara plana, sin ningún ángulo mecanizado",
        {"brazo_eje_diametro_radio": 1},
        segmentos={"brazo_chaveta_cuerda": 1},
        cara_plana="brazo_chaveta",
        cara_plana_angulo="brazo_chaveta_angulo",
        datum="brazo_eje_diametro_radio",
    ),
    "volante": Ficha(
        "disco de latón aligerado con seis agujeros y el agujero en D de la manivela",
        {
            "volante_diametro_radio": 1,
            "brazo_eje_diametro_radio": 1,
            "volante_aligeramiento_diametro_radio": 6,
        },
        segmentos={"brazo_chaveta_cuerda": 1},
        polares=(("volante_aligeramiento_al_centro", "volante_aligeramiento_reparto", 6),),
        cara_plana="brazo_chaveta",
        cara_plana_angulo="brazo_chaveta_angulo",
        datum="brazo_eje_diametro_radio",
    ),
    "base": Ficha(
        "tabla de nogal con los tres agujeros de los postes, en triángulo equilátero",
        {"poste_eje_diametro_radio": 3},
        segmentos={"base_ancho": 2, "base_fondo": 2},
        desde_datum=("base_entre_postes",),
        polares=(("base_entre_postes", "base_postes_angulo", 1),),
        voladizo="base_poste_al_borde_izquierdo",
        retranqueo="base_poste_al_borde_trasero",
        datum="poste_eje_diametro_radio",
    ),
    "balancin": Ficha(
        "barra de dos cubos diminuta: el cuarto de vuelta del canal 3",
        {
            "balancin_cubo_diametro_radio": 1,
            "balancin_extremo_diametro_radio": 1,
            "balancin_eje_diametro_radio": 1,
            "balancin_perno_diametro_radio": 1,
        },
        entre_centros=("balancin_entrada",),
        tangentes=4,
        segmentos={"balancin_chaveta_cuerda": 1},
        cara_plana="balancin_chaveta",
        cara_plana_angulo="balancin_chaveta_angulo",
        datum="balancin_eje_diametro_radio",
    ),
    "platina_levas": Ficha(
        "disco de contrachapado con los siete agujeros del mecanismo",
        {
            "platina_diametro_radio": 1,
            # DOS: el del árbol, en el centro, y el del eje de la manivela a 28.
            "rodamiento_arbol_alojamiento_diametro_radio": 2,
            "poste_eje_diametro_radio": 3,
            "brazo_eje_diametro_radio": 2,
            "apoyo_balancin_tornillo_diametro_radio": 2,
        },
        polares=(
            ("poste_radio_al_arbol", "poste_reparto", 3),
            ("platina_pivote_al_arbol", "platina_pivote_angulo_izquierdo", 1),
            ("platina_pivote_al_arbol", "platina_pivote_angulo_derecho", 1),
            ("reductor_entre_ejes", "platina_manivela_angulo", 1),
            ("platina_apoyo_trasero_al_arbol", "platina_apoyo_trasero_angulo", 1),
            ("platina_apoyo_delantero_al_arbol", "platina_apoyo_delantero_angulo", 1),
        ),
        datum="rodamiento_arbol_alojamiento_diametro_radio",
    ),
    "seguidor": Ficha(
        "barra de dos cubos con seis agujeros en línea: muelle, dos al sector y tres al rodillo",
        {
            "seguidor_cubo_diametro_radio": 1,
            "seguidor_extremo_diametro_radio": 1,
            "seguidor_pivote_diametro_radio": 1,
            "seguidor_muelle_diametro_radio": 1,
            "union_sector_seguidor_diametro_radio": 2,
            "seguidor_rodillo_diametro_radio": 3,
        },
        entre_centros=("brazo_seguidor", "brazo_seguidor_derecho", "brazo_seguidor_izquierdo"),
        tangentes=4,
        desde_datum=(
            "seguidor_muelle_radio",
            "union_sector_seguidor_cerca",
            "union_sector_seguidor_lejos",
        ),
        datum="seguidor_pivote_diametro_radio",
    ),
    "sector": Ficha(
        "disco con agujero de paso y los dos tornillos que lo calan al seguidor",
        {
            "amplificador_sector_radio_mecanizado": 1,
            "amplificador_sector_agujero_diametro_radio": 1,
            "union_sector_seguidor_diametro_radio": 2,
            "sector_mordaza_diametro_radio": 2,
        },
        desde_datum=("union_sector_seguidor_cerca", "union_sector_seguidor_lejos"),
        polares=(
            ("sector_mordaza_al_centro", "sector_mordaza_angulo_izquierdo", 1),
            ("sector_mordaza_al_centro", "sector_mordaza_angulo_derecho", 1),
        ),
        datum="amplificador_sector_agujero_diametro_radio",
    ),
    "tambor": Ficha(
        "cilindro liso, sin pestañas, calado al eje por la cara plana",
        {
            "amplificador_tambor_radio_mecanizado": 1,
            "brazo_eje_diametro_radio": 1,
        },
        segmentos={"brazo_chaveta_cuerda": 1},
        cara_plana="brazo_chaveta",
        cara_plana_angulo="brazo_chaveta_angulo",
        datum="brazo_eje_diametro_radio",
    ),
    "eje_manivela": Ficha(
        "sección del eje: Ø10 con una cara plana, como los de pivote",
        {"brazo_eje_diametro_radio": 1},
        segmentos={"brazo_chaveta_cuerda": 1},
        cara_plana="brazo_chaveta",
        cara_plana_angulo="brazo_chaveta_angulo",
        datum="brazo_eje_diametro_radio",
    ),
    "casquillo_rueda": Ficha(
        "anillo: el agujero de 15 de la rueda sobre el árbol de 10",
        {"casquillo_rueda_diametro_radio": 1, "eje_diametro_radio": 1},
        datum="eje_diametro_radio",
    ),
    "eje_balancin": Ficha(
        "sección del eje del balancín: Ø4 con una cara plana",
        {"balancin_eje_diametro_radio": 1},
        segmentos={"balancin_chaveta_cuerda": 1},
        cara_plana="balancin_chaveta",
        cara_plana_angulo="brazo_chaveta_angulo",
        datum="balancin_eje_diametro_radio",
    ),
    "apoyo_balancin": Ficha(
        "bloque con el agujero del eje, el alto sobre X",
        {"balancin_eje_diametro_radio": 1},
        segmentos={"apoyo_balancin_alto": 2, "apoyo_balancin_ancho": 2},
        voladizo="apoyo_balancin_bajo_eje",
        simetrico=True,
        datum="balancin_eje_diametro_radio",
    ),
    "bieleta": Ficha(
        "sección de la varilla",
        {"bieleta_diametro_radio": 1},
        datum="bieleta_diametro_radio",
    ),
    "casquillo_bieleta": Ficha(
        "anillo: el agujero de 3,2 del seguidor sobre la varilla de 2",
        {"casquillo_bieleta_diametro_radio": 1, "bieleta_diametro_radio": 1},
        datum="bieleta_diametro_radio",
    ),
    "tirante": Ficha(
        "sección de la varilla",
        {"tirante_diametro_radio": 1},
        datum="tirante_diametro_radio",
    ),
    "munon": Ficha("sección del muñón", {"eje_diametro_radio": 1}, datum="eje_diametro_radio"),
    "eje_motriz": Ficha(
        "sección del eje motriz", {"eje_diametro_radio": 1}, datum="eje_diametro_radio"
    ),
    "eje_cartucho": Ficha(
        "planta del eje con su valona: el eje, la valona y el pasador sobre +X",
        {"cubo_diametro_radio": 1, "eje_diametro_radio": 1, "pasador_diametro_radio": 1},
        desde_datum=("pasador_radio",),
        datum="eje_diametro_radio",
    ),
    "separador": Ficha(
        "disco con el eje y el pasador de índice sobre +X",
        {"separador_diametro_radio": 1, "eje_diametro_radio": 1, "pasador_diametro_radio": 1},
        desde_datum=("pasador_radio",),
        datum="eje_diametro_radio",
    ),
    "collar": Ficha(
        "anillo: el collar sobre el poste",
        {"collar_seguidor_diametro_radio": 1, "poste_eje_diametro_radio": 1},
        datum="poste_eje_diametro_radio",
    ),
    "tubo_separador": Ficha(
        "anillo: el tubo separador sobre el poste",
        {"tubo_separador_diametro_radio": 1, "tubo_separador_interior_diametro_radio": 1},
        datum="tubo_separador_interior_diametro_radio",
    ),
    "casquillo_rodillo": Ficha(
        "anillo: el casquillo del eje del rodillo",
        {"casquillo_rodillo_diametro_radio": 1, "casquillo_rodillo_interior_diametro_radio": 1},
        datum="casquillo_rodillo_interior_diametro_radio",
    ),
    "calzo_sector": Ficha(
        "barra: paso de la valona y los dos tornillos al sector",
        {
            "calzo_sector_cubo_diametro_radio": 1,
            "calzo_sector_extremo_diametro_radio": 1,
            "amplificador_sector_agujero_diametro_radio": 1,
            "union_sector_seguidor_diametro_radio": 2,
        },
        entre_centros=("union_sector_seguidor_lejos",),
        tangentes=4,
        desde_datum=("union_sector_seguidor_cerca",),
        datum="amplificador_sector_agujero_diametro_radio",
    ),
    "placa_tope": Ficha(
        "brazo corto: poste, pata del muelle y pasador de tope en línea",
        {
            "tope_cubo_diametro_radio": 1,
            "tope_extremo_diametro_radio": 1,
            "poste_eje_diametro_radio": 1,
            "muelle_pata_diametro_radio": 1,
            "tope_pasador_diametro_radio": 1,
        },
        entre_centros=("tope_brazo",),
        tangentes=4,
        desde_datum=("muelle_pata_radio",),
        datum="poste_eje_diametro_radio",
    ),
    "garra": Ficha(
        "anillo: el manguito de la garra",
        {"garra_diametro_radio": 1, "eje_diametro_radio": 1},
        datum="eje_diametro_radio",
    ),
    "bulon_tirante": Ficha(
        "sección del bulón",
        {"brazo_perno_diametro_radio": 1},
        datum="brazo_perno_diametro_radio",
    ),
    "mesa": Ficha(
        "chapa con los dos M2 de las orejetas, el fondo sobre X",
        {"mesa_tornillo_diametro_radio": 2},
        segmentos={"mesa_fondo": 2, "mesa_ancho": 2},
        desde_datum=("mesa_tornillos_entre",),
        voladizo="mesa_tornillo_al_borde",
        simetrico=True,
        datum="mesa_tornillo_diametro_radio",
    ),
    "biela_mesa": Ficha(
        "biela: los dos extremos iguales, sin cara plana",
        {"mesa_biela_extremo_diametro_radio": 2, "mesa_eje_diametro_radio": 2},
        entre_centros=("mesa_biela",),
        tangentes=4,
        datum="mesa_eje_diametro_radio",
    ),
    "eje_mesa_movil": Ficha(
        "sección del eje",
        {"mesa_eje_diametro_radio": 1},
        datum="mesa_eje_diametro_radio",
    ),
    "eje_mesa_fijo": Ficha(
        "sección del eje",
        {"mesa_eje_diametro_radio": 1},
        datum="mesa_eje_diametro_radio",
    ),
    "soporte_mesa": Ficha(
        "bloque con el agujero del eje fijo, el alto sobre X",
        {"mesa_eje_diametro_radio": 1},
        segmentos={"soporte_mesa_alto": 2, "soporte_mesa_fondo": 2},
        voladizo="mesa_bisagra_z",
        simetrico=True,
        datum="mesa_eje_diametro_radio",
    ),
    "orejeta_mesa": Ficha(
        "bloque con el agujero del eje móvil, el alto sobre X",
        {"mesa_eje_diametro_radio": 1},
        segmentos={"orejeta_mesa_alto": 2, "orejeta_mesa_fondo": 2},
        voladizo="mesa_biela_extremo_diametro_radio",
        simetrico=True,
        datum="mesa_eje_diametro_radio",
    ),
    "perno_codo": Ficha(
        "sección del pasador del codo",
        {"brazo_perno_diametro_radio": 1},
        datum="brazo_perno_diametro_radio",
    ),
    "casquillo_punta": Ficha(
        "anillo: el casquillo entre los dos distales",
        {"distal_punta_diametro_radio": 1, "punta_tubo_diametro_radio": 1},
        datum="punta_tubo_diametro_radio",
    ),
    "tubo_punta": Ficha(
        "anillo: el tubo de la punta",
        {"punta_tubo_diametro_radio": 1, "punta_tubo_interior_diametro_radio": 1},
        datum="punta_tubo_interior_diametro_radio",
    ),
    "brazo_horquilla": Ficha(
        "barra de dos cubos iguales con el agujero del tubo en el datum",
        {"horquilla_cubo_diametro_radio": 2, "punta_tubo_diametro_radio": 1},
        entre_centros=("horquilla_largo",),
        tangentes=4,
        datum="punta_tubo_diametro_radio",
    ),
    "poste_horquilla": Ficha(
        "bloque con los dos M2 de las láminas, el alto sobre X",
        {"flexura_tornillo_diametro_radio": 2},
        segmentos={"poste_horquilla_alto": 2, "horquilla_ancho": 2},
        desde_datum=("flexura_separacion",),
        voladizo="poste_horquilla_tornillo_al_pie",
        simetrico=True,
        datum="flexura_tornillo_diametro_radio",
    ),
    "pinza": Ficha(
        "bloque cuadrado con el agujero del portaminas",
        {"pinza_agujero_diametro_radio": 1},
        segmentos={"pinza_ancho": 4},
        voladizo="pinza_al_borde",
        simetrico=True,
        datum="pinza_agujero_diametro_radio",
    ),
    "lamina_flexura": Ficha(
        "lámina desarrollada con los dos M2",
        {"flexura_tornillo_diametro_radio": 2},
        segmentos={"lamina_desarrollo": 2, "flexura_ancho": 2},
        desde_datum=("lamina_entre_tornillos",),
        voladizo="lamina_tornillo_al_borde",
        simetrico=True,
        datum="flexura_tornillo_diametro_radio",
    ),
}
"""Las piezas prismáticas de la plataforma. No hay marco genérico a propósito:
la regla del proyecto es concreto ahora, marco en la máquina 2."""


@dataclass(frozen=True)
class Hallazgo:
    """Un rasgo que falta, que sobra o que no mide lo que debería."""

    gravedad: str
    texto: str


@dataclass
class Informe:
    archivo: str
    pieza: str
    entidades: dict[str, int] = field(default_factory=dict)
    bien: list[str] = field(default_factory=list)
    hallazgos: list[Hallazgo] = field(default_factory=list)
    datum: str = ""
    """Cómo está situada la pieza. **No es un incumplimiento del contrato**:
    el contrato dice formas y distancias, no en qué punto del plano se
    dibujan. Es una convención de trabajo, y se informa aparte para que no
    se confunda un croquis colocado de otra manera con una pieza mal hecha."""

    @property
    def cuadra(self) -> bool:
        return not self.hallazgos


def angulos_en_rad() -> dict[str, float]:
    """Los ángulos del contrato, que `cotas_en_mm` deja fuera a propósito.

    Un DXF no lleva ángulos como dato, pero sí lleva los CENTROS que un
    ángulo sitúa, y la platina es la primera pieza que los tiene fuera de
    +X. Van en su propio diccionario para que nadie sume radianes a
    milímetros, que es la regla 3.
    """
    datos = json.loads(CONTRATOS.read_text(encoding="utf-8"))
    return {
        v["nombre"]: float(v["valor"])
        for grupo in datos["contratos"]
        for v in grupo["valores"]
        if v["unidad"] == "rad"
    }


def circunferencias_de_taladros() -> frozenset[str]:
    """Las cotas que alguna ficha usa como radio de un **patrón circular**.

    Un patrón de más de un agujero no se dibuja agujero a agujero: se traza
    una circunferencia de construcción y se repite sobre ella, y esa
    circunferencia el CAD la acota en **diámetro**. Así que estas cotas son
    circulares aunque su nombre diga «al_centro» o «al_arbol», y les hace
    falta gemelo igual que a un radio.

    Lo dice la ficha y no el nombre a propósito: el nombre ya se entregó, y
    renombrar una cota entregada cuesta reteclear el croquis. Con `cuantos`
    = 1 no hay patrón —se acota la distancia y punto—, y entonces un
    diámetro sería un número que no mide nada.
    """
    return frozenset(r for f in FICHAS.values() for r, _, cuantos in f.polares if cuantos > 1)


def cotas_en_mm() -> dict[str, float]:
    """El contrato en milímetros, **con los gemelos**.

    El exportador saca de cada cota circular su otra forma porque el CAD
    acota el diámetro por defecto; si el gemelo es lo que se teclea, el
    gemelo es lo que tiene que explicar lo que se mide. Los ángulos se
    quedan fuera: un DXF no los lleva como dato.
    """
    datos = json.loads(CONTRATOS.read_text(encoding="utf-8"))
    salida: dict[str, float] = {}
    for grupo in datos["contratos"]:
        for v in grupo["valores"]:
            if v["unidad"] != "m":
                continue
            nombre, valor = v["nombre"], float(v["valor"]) * MM
            salida[nombre] = valor
            if "radio" in nombre or nombre in circunferencias_de_taladros():
                salida[f"{nombre}_diametro"] = valor * 2.0
            elif "diametro" in nombre:
                salida[f"{nombre}_radio"] = valor / 2.0
    return salida


def _circulares(msp) -> list[tuple[tuple[float, float], float]]:
    salida = []
    for e in msp:
        if e.dxf.layer in CAPAS_DE_ADORNO:
            continue
        if e.dxftype() in ("CIRCLE", "ARC"):
            c = e.dxf.center
            salida.append(((round(c.x, 9), round(c.y, 9)), e.dxf.radius))
    return salida


def _fundir(segmentos, tol: float = 1e-6):
    """Une los segmentos colineales que se tocan.

    **Un lado partido en dos sigue siendo un lado.** Onshape parte las
    verticales de un rectángulo por el eje de simetría, y sin fundirlas el
    comparador veía cuatro segmentos de 5 donde hay dos de 10: un falso
    positivo sobre cómo se dibujó, no sobre qué se dibujó. Lo que se compara
    tiene que ser la pieza, no el estilo de croquis.
    """
    sueltos = [list(map(list, s)) for s in segmentos]
    cambio = True
    while cambio:
        cambio = False
        for i, a in enumerate(sueltos):
            for j, b in enumerate(sueltos[i + 1 :], i + 1):
                ua = (a[1][0] - a[0][0], a[1][1] - a[0][1])
                ub = (b[1][0] - b[0][0], b[1][1] - b[0][1])
                if abs(ua[0] * ub[1] - ua[1] * ub[0]) > tol * max(
                    1.0, math.hypot(*ua) * math.hypot(*ub)
                ):
                    continue  # no son paralelos
                for pa in (0, 1):
                    for pb in (0, 1):
                        if math.dist(a[pa], b[pb]) > tol:
                            continue
                        nuevo = [a[1 - pa], b[1 - pb]]
                        # Y colineales de verdad: paralelos y tocándose basta,
                        # pero un pliegue de 180 grados volvería sobre sí mismo.
                        if math.dist(nuevo[0], nuevo[1]) < math.dist(a[0], a[1]):
                            continue
                        sueltos[i] = nuevo
                        del sueltos[j]
                        cambio = True
                        break
                    if cambio:
                        break
                if cambio:
                    break
            if cambio:
                break
    return [(tuple(a), tuple(b)) for a, b in sueltos]


def _segmentos(msp) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    salida = []
    for e in msp:
        if e.dxf.layer in CAPAS_DE_ADORNO:
            continue
        if e.dxftype() == "LINE":
            a, b = e.dxf.start, e.dxf.end
            salida.append(((a.x, a.y), (b.x, b.y)))
        elif e.dxftype() == "LWPOLYLINE":
            puntos = [(p[0], p[1]) for p in e.get_points("xy")]
            if e.closed:
                puntos.append(puntos[0])
            salida += list(itertools.pairwise(puntos))
    return _fundir(salida)


def _unidad_del_step(texto: str) -> float:
    """A cuántos milímetros equivale la unidad del archivo.

    **Se lee, no se supone.** Onshape exporta en metros y la mitad de los CAD
    en milímetros: dar por hecho uno de los dos multiplica toda la pieza por
    mil sin un solo aviso, que es la trampa de las unidades con otro
    disfraz. Si el archivo declara algo que no es un SI de longitud —una
    pulgada convertida, por ejemplo— se para, porque un factor inventado es
    peor que no leer el archivo.
    """
    for prefijo in re.findall(
        r"LENGTH_UNIT\(\)[^;]*?SI_UNIT\(([^,]+),\.METRE\.\)|SI_UNIT\(([^,]+),\.METRE\.\)"
        r"[^;]*?LENGTH_UNIT\(\)",
        texto,
    ):
        p = (prefijo[0] or prefijo[1]).strip()
        if p in ("$", ""):
            return 1000.0
        if p == ".MILLI.":
            return 1.0
        if p == ".CENTI.":
            return 10.0
        raise ValueError(f"el STEP mide en {p}METRE y no sé a cuánto equivale")
    raise ValueError("el STEP no declara una unidad de longitud del SI")


def leer_step(ruta: Path, tol: float = TOLERANCIA):
    """Los círculos y los segmentos de UNA cara del sólido, más su espesor.

    Un sólido extruido trae cada rasgo dos veces, arriba y abajo, así que se
    compara **una sola cara** y lo que las separa es el espesor. La cara que
    se elige es la que tenga más rasgos: en una pieza con un rebaje las dos
    no son iguales, y la que manda es la que describe el contorno entero.

    Sale con una expresión regular y sin kernel a propósito: leer un STEP
    entero pide los 800 MB de OCCT, que son dependencia opcional, y lo que
    hace falta aquí son centros y radios.
    """
    texto = ruta.read_text(encoding="utf-8", errors="replace")
    factor = _unidad_del_step(texto)
    puntos = {
        i: tuple(float(v) for v in xyz.split(","))
        for i, xyz in re.findall(r"#(\d+)\s*=\s*CARTESIAN_POINT\('[^']*',\(([^)]*)\)\)", texto)
    }
    ejes = dict(re.findall(r"#(\d+)\s*=\s*AXIS2_PLACEMENT_3D\('[^']*',#(\d+)", texto))
    vertices = dict(re.findall(r"#(\d+)\s*=\s*VERTEX_POINT\('[^']*',#(\d+)\)", texto))
    rectas = set(re.findall(r"#(\d+)\s*=\s*LINE\(", texto))

    circulos: list[tuple[float, tuple[float, float, float]]] = []
    for eje, radio in re.findall(r"#\d+\s*=\s*CIRCLE\('[^']*',#(\d+),([\d.eE+-]+)\)", texto):
        if eje not in ejes or ejes[eje] not in puntos:
            continue
        circulos.append((float(radio) * factor, puntos[ejes[eje]]))

    segmentos: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
    for v1, v2, curva in re.findall(r"#\d+\s*=\s*EDGE_CURVE\('[^']*',#(\d+),#(\d+),#(\d+),", texto):
        if curva not in rectas or v1 not in vertices or v2 not in vertices:
            continue
        segmentos.append((puntos[vertices[v1]], puntos[vertices[v2]]))

    zs = [c[1][2] for c in circulos] + [p[2] for s in segmentos for p in s]
    if not zs:
        raise ValueError("el STEP no trae ni un círculo ni una arista recta")
    espesor = (max(zs) - min(zs)) * factor

    def cuantos(z: float) -> int:
        return sum(abs(c[1][2] * factor - z) <= tol for c in circulos) + sum(
            abs(a[2] * factor - z) <= tol and abs(b[2] * factor - z) <= tol for a, b in segmentos
        )

    cara = max(sorted({round(z * factor, 6) for z in zs}), key=lambda z: (cuantos(z), z))
    en_la_cara = lambda p: abs(p[2] * factor - cara) <= tol  # noqa: E731
    circulares = [
        ((round(c[0] * factor, 9), round(c[1] * factor, 9)), r)
        for r, c in circulos
        if en_la_cara(c)
    ]
    planos = [
        ((a[0] * factor, a[1] * factor), (b[0] * factor, b[1] * factor))
        for a, b in segmentos
        if en_la_cara(a) and en_la_cara(b)
    ]
    # Se cuenta lo de UNA cara: un sólido trae cada rasgo dos veces y
    # «14 CIRCLE» en un disco de seis agujeros invita a buscar el error donde
    # no está.
    planos = _fundir(planos)
    entidades = {"CIRCLE": len(circulares)} | ({"LINE": len(planos)} if planos else {})
    return entidades, circulares, planos, espesor


def _tangente(a, b, circulares, tol) -> list[float]:
    """Si los dos extremos del segmento se apoyan en sendos círculos y es
    perpendicular al radio en los dos, es una tangente exterior.

    La perpendicularidad se impone, no se mira a ojo: es el error que este
    repo ya cometió dos veces seguidas con la cinta del cabestrante. Devuelve
    el coseno en cada contacto, que debería ser cero.
    """
    cosenos = []
    for p in (a, b):
        for centro, radio in circulares:
            if abs(math.dist(p, centro) - radio) > tol:
                continue
            v = (p[0] - centro[0], p[1] - centro[1])
            u = (b[0] - a[0], b[1] - a[1])
            cos = abs(v[0] * u[0] + v[1] * u[1]) / (radio * math.hypot(*u))
            if cos < 1e-6:
                cosenos.append(cos)
                break
    return cosenos if len(cosenos) == 2 else []


def comparar(ruta: Path, pieza: str, tol: float = TOLERANCIA) -> Informe:
    if pieza not in FICHAS:
        raise KeyError(f"no hay ficha de «{pieza}». Hay: {', '.join(sorted(FICHAS))}")
    ficha, cotas = FICHAS[pieza], cotas_en_mm()
    inf = Informe(archivo=ruta.name, pieza=pieza)
    espesor: float | None = None
    if ruta.suffix.lower() in (".step", ".stp"):
        inf.entidades, circulares, segmentos, espesor = leer_step(ruta, tol)
    else:
        doc = ezdxf.readfile(str(ruta))
        msp = doc.modelspace()
        for e in msp:
            inf.entidades[e.dxftype()] = inf.entidades.get(e.dxftype(), 0) + 1
        circulares, segmentos = _circulares(msp), _segmentos(msp)

    # --- el espesor, que es lo que el croquis no puede traer ---
    if espesor is not None:
        clase, cota = LISTADO[pieza].solido
        esperado = cotas[cota]
        if abs(espesor - esperado) <= tol:
            inf.bien.append(f"{clase} de {esperado:g}   #cota.{cota}")
        else:
            inf.hallazgos.append(
                Hallazgo(
                    "falta",
                    f"#cota.{cota} pide {esperado:g} de {clase} y el sólido mide "
                    f"{espesor:.4f}: el contorno puede estar bien y la pieza no entrar",
                )
            )

    # --- radios: cada rasgo declarado, con su recuento ---
    #
    # **Las cotas se agrupan POR VALOR.** Dos rasgos distintos pueden medir lo
    # mismo y entonces no se distinguen midiendo: en el seguidor el paso del
    # rodillo y los dos del sector son los tres Ø3,2, y el alojamiento del
    # casquillo y el extremo del brazo son los dos Ø10. Pedirlos por separado
    # hacía que cada cota se llevara los tres y sobrara, y a la vez que la
    # siguiente no encontrara ninguno y faltara: cuatro quejas por un dibujo
    # correcto. Lo que identifica un rasgo es DÓNDE está, no cuánto mide, y de
    # eso se encargan `desde_datum` y `entre_centros`.
    pendientes = list(circulares)
    por_valor: dict[float, list[tuple[str, int]]] = {}
    for nombre, cuantos in ficha.radios.items():
        if nombre not in cotas:
            inf.hallazgos.append(Hallazgo("contrato", f"la ficha cita «{nombre}», que no está"))
            continue
        clave = next((v for v in por_valor if abs(v - cotas[nombre]) <= tol), cotas[nombre])
        por_valor.setdefault(clave, []).append((nombre, cuantos))
    for esperado, cuales in por_valor.items():
        cuantos = sum(n for _, n in cuales)
        casan = [c for c in pendientes if abs(c[1] - esperado) <= tol]
        for c in casan:
            pendientes.remove(c)
        quien = " · ".join(f"#cota.{n}" + (f" ×{k}" if len(cuales) > 1 else "") for n, k in cuales)
        if len(casan) == cuantos:
            inf.bien.append(f"R{esperado:g} ×{cuantos}   {quien}")
        else:
            inf.hallazgos.append(
                Hallazgo(
                    "falta" if len(casan) < cuantos else "sobra",
                    f"{quien} piden {cuantos} arco(s) de R{esperado:g} y hay {len(casan)}",
                )
            )
    for centro, radio in pendientes:
        inf.hallazgos.append(
            Hallazgo(
                "huerfano",
                f"R{radio:.4f} en ({centro[0]:g},{centro[1]:g}) no lo explica "
                "ninguna cota de esta pieza",
            )
        )

    # --- del datum al centro de un rasgo ---
    situados: list[tuple[float, float]] = [(0.0, 0.0)]
    for nombre in ficha.desde_datum:
        esperado = cotas[nombre]
        if any(abs(c[0] - esperado) <= tol and abs(c[1]) <= tol for c, _ in circulares):
            situados.append((esperado, 0.0))
            inf.bien.append(f"centro a {esperado:g} del datum   #cota.{nombre}")
        else:
            inf.hallazgos.append(
                Hallazgo("falta", f"#cota.{nombre} pide un centro a {esperado:g} del datum")
            )

    # --- agujeros en polares ---
    for cota_r, cota_a, cuantos in ficha.polares:
        radio = cotas[cota_r]
        # Con `cuantos` > 1 la cota es el REPARTO y los agujeros van a sus
        # múltiplos desde 0; con uno solo, la cota es su propio ángulo.
        angulo = angulos_en_rad()[cota_a]
        cuales = [angulo * i for i in range(cuantos)] if cuantos > 1 else [angulo]
        esperados = [(radio * math.cos(t), radio * math.sin(t)) for t in cuales]
        faltan = [
            (i, t, e)
            for i, (t, e) in enumerate(zip(cuales, esperados, strict=True))
            if not any(math.dist(e, c) <= tol for c, _ in circulares)
        ]
        # Los que SÍ están quedan situados aunque el grupo falle: si no, los
        # dos postes buenos salían luego como centros huérfanos y el informe
        # acusaba de sobrar a lo único que estaba bien.
        sin_sitio = {i for i, _, _ in faltan}
        situados.extend(e for i, e in enumerate(esperados) if i not in sin_sitio)
        if not faltan:
            inf.bien.append(
                f"{cuantos} centro(s) a {radio:g} y {math.degrees(angulo):g}°"
                f"   #cota.{cota_r} · #angulo.{cota_a}"
            )
        for i, t, e in faltan:
            # **Decir qué hay en su lugar, no solo que falta.** La platina
            # volvió dos veces con el tercer poste y el pivote izquierdo
            # cambiados de sitio, y «el peor se queda a 2,85 mm» obliga a
            # reconstruir a mano cuál de los cuatro agujeros es. Con el
            # diámetro de lo más cercano, el informe dice el error: donde va
            # un Ø8 hay un Ø10.
            cerca = min(circulares, key=lambda c: math.dist(e, c[0]), default=None)
            vecino = (
                f", y lo más cerca hay un Ø{2 * cerca[1]:g} a {math.dist(e, cerca[0]):.4f} mm"
                if cerca
                else ""
            )
            cual = f" el {i + 1} de {cuantos}," if cuantos > 1 else ""
            inf.hallazgos.append(
                Hallazgo(
                    "falta",
                    f"#cota.{cota_r} con #angulo.{cota_a} pide{cual} un centro a "
                    f"{radio:g} y {math.degrees(t):g}° y no hay ninguno{vecino}",
                )
            )

    # --- dónde empieza el contorno respecto del datum ---
    if ficha.voladizo:
        esperado = cotas[ficha.voladizo]
        bordes = [min(a[0], b[0]) for a, b in segmentos if abs(a[0] - b[0]) <= tol]
        if not bordes:
            inf.hallazgos.append(
                Hallazgo("falta", f"#cota.{ficha.voladizo}: no hay ningún borde vertical")
            )
        elif abs(min(bordes) + esperado) <= tol:
            inf.bien.append(f"borde a {esperado:g} del datum   #cota.{ficha.voladizo}")
        else:
            inf.hallazgos.append(
                Hallazgo(
                    "falta",
                    f"#cota.{ficha.voladizo} pide el borde a {-esperado:+g} del datum "
                    f"y está a {min(bordes):+g}: el contorno no está donde dice el contrato",
                )
            )

    if ficha.retranqueo:
        esperado = cotas[ficha.retranqueo]
        bordes = [min(a[1], b[1]) for a, b in segmentos if abs(a[1] - b[1]) <= tol]
        if not bordes:
            inf.hallazgos.append(
                Hallazgo("falta", f"#cota.{ficha.retranqueo}: no hay ningún borde horizontal")
            )
        elif abs(min(bordes) + esperado) <= tol:
            inf.bien.append(f"borde de atrás a {esperado:g} del datum   #cota.{ficha.retranqueo}")
        else:
            inf.hallazgos.append(
                Hallazgo(
                    "falta",
                    f"#cota.{ficha.retranqueo} pide el borde de atrás a {-esperado:+g} del "
                    f"datum y está a {min(bordes):+g}: el contorno no está donde dice el "
                    "contrato",
                )
            )

    # --- simetría respecto del eje X ---
    if ficha.simetrico:
        altos = [p[1] for a, b in segmentos for p in (a, b)]
        altos += [c[1] + s * r for c, r in circulares for s in (-1, 1)]
        if altos and abs(max(altos) + min(altos)) <= tol:
            inf.bien.append("contorno simétrico respecto del eje X")
        else:
            inf.hallazgos.append(
                Hallazgo(
                    "falta",
                    f"la pieza debería ser simétrica respecto del eje X y va de "
                    f"{min(altos):+g} a {max(altos):+g}",
                )
            )

    # --- la ranura: dos arcos que son UN rasgo ---
    circulares_sueltos = list(circulares)
    if ficha.ranura:
        recorrido, radio_cota = cotas[ficha.ranura[0]], cotas[ficha.ranura[1]]
        extremos = [c for c in circulares_sueltos if abs(c[1] - radio_cota) <= tol]
        par = [
            (a, b)
            for i, a in enumerate(extremos)
            for b in extremos[i + 1 :]
            if abs(math.dist(a[0], b[0]) - recorrido) <= tol
        ]
        if par:
            a, b = par[0]
            circulares_sueltos.remove(a)
            circulares_sueltos.remove(b)
            medio = ((a[0][0] + b[0][0]) / 2, (a[0][1] + b[0][1]) / 2)
            circulares_sueltos.append((medio, radio_cota))
            inf.bien.append(f"ranura de {recorrido:g} de recorrido   #cota.{ficha.ranura[0]}")
        else:
            inf.hallazgos.append(
                Hallazgo(
                    "falta",
                    f"#cota.{ficha.ranura[0]}: no hay dos arcos de R{radio_cota:g} "
                    f"separados {recorrido:g}",
                )
            )

    # --- distancias entre centros ---
    # Un centro ya situado desde el datum no vuelve a pedir cota, y la
    # distancia entre dos situados es DERIVADA: con cinco agujeros en línea
    # hay diez pares y solo cuatro cotas, así que sin esto el informe saca
    # seis huérfanas de un dibujo que está entero.
    # Un `entre_centros` medido DESDE el datum también sitúa: el rodillo del
    # seguidor está a 45 del pivote por `brazo_seguidor`, no por `desde_datum`,
    # y sin esto sus tres distancias a los demás agujeros salían huérfanas.
    for nombre in ficha.entre_centros:
        situados.append((cotas[nombre], 0.0))

    def situado(p: tuple[float, float]) -> bool:
        return any(math.dist(p, q) <= tol for q in situados)

    centros = sorted({c for c, _ in circulares_sueltos})
    pares = [
        (a, b, math.dist(a, b))
        for i, a in enumerate(centros)
        for b in centros[i + 1 :]
        if math.dist(a, b) > tol
    ]
    for nombre in ficha.entre_centros:
        esperado = cotas[nombre]
        casan = [t for t in pares if abs(t[2] - esperado) <= tol]
        for t in casan:
            pares.remove(t)
        if casan:
            inf.bien.append(f"entre centros {esperado:g}   #cota.{nombre}")
        else:
            cerca = min((t[2] for t in pares), default=0.0)
            inf.hallazgos.append(
                Hallazgo(
                    "falta",
                    f"#cota.{nombre} pide {esperado:g} entre centros"
                    + (f", la más próxima {cerca:.4f}" if pares else ""),
                )
            )
    # Y lo que sobra solo es huérfano si alguno de los dos centros no estaba
    # situado ya: la distancia entre dos situados es derivada, no una cota.
    #
    # **Un centro sin situar se dice UNA vez, no una por pareja.** Con los
    # agujeros en polares, un grupo que falla deja tres centros sueltos y la
    # cuenta de parejas saca catorce líneas de ruido que tapan las dos que
    # importan. Y la queja buena no es «hay una distancia de 122,51 que no
    # está en el contrato», es «este agujero no lo sitúa nada».
    sueltos_de_centro = sorted(
        {a for a, b, _ in pares if not situado(a)} | {b for a, b, _ in pares if not situado(b)}
    )
    for c in sueltos_de_centro:
        inf.hallazgos.append(
            Hallazgo("huerfano", f"un centro en ({c[0]:.4f}, {c[1]:.4f}) que no sitúa ninguna cota")
        )

    # --- segmentos: la cuerda de la cara plana y poco más. Una tangente no
    # es una cota, la coloca la propia tangencia, así que se aparta antes.
    cosenos: list[float] = []
    sueltos = []
    for a, b in segmentos:
        if math.dist(a, b) <= tol:
            continue
        toca = _tangente(a, b, circulares, tol)
        if toca:
            cosenos += toca
        else:
            sueltos.append(math.dist(a, b))
    for nombre, cuantos in ficha.segmentos.items():
        esperado = cotas[nombre]
        casan = [x for x in sueltos if abs(x - esperado) <= tol]
        for x in casan:
            sueltos.remove(x)
        if len(casan) == cuantos:
            inf.bien.append(f"segmento {esperado:g} ×{cuantos}   #cota.{nombre}")
        else:
            inf.hallazgos.append(
                Hallazgo(
                    "falta" if len(casan) < cuantos else "sobra",
                    f"#cota.{nombre} pide {cuantos} segmento(s) de {esperado:g} y hay {len(casan)}",
                )
            )
    for x in sueltos:
        inf.hallazgos.append(Hallazgo("huerfano", f"segmento de {x:.4f} sin cota ni tangencia"))

    # --- la cara plana, con signo ---
    if ficha.cara_plana:
        esperado = cotas[ficha.cara_plana]
        # La normal de la cara: la cuerda es perpendicular a ella, y la
        # distancia del eje al plano se mide sobre ella, con signo.
        girada = angulos_en_rad()[ficha.cara_plana_angulo] if ficha.cara_plana_angulo else 0.0
        nx, ny = math.cos(girada), math.sin(girada)
        cuerda = cotas[next(iter(ficha.segmentos))] if ficha.segmentos else 0.0
        datum = min(
            (c for c, r in circulares if abs(r - cotas[ficha.datum]) <= tol),
            key=lambda c: math.hypot(*c),
            default=None,
        )
        ox, oy = datum if datum else (0.0, 0.0)
        planas = [
            ((a[0] + b[0]) / 2 - ox) * nx + ((a[1] + b[1]) / 2 - oy) * ny
            for a, b in segmentos
            if abs(math.dist(a, b) - cuerda) <= tol
            and abs((b[0] - a[0]) * nx + (b[1] - a[1]) * ny) <= tol
        ]
        if not planas:
            inf.hallazgos.append(
                Hallazgo(
                    "falta",
                    f"#cota.{ficha.cara_plana}: no hay ninguna cara plana con la normal a "
                    f"{math.degrees(girada):g}°",
                )
            )
        elif any(abs(x - esperado) <= tol for x in planas):
            inf.bien.append(f"cara plana a {esperado:g} del eje   #cota.{ficha.cara_plana}")
        else:
            inf.hallazgos.append(
                Hallazgo(
                    "falta",
                    f"#cota.{ficha.cara_plana} pide la cara a {esperado:+g} del eje y está a "
                    f"{planas[0]:+g}: mirando al otro lado cala el brazo media vuelta girado",
                )
            )

    # --- dónde está puesta: ni cota ni incumplimiento, convención ---
    if ficha.datum:
        esperado = cotas[ficha.datum]
        en_origen = [c for c, r in circulares if abs(r - esperado) <= tol and math.hypot(*c) <= tol]
        otros = [c for c, _ in circulares if math.hypot(*c) > tol]
        if not en_origen:
            inf.datum = (
                f"el rasgo datum (#cota.{ficha.datum}) NO está en el origen: "
                "hay que anclarla a mano, y lo que se ancla a mano se ancla mal"
            )
        elif otros and any(abs(c[1]) <= tol and c[0] > tol for c in otros):
            inf.datum = (
                "datum en el origen y el siguiente centro sobre +X: "
                "dos coincidentes y queda totalmente definida"
            )
        elif not otros and not segmentos:
            # Un disco con el agujero concéntrico no tiene giro que quitar: un
            # CÍRCULO no tiene grado de libertad de rotación, así que centro y
            # radios lo definen entero. Y es lo mismo que dice el contrato del
            # sector —«un disco con un agujero no tiene orientación»—, solo que
            # aquí hay que decirlo o el informe pide una cota angular que no
            # existe.
            inf.datum = (
                "todos los rasgos concéntricos en el origen: un círculo no tiene "
                "giro, así que con una coincidente queda totalmente definida"
            )
        elif not otros and ficha.cara_plana:
            # Una pieza de un solo centro —la sección de un eje— no tiene un
            # «centro siguiente». Lo que la orienta es la cara plana, y con
            # su normal en +X el anclaje sigue siendo dos coincidentes.
            inf.datum = (
                "datum en el origen y la cara plana sobre +X: "
                "dos coincidentes y queda totalmente definida"
            )
        elif not otros and ficha.simetrico and segmentos:
            # Un bloque con un solo agujero: el giro lo quita un BORDE, no un
            # segundo centro. Simétrico respecto de X, sus lados largos van en
            # horizontal, y eso es una restricción que el CAD pone de un clic.
            inf.datum = (
                "datum en el origen y un borde horizontal: una coincidente y una "
                "horizontal, y queda totalmente definida"
            )
        else:
            inf.datum = (
                "datum en el origen, pero el segundo centro no cae sobre +X: "
                "el giro hay que quitarlo con una cota angular"
            )

    # --- tangencias ---
    if ficha.tangentes:
        if len(cosenos) == ficha.tangentes:
            inf.bien.append(
                f"{len(cosenos)} contactos tangentes, perpendicularidad peor {max(cosenos):.1e}"
            )
        else:
            inf.hallazgos.append(
                Hallazgo(
                    "falta" if len(cosenos) < ficha.tangentes else "sobra",
                    f"la ficha pide {ficha.tangentes} contactos tangentes y hay "
                    f"{len(cosenos)}: el contorno no son tangentes de verdad",
                )
            )
    return inf


def adivinar(ruta: Path, tol: float = TOLERANCIA) -> str:
    """Qué ficha cuadra, cuando nadie lo dice. La que menos fallos deje."""
    return min(FICHAS, key=lambda p: len(comparar(ruta, p, tol).hallazgos))


def informe(inf: Informe) -> str:
    marca = {
        "falta": "FALTA   ",
        "sobra": "SOBRA   ",
        "huerfano": "HUÉRFANO",
        "contrato": "FICHA   ",
    }
    lineas = [
        f"{inf.archivo}  ·  {inf.pieza}",
        f"  {FICHAS[inf.pieza].que_es}",
        "  " + " · ".join(f"{n} {t}" for t, n in sorted(inf.entidades.items())),
        "",
    ]
    lineas += [f"  = {b}" for b in inf.bien]
    if inf.datum:
        lineas += ["", f"  · situación      {inf.datum}"]
    if inf.hallazgos:
        lineas.append("")
        lineas += [f"  ! {marca[h.gravedad]}  {h.texto}" for h in inf.hallazgos]
    lineas += [
        "",
        "  cuadra con el contrato"
        if inf.cuadra
        else f"  {len(inf.hallazgos)} cosa(s) que no cuadran",
        "",
        "  Ni el DXF ni el STEP llevan las restricciones: comprueba en el CAD",
        "  que el croquis sale «totalmente definida». Uno exacto y suelto se ve",
        "  bien y se mueve luego.",
    ]
    return "\n".join(lineas) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("dxf", type=Path, nargs="+", help="DXF del croquis o STEP del sólido")
    p.add_argument("--pieza", choices=sorted(FICHAS), help="por defecto, la que mejor cuadre")
    p.add_argument("--tol", type=float, default=TOLERANCIA, help="en mm")
    op = p.parse_args(argv)
    malos = 0
    for ruta in op.dxf:
        inf = comparar(ruta, op.pieza or adivinar(ruta, op.tol), op.tol)
        print(informe(inf))
        malos += not inf.cuadra
    return 1 if malos else 0


if __name__ == "__main__":
    raise SystemExit(main())
