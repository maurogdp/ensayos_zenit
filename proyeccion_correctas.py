#!/usr/bin/env python3
"""Estima preguntas correctas para ensayos no rendidos.

Calcula el porcentaje promedio de aciertos por estudiante y lo aplica a
los exámenes que aún no ha rendido para proyectar la cantidad de
respuestas correctas. El resultado se guarda en
``proyeccion_preguntas_correctas.csv``.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Set

INPUT_DIR = Path("csv_ensayos")
OUTPUT_FILE = Path("proyeccion_preguntas_correctas.csv")


def _to_float(valor: str | None) -> float:
    try:
        return float(valor or 0)
    except ValueError:
        return 0.0


def leer_rendimientos() -> tuple[dict[str, dict[str, object]], Dict[str, int]]:
    estudiantes: dict[str, dict[str, object]] = {}
    preguntas_por_examen: Dict[str, int] = {}

    for ruta in sorted(INPUT_DIR.glob("*.csv")):
        with ruta.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            filas = list(reader)
        if not filas:
            continue

        examen = filas[0].get("QuizName") or ruta.stem
        preguntas = sum(
            1
            for clave, valor in filas[0].items()
            if clave.startswith("Points") and _to_float(valor) > 0
        )
        preguntas_por_examen[examen] = preguntas

        for fila in filas:
            sid = fila.get("StudentID", "").strip()
            nombre = fila.get("FirstName", "").strip()
            apellido = fila.get("LastName", "").strip()
            earned = _to_float(fila.get("Earned Points", ""))
            possible = _to_float(fila.get("Possible Points", ""))
            porcentaje = earned / possible if possible else 0.0

            info = estudiantes.setdefault(
                sid,
                {
                    "FirstName": nombre,
                    "LastName": apellido,
                    "percentages": [],
                    "exams": set(),
                },
            )
            info["FirstName"] = info.get("FirstName") or nombre
            info["LastName"] = info.get("LastName") or apellido
            porcentajes: list[float] = info["percentages"]  # type: ignore[assignment]
            porcentajes.append(porcentaje)
            examenes: Set[str] = info["exams"]  # type: ignore[assignment]
            examenes.add(examen)

    return estudiantes, preguntas_por_examen


def proyectar(
    estudiantes: dict[str, dict[str, object]], preguntas_por_examen: Dict[str, int]
) -> list[dict[str, object]]:
    filas: list[dict[str, object]] = []
    for sid, info in estudiantes.items():
        nombre = info["FirstName"]
        apellido = info["LastName"]
        porcentajes: list[float] = info["percentages"]  # type: ignore[assignment]
        examenes: Set[str] = info["exams"]  # type: ignore[assignment]
        promedio = sum(porcentajes) / len(porcentajes) if porcentajes else 0.0
        for examen, preguntas in preguntas_por_examen.items():
            if examen not in examenes:
                proyectado = round(promedio * preguntas, 2)
                filas.append(
                    {
                        "StudentID": sid,
                        "FirstName": nombre,
                        "LastName": apellido,
                        "Exam": examen,
                        "ProjectedCorrect": proyectado,
                    }
                )
    return filas


def escribir_csv(filas: list[dict[str, object]]) -> None:
    campos = ["StudentID", "FirstName", "LastName", "Exam", "ProjectedCorrect"]
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(filas)


def main() -> None:
    estudiantes, preguntas_por_examen = leer_rendimientos()
    filas = proyectar(estudiantes, preguntas_por_examen)
    escribir_csv(filas)


if __name__ == "__main__":
    main()
