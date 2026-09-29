"""Excepciones de dominio.

Convención del proyecto, de CLAUDE.md: **un fallo de envolvente no es una
excepción**. Que un perfil no sea fabricable, que una frase no quepa o que un
par se pase del presupuesto son resultados del cálculo y viajan en un
`Veredicto`.

Aquí solo viven los fallos que sí son errores de programa: pedir un actuador
que no existe, un contrato que no se cumple, una ficha mal cableada que llegó
sin validar.
"""

from __future__ import annotations


class ErrorDeDominio(Exception):
    """Raíz de los errores propios. Nunca se lanza directamente."""


class ActuadorDesconocido(ErrorDeDominio):
    """La ficha nombra una cinemática que no está en el registro."""


class ContratoIncumplido(ErrorDeDominio):
    """Un módulo no encaja en la bahía o el eje que dice cumplir."""


class FueraDeAlcance(ErrorDeDominio):
    """Se pide al actuador un punto al que no llega.

    Es geometría imposible, no un límite de diseño: por eso es excepción y no
    incidencia. Quien compila debe preguntar antes con `alcanzable()` y
    devolver un veredicto en condiciones.
    """


__all__ = [
    "ActuadorDesconocido",
    "ContratoIncumplido",
    "ErrorDeDominio",
    "FueraDeAlcance",
]
