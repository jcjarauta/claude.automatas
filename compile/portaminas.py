"""El portaminas decide dónde va el plato 1.

`base_al_plato` lleva desde el principio un «75 provisional» porque lo fija
cómo se sujeta el lápiz. Ahora que el lápiz se sujeta de una manera
concreta —el tubo hueco de la punta, la horquilla y la pinza, colgados del
plato 1— lo que lo fija se puede escribir:

- la PINZA aprieta una franja fija respecto del plato 1 —sus `pinza_largo`
  bajo el tope, que está a `horquilla_espesor + poste_horquilla_alto`— y esa
  franja tiene que caer sobre el plástico liso: por encima del agarre
  metálico de delante y por debajo del clip, con `holgura_minima`;
- el TUBO de la punta no aprieta: el lápiz pasa por dentro con holgura, así
  que puede quedar sobre el agarre si el agarre cabe por él. Si no cabe, el
  tubo también tiene que quedar por encima del agarre;
- y el tubo, que baja `punta_tubo_largo` bajo el plato 1, tiene que librar
  la mesa con `holgura_minima`.

Eso da una ventana. Las cinco medidas del lápiz no las da el fabricante
(ni Staedtler ni las tiendas coinciden en el diámetro), así que se miden con
pie de rey y se pasan por `scripts/medir_portaminas.py`.

Milímetros, como el contrato en `contrato_mm`: aquí no hay núcleo, hay una
regla de montaje.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

HOLGURA_DEL_AGUJERO = 0.1
"""Lo que la pinza se taladra por encima del cuerpo medido, en diámetro. El
prisionero M3 cierra el resto; más justo no entra un lápiz de plástico con su
tolerancia de inyección."""

HOLGURA_EN_EL_TUBO = 0.2
"""Lo mínimo que tiene que sobrar entre el cuerpo y el interior del tubo de
la punta, en diámetro, para que el lápiz entre sin forzar."""


@dataclass(frozen=True)
class Portaminas:
    """Las cinco medidas que deciden el montaje, en mm."""

    longitud: float
    """De la punta de la mina, con la mina asomando lo que asoma al escribir,
    a lo alto del pulsador."""
    cuerpo: float
    """Diámetro del cuerpo de plástico liso, donde aprieta la pinza."""
    agarre: float
    """De la punta de la mina a donde ACABA el agarre metálico de delante."""
    clip: float
    """De lo alto del pulsador al pie del clip."""
    agarre_diametro: float
    """El diámetro MAYOR del agarre metálico: decide si pasa por el tubo."""

    @classmethod
    def del_catalogo(cls, ficha: dict[str, Any]) -> Portaminas:
        cotas = {k["nombre"]: float(k["valor"]) * 1000.0 for k in ficha["cotas"]}
        return cls(
            longitud=cotas["longitud"],
            cuerpo=cotas["cuerpo"],
            agarre=cotas["agarre"],
            clip=cotas["clip"],
            agarre_diametro=cotas["agarre_diametro"],
        )


@dataclass(frozen=True)
class Ventana:
    minimo: float
    maximo: float

    def admite(self, base_al_plato: float) -> bool:
        return self.minimo - 1e-9 <= base_al_plato <= self.maximo + 1e-9


def ventana(lapiz: Portaminas, c: dict[str, float]) -> Ventana:
    """Entre qué valores de `base_al_plato` el portalápiz agarra plástico liso."""
    hueco = c["punta_tubo_interior_diametro"] - lapiz.cuerpo
    if hueco < HOLGURA_EN_EL_TUBO:
        raise ValueError(
            f"el cuerpo de {lapiz.cuerpo:g} no pasa por el tubo de la punta "
            f"({c['punta_tubo_interior_diametro']:g} por dentro): sobran {hueco:.2f}"
        )
    tope_de_la_pinza = c["horquilla_espesor"] + c["poste_horquilla_alto"]
    pie_de_la_pinza = tope_de_la_pinza - c["pinza_largo"]
    punta, h = c["mesa_altura"], c["holgura_minima"]
    fin_del_agarre = punta + lapiz.agarre + h
    minimos = [
        fin_del_agarre - pie_de_la_pinza,  # la pinza, sobre plástico
        punta + h + c["punta_tubo_largo"],  # el tubo, por encima de la mesa
    ]
    if c["punta_tubo_interior_diametro"] - lapiz.agarre_diametro < HOLGURA_EN_EL_TUBO:
        minimos.append(fin_del_agarre + c["punta_tubo_largo"])  # el tubo no lo traga
    maximo = punta + lapiz.longitud - lapiz.clip - h - tope_de_la_pinza
    return Ventana(max(minimos), maximo)


def recomendar(
    lapiz: Portaminas, c: dict[str, float], actual: float, modo: str = "cercano"
) -> float:
    """Qué `base_al_plato` tomar dentro de la ventana.

    - "cercano", con el portaminas MEDIDO: lo más cerca del valor actual,
      porque mover el plato 1 mueve la máquina entera.
    - "centro", con el portaminas ESTIMADO: el centro de la ventana, que es
      lo que más aguanta cuando lleguen las medidas de verdad y la ventana se
      corra unos milímetros. Elegir el borde con números estimados es elegir
      volver a mover la máquina.
    """
    v = ventana(lapiz, c)
    if v.minimo > v.maximo:
        raise ValueError(
            f"el portalápiz no cabe en el plástico liso: hace falta "
            f"base_al_plato ≥ {v.minimo:g} por el agarre y ≤ {v.maximo:g} por el clip"
        )
    if modo == "centro":
        return (v.minimo + v.maximo) / 2
    if modo != "cercano":
        raise ValueError(f"modo «{modo}»: o «cercano» o «centro»")
    return min(max(actual, v.minimo), v.maximo)


def agujero_de_la_pinza(lapiz: Portaminas) -> float:
    return lapiz.cuerpo + HOLGURA_DEL_AGUJERO


__all__ = ["Portaminas", "Ventana", "agujero_de_la_pinza", "recomendar", "ventana"]
