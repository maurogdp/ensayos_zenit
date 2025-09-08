# Ensayos Zenit

Este repositorio contiene scripts de apoyo para el análisis de resultados
de cuestionarios.

## `procesar_respuestas.py`

Este script lee el archivo `quiz-M1 1 Moraleja 2025-full.csv` y genera
los siguientes resúmenes:

* `resumen_estudiantes.csv`: cantidad de respuestas correctas e
  incorrectas por estudiante. Solo se consideran las preguntas con
  puntaje (`PointsN` > 0).
* `dificultad_preguntas.csv`: índice de dificultad de cada pregunta
  calculado como `respuestas_correctas / total_estudiantes`.

Las preguntas con puntaje cero se excluyen del conteo de respuestas
correctas/incorrectas de los estudiantes, pero se evalúan igualmente al
calcular el índice de dificultad.

### Uso

```bash
python procesar_respuestas.py
```

Los archivos de salida se generan en la raíz del repositorio.
