#!/usr/bin/env python3
"""Genera un resumen de rendiciones y puntajes por estudiante.

Recorre todos los archivos CSV en ``csv_ensayos/`` y produce un archivo
``resumen_rendiciones.csv`` con las columnas ``StudentID,FirstName,LastName,Exam,Status,Score``.
Si un estudiante no ha rendido un examen se marca como ``NR`` y el
puntaje queda vacío.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Set

INPUT_DIR = Path("csv_ensayos")
OUTPUT_FILE = Path("resumen_rendiciones.csv")


def reunir_datos() -> tuple[dict[str, dict[str, object]], Set[str]]:
    """Lee todos los CSV y consolida la información."""
    estudiantes: dict[str, dict[str, object]] = {}
    examenes: Set[str] = set()

    for ruta in sorted(INPUT_DIR.glob("*.csv")):
        with ruta.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for fila in reader:
                examen = fila.get("QuizName") or ruta.stem
                examenes.add(examen)
                sid = fila.get("StudentID", "").strip()
                nombre = fila.get("FirstName", "").strip()
                apellido = fila.get("LastName", "").strip()
                try:
                    puntaje = float(fila.get("Earned Points", "") or 0)
                except ValueError:
                    puntaje = 0.0

                info = estudiantes.setdefault(
                    sid, {"FirstName": nombre, "LastName": apellido, "scores": {}}
                )
                info["FirstName"] = info.get("FirstName") or nombre
                info["LastName"] = info.get("LastName") or apellido
                scores: Dict[str, float] = info["scores"]  # type: ignore[assignment]
                scores[examen] = puntaje
    return estudiantes, examenes


def generar_resumen(
    estudiantes: dict[str, dict[str, object]], examenes: Set[str]
) -> list[dict[str, object]]:
    """Crea las filas para el CSV de salida."""
    filas: list[dict[str, object]] = []
    for sid, info in estudiantes.items():
        nombre = info["FirstName"]
        apellido = info["LastName"]
        scores: Dict[str, float] = info["scores"]  # type: ignore[assignment]
        for examen in sorted(examenes):
            if examen in scores:
                filas.append(
                    {
                        "StudentID": sid,
                        "FirstName": nombre,
                        "LastName": apellido,
                        "Exam": examen,
                        "Status": "R",
                        "Score": scores[examen],
                    }
                )
            else:
                filas.append(
                    {
                        "StudentID": sid,
                        "FirstName": nombre,
                        "LastName": apellido,
                        "Exam": examen,
                        "Status": "NR",
                        "Score": "",
                    }
                )
    return filas


def escribir_csv(filas: list[dict[str, object]]) -> None:
    campos = ["StudentID", "FirstName", "LastName", "Exam", "Status", "Score"]
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(filas)


def main() -> None:
    estudiantes, examenes = reunir_datos()
    resumen = generar_resumen(estudiantes, examenes)
    escribir_csv(resumen)


if __name__ == "__main__":
    main()
