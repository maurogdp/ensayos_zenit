#!/usr/bin/env python3
"""Analiza y describe los archivos en una carpeta.

Este script lista los archivos contenidos en la carpeta indicada y
proporciona una breve descripci\u00f3n de cada uno, incluyendo su tama\u00f1o,
su tipo seg\u00fan la extensi\u00f3n y, si es un archivo de texto, el n\u00famero de
l\u00edneas y la primera l\u00ednea del archivo.
"""

from __future__ import annotations

import argparse
import mimetypes
from pathlib import Path
from typing import Iterable, Dict, Any


def describir_archivo(ruta: Path) -> Dict[str, Any]:
    """Devuelve informaci\u00f3n sobre un archivo."""
    info: Dict[str, Any] = {
        "nombre": ruta.name,
        "tamanio": ruta.stat().st_size,
        "tipo": mimetypes.guess_type(str(ruta))[0] or "desconocido",
    }

    texto_permitido = {".txt", ".csv", ".md", ".py"}
    if ruta.suffix.lower() in texto_permitido:
        try:
            contenido = ruta.read_text(encoding="utf-8").splitlines()
            info["lineas"] = len(contenido)
            info["primera_linea"] = contenido[0] if contenido else ""
        except UnicodeDecodeError:
            info["lineas"] = None
            info["primera_linea"] = ""
    else:
        info["lineas"] = None
        info["primera_linea"] = ""

    return info


def analizar_directorio(directorio: Path) -> Iterable[Dict[str, Any]]:
    """Analiza todos los archivos del directorio."""
    for ruta in sorted(directorio.iterdir()):
        if ruta.is_file():
            yield describir_archivo(ruta)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analiza y describe los archivos en una carpeta"
    )
    parser.add_argument(
        "directorio",
        nargs="?",
        default=".",
        help="Ruta de la carpeta a analizar (por defecto, la carpeta actual)",
    )
    args = parser.parse_args()

    dir_path = Path(args.directorio)
    if not dir_path.is_dir():
        raise SystemExit(f"La ruta {dir_path} no es un directorio v\u00e1lido")

    resultados = list(analizar_directorio(dir_path))
    for info in resultados:
        print(
            f"{info['nombre']}: {info['tamanio']} bytes, tipo {info['tipo']}"
        )
        if info["lineas"] is not None:
            primera = info["primera_linea"].strip()
            print(
                f"  {info['lineas']} l\u00edneas. Primera l\u00ednea: {primera}"
            )
    print(f"Total de archivos: {len(resultados)}")


if __name__ == "__main__":
    main()
