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

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from compile.escribiente import Compilacion, compilar
from compile.texto import ALTURA_DE_X, escritura_de, fuentes
from core.errors import ErrorDeDominio
from core.escritura import Escritura
from core.tipografia import ENLACE
from core.units import TAU, Metros, a_mm, mm

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = RAIZ / "web" / "index.html"
PEDIDOS = RAIZ / "build" / "pedidos"

app = FastAPI(title="Escribiente · pedidos", docs_url="/api/docs")


# ---------------------------------------------------------------------------
# Lo que entra y lo que sale
# ---------------------------------------------------------------------------


class Peticion(BaseModel):
    texto: str = Field(min_length=1, max_length=120)
    fuente: str = "cursiva"
    altura_de_x_mm: float = Field(default=float(a_mm(ALTURA_DE_X)), gt=1.0, le=60.0)
    enlace: float = Field(default=ENLACE, ge=0.0, le=2.0)


def _trazos_mm(escritura: Escritura) -> list[list[list[float]]]:
    """Los trazos en milímetros, que es como los dibuja el navegador."""
    return [
        [[round(a_mm(Metros(x)), 4), round(a_mm(Metros(y)), 4)] for x, y in t.puntos]
        for t in escritura.trazos
    ]


def _componer(peticion: Peticion) -> Escritura:
    try:
        return escritura_de(
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
    escritura = _componer(peticion)
    return {
        "trazos": _trazos_mm(escritura),
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
    """
    compilacion = compilar(_componer(peticion), simular_el_trazo=False)
    veredicto = compilacion.veredicto
    return {
        "estado": _estado(compilacion),
        "reparto": _reparto(compilacion),
        "incidencias": [i.model_dump(mode="json") for i in veredicto.incidencias],
        "metricas": {k: round(v, 5) for k, v in veredicto.metricas.items()},
    }


def _nombre_de_carpeta(texto: str) -> str:
    limpio = re.sub(r"[^a-zA-Z0-9]+", "-", texto).strip("-").lower()[:40] or "pedido"
    return f"{datetime.now(UTC):%Y%m%d-%H%M%S}-{limpio}"


@app.post("/api/pedido")
def hacer_pedido(peticion: Peticion) -> dict[str, Any]:
    """Compila el pedido y deja el paquete en disco. Puede tardar."""
    from compile.cli import main as compilar_desde_cli

    escritura = _componer(peticion)
    carpeta = PEDIDOS / _nombre_de_carpeta(peticion.texto)
    carpeta.mkdir(parents=True, exist_ok=True)
    entrada = carpeta / "escritura.json"
    entrada.write_text(
        json.dumps(
            {"nombre": peticion.texto, "trazos": _trazos_mm(escritura)},
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )

    compilacion = compilar(escritura)
    veredicto = compilacion.veredicto
    # El paquete lo escribe el CLI, no esta capa: un solo sitio donde
    # vive qué archivos lleva un pedido.
    compilar_desde_cli([str(entrada), "--out", str(carpeta)])

    simulado = (
        [
            [round(a_mm(Metros(x)), 3), round(a_mm(Metros(y)), 3)]
            for x, y in compilacion.simulacion.escritos
        ]
        if compilacion.simulacion is not None
        else []
    )
    return {
        "pedido": carpeta.name,
        "apto": veredicto.apto,
        "incidencias": [i.model_dump(mode="json") for i in veredicto.incidencias],
        "metricas": {k: round(v, 5) for k, v in veredicto.metricas.items()},
        "trazos": _trazos_mm(compilacion.escritura),
        "simulado": simulado,
        "archivos": sorted(
            f.name for f in carpeta.rglob("*") if f.is_file() and f.name != "escritura.json"
        ),
    }


@app.get("/api/pedido/{pedido}/{archivo}")
def descargar(pedido: str, archivo: str) -> FileResponse:
    carpeta = (PEDIDOS / pedido).resolve()
    ruta = (carpeta / archivo).resolve()
    # Sin esto, un `archivo` con «..» sirve cualquier cosa del disco.
    if not ruta.is_file() or PEDIDOS.resolve() not in ruta.parents:
        raise HTTPException(status_code=404, detail="no existe")
    return FileResponse(ruta, filename=archivo)


@app.get("/")
def pagina() -> FileResponse:
    return FileResponse(PAGINA)
