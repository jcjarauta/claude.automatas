"""La interfaz local de pedidos: teclear una frase y llevarse el cartucho.

    uv run --group web uvicorn api.main:app --reload
    # y abrir http://127.0.0.1:8000

**Qué es y qué no.** Es el front-end de captura más barato que existe
—en vez de dibujar la frase, se teclea— enchufado a la cadena que ya
estaba: `core.tipografia` da los trazos, el compilador hace las levas y
`compile.cli` escribe el paquete.

**No ejecuta comandos propios.** El paquete lo escribe el mismo CLI que
se usa desde el terminal, llamado como función. Si esta capa tuviera su
propia copia de ese trabajo, serían dos sitios donde vive lo mismo y se
separarían a la tercera semana: el pedido de la web y el del terminal
tienen que salir byte a byte iguales.

**Ni un modelo de lenguaje en este camino.** Regla 4: mismo input, misma
geometría. De un texto a una leva solo pasan la fuente y el compilador,
los dos deterministas.
"""

from __future__ import annotations

import itertools
import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from compile.escribiente import Compilacion, Escribiente, compilar
from compile.renglones import compilar_por_renglones
from compile.texto import ALTURA_DE_X, composicion_de, fuentes, huecos_de
from core.errors import ErrorDeDominio
from core.escritura import Escritura
from core.tipografia import ENLACE, Composicion
from core.units import TAU, Metros, a_mm, mm
from emit.patron import patron_de

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = RAIZ / "web" / "index.html"
PEDIDOS = RAIZ / "build" / "pedidos"

app = FastAPI(title="Escribiente · pedidos", docs_url="/api/docs")


# ---------------------------------------------------------------------------
# Lo que entra y lo que sale
# ---------------------------------------------------------------------------


class Peticion(BaseModel):
    texto: str = Field(min_length=1, max_length=240)
    """Un salto de línea es un renglón, y **un renglón es un cartucho**: tres
    levas más y cambiarlo a mitad de la frase. Por eso lo parte quien pide y
    no el programa."""
    fuente: str = "cursiva"
    altura_de_x_mm: float = Field(default=float(a_mm(ALTURA_DE_X)), gt=1.0, le=60.0)
    enlace: float = Field(default=ENLACE, ge=0.0, le=2.0)


def _trazos_mm(escritura: Escritura) -> list[list[list[float]]]:
    """Los trazos en milímetros, que es como los dibuja el navegador."""
    return [
        [[round(a_mm(Metros(x)), 4), round(a_mm(Metros(y)), 4)] for x, y in t.puntos]
        for t in escritura.trazos
    ]


def _componer(peticion: Peticion) -> Composicion:
    try:
        return composicion_de(
            peticion.texto,
            fuente=peticion.fuente,
            altura_de_x=mm(peticion.altura_de_x_mm),
            enlace=peticion.enlace,
        )
    except (ErrorDeDominio, ValueError, FileNotFoundError) as fallo:
        # Un carácter que la fuente no tiene no es un error del servidor:
        # es una respuesta legítima que hay que poder enseñar.
        raise HTTPException(status_code=422, detail=str(fallo)) from fallo


# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------


@app.get("/api/fuentes")
def listar_fuentes() -> dict[str, Any]:
    return {"fuentes": fuentes(), "altura_de_x_mm": float(a_mm(ALTURA_DE_X)), "enlace": ENLACE}


@app.post("/api/trazos")
def ver_trazos(peticion: Peticion) -> dict[str, Any]:
    """El texto como trazos, sin compilar. Es la vista previa: instantánea.

    Compilar tarda segundos; ver cómo queda la frase tiene que ser
    inmediato o nadie prueba una segunda opción.
    """
    compuesta = _componer(peticion)
    escritura = compuesta.escritura
    # Los huecos van aquí y no en `/api/capacidad` porque el deslizante los
    # necesita en cada tecla y esto cuesta milisegundos: son los trazos de
    # la fuente puestos en fila, sin leva ninguna.
    separaciones = huecos_de(
        peticion.texto, fuente=peticion.fuente, altura_de_x=mm(peticion.altura_de_x_mm)
    )
    # La tinta que deja la frase. Con ella, lo que el enlace añade al unir
    # un hueco deja de ser un número suelto y pasa a ser un porcentaje:
    # 64 mm de raya suenan a poco hasta que son el 12 % de la letra.
    tinta = sum(
        math.dist(a, b)
        for t in escritura.trazos
        for a, b in itertools.pairwise([(float(x), float(y)) for x, y in t.puntos])
    )
    return {
        "trazos": _trazos_mm(escritura),
        "renglones": [list(r) for r in compuesta.renglones],
        "huecos": sorted(round(h, 3) for r in separaciones for h in r),
        "tinta_mm": round(a_mm(Metros(tinta)), 1),
        "ancho_mm": round(a_mm(escritura.ancho), 2),
        "alto_mm": round(a_mm(escritura.alto), 2),
    }


FALTA_MEDIR = "falta_medir_el_trazo"
"""La incidencia que solo existe en el camino corto: hay levas recortadas y
nadie ha recorrido todavía las levas para ver cuánto redondean la letra."""


def _estado(compilacion: Compilacion) -> str:
    """Tres estados, no dos.

    `Veredicto.apto` es un booleano honesto —no se ha encontrado ningún
    error— pero en la vista previa eso no es lo mismo que «cabe»: faltan por
    medir las levas recortadas. Decir «sí» aquí sería prometer un número que
    nadie ha calculado, y es justo el número por el que «Gracias» no pasa.
    """
    if not compilacion.veredicto.apto:
        return "no"
    if any(i.codigo == FALTA_MEDIR for i in compilacion.veredicto.incidencias):
        return "falta_medir"
    return "si"


def _reparto(compilacion: Compilacion) -> dict[str, float]:
    """Cómo se han repartido los 360°: lo que queda en el papel y lo que se
    come el lápiz en el aire. Es el presupuesto de la máquina, y la frase o
    cabe dentro de él o no cabe.

    **`necesario_grados` no es decorativo.** Cuando los mínimos pasan de una
    vuelta, `repartir` ya no reparte: devuelve un corte proporcional «para
    poder enseñar cómo quedaría». Dibujar esos dos números como si fueran el
    presupuesto pinta una barra sanísima —281° de tinta— justo al lado de un
    «no cabe», y más sana que la de una frase que casi cabe. El número que
    manda ahí es cuánto piden los mínimos, y lo publica el núcleo.
    """
    tinta = sum(float(t.arco) for t in compilacion.tramos if t.clase == "trazo")
    vuelo = sum(float(t.arco) for t in compilacion.tramos if t.clase == "vuelo")
    necesario = compilacion.veredicto.metricas.get("arco_minimo_necesario", 0.0)
    return {
        "tinta_grados": round(tinta * 360.0 / TAU, 1),
        "vuelo_grados": round(vuelo * 360.0 / TAU, 1),
        "necesario_grados": round(necesario * 360.0 / TAU, 1),
        "cabe_por_minimos": float(necesario < TAU),
        "trazos": float(sum(1 for t in compilacion.tramos if t.clase == "trazo")),
    }


ORDEN = {"no": 0, "falta_medir": 1, "si": 2}
"""De peor a mejor. El estado del pedido es el **peor** de sus renglones:
que dos de tres quepan no sirve de nada, porque la frase se entrega entera."""


def _medida(compilacion: Compilacion) -> dict[str, Any]:
    veredicto = compilacion.veredicto
    return {
        "estado": _estado(compilacion),
        "reparto": _reparto(compilacion),
        "incidencias": [i.model_dump(mode="json") for i in veredicto.incidencias],
        "metricas": {k: round(v, 5) for k, v in veredicto.metricas.items()},
    }


def _compilaciones(compuesta: Composicion, simular: bool) -> list[Compilacion]:
    """Una compilación por renglón, o una sola si no hay saltos de línea.

    Con un renglón no se pasa por `compilar_por_renglones` para que el
    camino de siempre siga siendo literalmente el de siempre: un pedido de
    una vuelta tiene que dar el mismo DXF que antes de que existieran los
    renglones, y eso lo vigila el golden.
    """
    if len(compuesta.renglones) == 1:
        return [compilar(compuesta.escritura, simular_el_trazo=simular)]
    return compilar_por_renglones(
        compuesta.escritura, compuesta.renglones, simular_el_trazo=simular
    )


@app.post("/api/capacidad")
def medir_capacidad(peticion: Peticion) -> dict[str, Any]:
    """¿Cabe la frase? El mismo camino del pedido, parado antes de simular.

    Saber que no cabe tiene que costar lo que cuesta teclearlo. Recorrer las
    levas tarda cuarenta y cinco segundos con dos recortadas; todo lo de
    antes —reparto de θ, cinemática inversa, las tres levas y la envolvente
    de C3— tarda medio segundo y es casi todo el veredicto.

    No es un atajo ni una estimación: es `compilar` con una parada. Un
    predictor aparte diría que cabe algo que luego no cabe, y esa es la
    manera más rápida de que nadie se fíe de la vista previa.

    Con varios renglones se mide **cada uno por su lado**, porque cada uno
    es un cartucho con su propia vuelta y su propio veredicto. Lo que se
    reparte entre renglones no son los grados: son las letras.
    """
    compuesta = _componer(peticion)
    medidas = [_medida(c) for c in _compilaciones(compuesta, simular=False)]
    peor = min(medidas, key=lambda m: ORDEN[m["estado"]])
    return {
        "estado": peor["estado"],
        "renglones": medidas,
        "cartuchos": len(medidas),
        "levas": 3 * len(medidas),
        # Compatibilidad con el camino de un solo renglón, que es el 90 % de
        # los pedidos: los dos campos de siempre, los del peor renglón.
        "reparto": peor["reparto"],
        "incidencias": peor["incidencias"],
        "metricas": peor["metricas"],
    }


def _nombre_de_carpeta(texto: str) -> str:
    limpio = re.sub(r"[^a-zA-Z0-9]+", "-", texto).strip("-").lower()[:40] or "pedido"
    return f"{datetime.now(UTC):%Y%m%d-%H%M%S}-{limpio}"


@app.post("/api/pedido")
def hacer_pedido(peticion: Peticion) -> dict[str, Any]:
    """Compila el pedido y deja el paquete en disco. Puede tardar.

    Con varios renglones salen varios cartuchos, cada uno en su carpeta
    `renglon_N`. Eso ya lo sabe hacer el CLI desde que existe
    `compile.renglones`: aquí solo se escribe el reparto en el JSON del
    pedido y se le deja hacer.
    """
    from compile.cli import main as compilar_desde_cli

    compuesta = _componer(peticion)
    carpeta = PEDIDOS / _nombre_de_carpeta(peticion.texto)
    carpeta.mkdir(parents=True, exist_ok=True)
    entrada = carpeta / "escritura.json"
    pedido: dict[str, Any] = {
        "nombre": peticion.texto.replace("\n", " "),
        "trazos": _trazos_mm(compuesta.escritura),
    }
    # Sin `renglones` el CLI compila una sola vuelta, que es lo de siempre.
    if len(compuesta.renglones) > 1:
        pedido["renglones"] = [list(r) for r in compuesta.renglones]
    entrada.write_text(json.dumps(pedido, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    compilaciones = _compilaciones(compuesta, simular=True)
    # El paquete lo escribe el CLI, no esta capa: un solo sitio donde
    # vive qué archivos lleva un pedido.
    compilar_desde_cli([str(entrada), "--out", str(carpeta)])

    maquina = Escribiente()
    ancho = a_mm(maquina.caja_ancho)
    alto = a_mm(maquina.caja_alto)
    centro_y = a_mm(maquina.caja_centro_y)
    caja = (-ancho / 2.0, centro_y - alto / 2.0, ancho, alto)

    def _simulado(compilacion: Compilacion) -> dict[str, list[list[list[float]]]]:
        """El recorrido partido en tramos, como en la hoja de trazo patrón.

        **Dibujado de una tirada, miente.** `Simulacion.escritos` quita los
        puntos en vuelo, así que unir lo que queda con una polilínea traza
        rayas de una letra a otra que la máquina no dibuja. Con dos
        renglones es aún peor: los une entre sí, y son dos cartuchos que no
        comparten vuelta. `emit.patron` ya resolvía esto para el papel —
        «sin partirlo, la hoja mostraría líneas que la máquina no dibuja»—
        y lo que faltaba era que la pantalla mirase lo mismo.
        """
        if compilacion.simulacion is None:
            return {"tinta": [], "vuelo": []}
        patron = patron_de(
            nombre=compilacion.escritura.nombre,
            puntos=compilacion.simulacion.puntos,
            altura=compilacion.simulacion.altura,
            caja=caja,
            error_del_modelo=compilacion.simulacion.error_maximo * 1000.0,
        )

        def _redondo(tramos: object) -> list[list[list[float]]]:
            return [[[round(x, 3), round(y, 3)] for x, y in t] for t in tramos]  # type: ignore[attr-defined]

        return {"tinta": _redondo(patron.escritos), "vuelo": _redondo(patron.vuelo)}

    uno = len(compilaciones) == 1
    renglones: list[dict[str, Any]] = [
        {
            "numero": numero,
            "carpeta": "" if uno else f"renglon_{numero}",
            "apto": c.veredicto.apto,
            "incidencias": [i.model_dump(mode="json") for i in c.veredicto.incidencias],
            "metricas": {k: round(v, 5) for k, v in c.veredicto.metricas.items()},
            "trazos": _trazos_mm(c.escritura),
            "simulado": _simulado(c),
            "archivos": sorted(_relativos(carpeta / ("" if uno else f"renglon_{numero}"), carpeta)),
        }
        for numero, c in enumerate(compilaciones, start=1)
    ]
    return {
        "pedido": carpeta.name,
        # Entero o nada: la frase se entrega completa, así que un renglón
        # que no cabe deja el pedido fuera aunque los otros dos salgan.
        "apto": all(r["apto"] for r in renglones),
        "cartuchos": len(renglones),
        "levas": 3 * len(renglones),
        "renglones": renglones,
        # Lo de siempre, para el camino de un solo renglón: la unión de todo.
        "incidencias": [i for r in renglones for i in r["incidencias"]],
        "metricas": renglones[0]["metricas"],
        "trazos": [t for r in renglones for t in r["trazos"]],
        "simulado": {
            "tinta": [t for r in renglones for t in r["simulado"]["tinta"]],
            "vuelo": [t for r in renglones for t in r["simulado"]["vuelo"]],
        },
        "archivos": sorted({a for r in renglones for a in r["archivos"]}),
    }


def _relativos(donde: Path, raiz: Path) -> list[str]:
    """Los archivos del paquete, con su ruta desde la carpeta del pedido.

    Con renglones el paquete sale en subcarpetas, así que el nombre a secas
    ya no basta: tres `informe.md` colapsarían en uno y los enlaces de
    descarga se pisarían entre sí.
    """
    if not donde.is_dir():
        return []
    return [
        str(f.relative_to(raiz)).replace("\\", "/")
        for f in donde.rglob("*")
        if f.is_file() and f.name != "escritura.json"
    ]


@app.get("/api/pedido/{pedido}/{archivo:path}")
def descargar(pedido: str, archivo: str) -> FileResponse:
    carpeta = (PEDIDOS / pedido).resolve()
    ruta = (carpeta / archivo).resolve()
    # Sin esto, un `archivo` con «..» sirve cualquier cosa del disco. Y se
    # comprueba contra la carpeta DEL PEDIDO, no contra `pedidos`: con la
    # raíz valdría «../otro-pedido/informe.md», que no saca nada del disco
    # pero tampoco es lo que el enlace dice que es.
    if not ruta.is_file() or carpeta not in ruta.parents:
        raise HTTPException(status_code=404, detail="no existe")
    return FileResponse(ruta, filename=Path(archivo).name)


@app.get("/")
def pagina() -> FileResponse:
    return FileResponse(PAGINA)
