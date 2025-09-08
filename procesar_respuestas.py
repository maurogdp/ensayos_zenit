#!/usr/bin/env python3
"""Procesa los resultados de un quiz y genera resúmenes.

Lee el archivo ``quiz-M1 1 Moraleja 2025-full.csv`` y produce dos
archivos CSV:

* ``resumen_estudiantes.csv`` con la cantidad de respuestas correctas
  e incorrectas por estudiante (solo se contabilizan las preguntas con
  puntaje asignado).
* ``dificultad_preguntas.csv`` con el índice de dificultad de cada
  pregunta calculado como ``respuestas_correctas / total_estudiantes``.

Las preguntas con ``PointsN`` igual a cero no se consideran para las
estadísticas de cada estudiante, pero sí se evalúan para el cálculo del
índice de dificultad.
"""
from __future__ import annotations

import csv
from pathlib import Path

INPUT_FILE = Path('quiz-M1 1 Moraleja 2025-full.csv')
OUTPUT_STUDENTS = Path('resumen_estudiantes.csv')
OUTPUT_DIFFICULTY = Path('dificultad_preguntas.csv')
MAX_QUESTIONS = 65


def leer_datos() -> list[dict[str, str]]:
    """Lee el CSV de origen y devuelve una lista de filas."""
    with INPUT_FILE.open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        return list(reader)


def procesar_estudiantes(filas: list[dict[str, str]]) -> list[dict[str, int]]:
    """Genera el resumen de respuestas correctas e incorrectas."""
    resultados: list[dict[str, int]] = []
    for fila in filas:
        correctas = 0
        incorrectas = 0
        for n in range(1, MAX_QUESTIONS + 1):
            stu = fila.get(f'Stu{n}', '').strip()
            pri = fila.get(f'PriKey{n}', '').strip()
            try:
                puntos = float(fila.get(f'Points{n}', '0') or 0)
            except ValueError:
                puntos = 0.0

            if stu == pri:
                if puntos > 0:
                    correctas += 1
            else:
                if puntos > 0:
                    incorrectas += 1
        resultados.append({
            'FirstName': fila.get('FirstName', ''),
            'LastName': fila.get('LastName', ''),
            'correctas': correctas,
            'incorrectas': incorrectas,
        })
    return resultados


def calcular_dificultad(filas: list[dict[str, str]]) -> list[dict[str, float]]:
    """Calcula el índice de dificultad para cada pregunta."""
    total_estudiantes = len(filas)
    correctas_por_pregunta = {n: 0 for n in range(1, MAX_QUESTIONS + 1)}

    for fila in filas:
        for n in range(1, MAX_QUESTIONS + 1):
            stu = fila.get(f'Stu{n}', '').strip()
            pri = fila.get(f'PriKey{n}', '').strip()
            if stu == pri and pri != '':
                correctas_por_pregunta[n] += 1

    dificultades = []
    for n in range(1, MAX_QUESTIONS + 1):
        indice = (
            correctas_por_pregunta[n] / total_estudiantes
            if total_estudiantes else 0.0
        )
        dificultades.append({
            'pregunta': f'Stu{n}',
            'indice_dificultad': round(indice, 4),
        })
    return dificultades


def escribir_csv(ruta: Path, filas: list[dict[str, object]], campos: list[str]) -> None:
    """Escribe un archivo CSV en la ruta indicada."""
    with ruta.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(filas)


def main() -> None:
    filas = leer_datos()
    resumen = procesar_estudiantes(filas)
    dificultad = calcular_dificultad(filas)

    escribir_csv(OUTPUT_STUDENTS, resumen, ['FirstName', 'LastName', 'correctas', 'incorrectas'])
    escribir_csv(OUTPUT_DIFFICULTY, dificultad, ['pregunta', 'indice_dificultad'])


if __name__ == '__main__':
    main()
