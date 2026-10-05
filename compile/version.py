"""De qué versión del repositorio sale un documento.

Toda hoja que se pueda imprimir suelta lleva el commit en su cajetín: una
hoja fotocopiada sin versión sobrevive al diseño que la generó, y entonces
no hay forma de saber cuál de dos papeles es el viejo.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def version_del_repositorio(raiz: Path = RAIZ) -> str:
    """«commit abc1234», con «+cambios» si el árbol tiene cambios sin
    guardar: una hoja de un árbol sucio no es la de ese commit."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=raiz,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        sucio = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=raiz,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "sin control de versiones"
    return f"commit {commit}" + (" +cambios" if sucio else "")


__all__ = ["version_del_repositorio"]
