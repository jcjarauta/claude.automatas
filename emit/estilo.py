"""Un solo estilo para todas las hojas: colores, grosores, cuerpos, flecha y
las leyendas del cajetín.

Lo leen el dossier (`emit.dossier`), las fichas (`emit.fichas`), el acotado
(`emit.acotado`) y las hojas SVG de `scripts/` (`scripts/acotar.py`). Antes
cada uno llevaba el suyo, y una cota con la flecha de un tamaño en una hoja y
de otro en la siguiente se lee como si fueran dos documentos distintos, y son
el mismo juego de piezas.

Los colores de cada grupo no están aquí: son parte de la declaración del grupo
(`emit.montaje.GRUPOS`), que es donde se decide qué es cada subsistema.

Medidas en mm de la hoja; cuerpos de letra en puntos.
"""

from __future__ import annotations

# --- colores ---------------------------------------------------------------
TINTA = "#1b1b1b"
"""Aristas visibles, texto."""
COTA = "#b03030"
"""Líneas de cota, flechas y sus números."""
GRIS = "#8a8f96"
"""Aristas ocultas, extensiones de las cotas por coordenadas."""
AUXILIAR = "#9aa7b4"
"""Líneas auxiliares de las hojas SVG."""
REFERENCIA = "#1b5fb0"
"""Las referencias a la tabla de variables y los nombres de variable."""
SUAVE = "#41464d"
"""Rótulos de vista y cabeceras."""
FILETE = "#c4c7cc"
"""Filetes de las tablas."""

# --- grosores (mm) ---------------------------------------------------------
VISIBLE = 0.35
OCULTA = 0.13
LINEA_DE_COTA = 0.18
EXTENSION = 0.10
RAYADO = 0.12
MARCO = 0.5
CAJETIN = 0.35
DISCONTINUA = (1.2, 0.8)
"""Trazo y hueco de las aristas ocultas."""
TRAZO_Y_PUNTO = (3.0, 0.8, 0.5, 0.8)
"""Eje y plano de corte."""

# --- flecha (mm) -----------------------------------------------------------
FLECHA_LARGO = 2.2
FLECHA_ANCHO = 0.7
"""Medio ancho de la base de la flecha."""

# --- cuerpos (pt) ----------------------------------------------------------
FUENTE = "Helvetica"
FUENTE_NEGRITA = "Helvetica-Bold"
CUERPO_COTA = 7.0
CUERPO_REFERENCIA = 5.0
CUERPO_TABLA = 5.4
CUERPO_TEXTO = 5.6
CUERPO_ROTULO_DE_VISTA = 7.0
CUERPO_TITULO = 12.0

# --- leyendas --------------------------------------------------------------
NO_MEDIR = "No medir sobre esta hoja: para cortar, plantillas.pdf"
"""Junto a la escala de toda hoja que no va a 1:1. Las vistas van a escalas
distintas —1:1, 2:1— y la isométrica a ninguna: el día que alguien mida, el
tambor le sale del doble. Es la frontera que separa el dossier de las
plantillas, dicha donde se lee."""

ESCALA_VARIAS = "varias, sin escala"
"""La escala de una hoja con vistas a escalas distintas, como la de grupo."""


__all__ = [
    "AUXILIAR",
    "CAJETIN",
    "COTA",
    "CUERPO_COTA",
    "CUERPO_REFERENCIA",
    "CUERPO_ROTULO_DE_VISTA",
    "CUERPO_TABLA",
    "CUERPO_TEXTO",
    "CUERPO_TITULO",
    "DISCONTINUA",
    "ESCALA_VARIAS",
    "EXTENSION",
    "FILETE",
    "FLECHA_ANCHO",
    "FLECHA_LARGO",
    "FUENTE",
    "FUENTE_NEGRITA",
    "GRIS",
    "LINEA_DE_COTA",
    "MARCO",
    "NO_MEDIR",
    "OCULTA",
    "RAYADO",
    "REFERENCIA",
    "SUAVE",
    "TINTA",
    "TRAZO_Y_PUNTO",
    "VISIBLE",
]
