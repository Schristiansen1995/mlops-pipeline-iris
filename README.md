# Pipeline MLOps: estandarización y control de calidad de datos

Proyecto de la **Semana 2 (Pipelines y Calidad)** del Seminario de Grado II. Entrena un Random Forest con el dataset Iris y revisa la calidad de los datos antes de entrenar: si algo no cumple el contrato, el pipeline se detiene.

**Autor:** Santiago Christiansen García (Universidad Santo Tomás, sede Tunja)

## Qué hace el pipeline

| Etapa (`dvc.yaml`) | Qué hace |
|---|---|
| `prepare` | Carga Iris (150 filas), separa 80 % para entrenamiento y 20 % para prueba (semilla 42) y guarda `data/processed/train.csv` y `data/processed/test.csv`. |
| `train` | Valida los dos CSV con el validador propio y con Great Expectations. Si todo cumple, entrena un `RandomForestClassifier` y registra la corrida en MLflow. |
| `test` | Corre pytest: revisa los datos, que el modelo exista y que su exactitud en prueba sea mayor que 0.8. |

## Estructura

```
.
├── Makefile                   # comando único: make
├── dvc.yaml                   # etapas del pipeline
├── dvc.lock                   # estado del pipeline (lo genera DVC)
├── requirements.txt           # dependencias con versiones fijadas
├── contrato/
│   └── contrato_datos.json    # contrato de datos: campos, reglas y ejemplos
├── src/
│   ├── prepare.py             # etapa prepare
│   ├── train.py               # etapa train: validaciones, entrenamiento y MLflow
│   ├── validar_datos.py       # validador propio (solo biblioteca estándar)
│   └── validacion_ge.py       # expectativas de Great Expectations
└── tests/
    ├── test_model.py          # pruebas del modelo
    └── test_validar_datos.py  # pruebas del validador y del contrato
```

Al correr el pipeline se generan `.venv/`, `data/processed/`, `models/`, `mlruns/` y `mlflow.db`. Están en `.gitignore` y no se suben al repositorio. El directorio `.dvc/` guarda la configuración de DVC y sí se versiona.

## Requisitos

- **GNU Make.** Viene en Linux; en macOS sale con las herramientas de línea de comandos de Xcode; en Windows usa WSL.
- **Python 3.13** (versión con la que se probó: 3.13.18).
- **Git** (recomendado: DVC se integra con Git).

## Reproducir desde cero

```bash
git clone https://github.com/Schristiansen1995/mlops-pipeline-iris.git
cd mlops-pipeline-iris
make
```

`make` crea el entorno virtual `.venv`, instala las versiones fijadas en `requirements.txt` y corre el pipeline completo. Si descargaste el proyecto como ZIP, ejecuta `git init -b main` antes de `make` para que DVC quede integrado con Git.

## Comandos

| Comando | Qué hace |
|---|---|
| `make` | Pipeline completo: `prepare` → `train` → `test` |
| `make validar` | Solo el validador propio sobre `train.csv` y `test.csv` |
| `make pruebas` | Pytest con salida detallada (corre el pipeline si hace falta) |
| `make limpiar` | Borra datos, modelo y registros de MLflow; conserva `.venv` |
| `make limpiar-entorno` | Borra también `.venv` |
| `make ayuda` | Lista los comandos |

## Contrato de datos

`contrato/contrato_datos.json` (versión 2.0.0) define lo que debe cumplir cada fila:

| Campo | Tipo | Rango permitido | Nulos |
|---|---|---|---|
| `sepal length (cm)` | decimal | 4.0 a 8.0 | no |
| `sepal width (cm)` | decimal | 1.0 a 6.0 | no |
| `petal length (cm)` | decimal | 0.5 a 8.0 | no |
| `petal width (cm)` | decimal | 0.05 a 3.0 | no |
| `species` (objetivo) | entero | 0, 1 o 2 | no |

- **Regla cruzada:** `petal length (cm) > petal width (cm)`.
- **Objetivo:** `species` es la variable que se predice (0 = setosa, 1 = versicolor, 2 = virginica). No forma parte de la entrada de inferencia.

Ejemplo válido:

```json
{"sepal length (cm)": 5.1, "sepal width (cm)": 3.5, "petal length (cm)": 1.4, "petal width (cm)": 0.2}
```

Ejemplo inválido: produce `tipo` en `sepal length (cm)`, `nulo` en `sepal width (cm)` y `rango` en `petal length (cm)`.

```json
{"sepal length (cm)": "cinco", "sepal width (cm)": null, "petal length (cm)": 12.5, "petal width (cm)": 0.2}
```

## Validación de datos

`src/validar_datos.py` usa solo la biblioteca estándar de Python (`csv`, `json`, `math`, `argparse` y `sys`). Reporta cinco tipos de error:

| Tipo | Significado |
|---|---|
| `faltante` | La columna que pide el contrato no existe |
| `nulo` | Valor vacío (`""`, `na`, `nan`, `null`, `none`) donde el contrato no lo permite |
| `tipo` | El valor no es del tipo declarado. Un booleano no cuenta como número |
| `rango` | Número fuera de `[mínimo, máximo]`, o texto fuera de los valores permitidos |
| `regla_cruzada` | Dos campos se contradicen, por ejemplo un pétalo más ancho que largo |

Si hay errores, el validador muestra la fila, el campo y el motivo, y termina con un código distinto de cero. Así se ve la salida con un `train.csv` alterado a mano:

```text
FALLA: 2 error(es) en 2 de 120 filas.
  fila    3 | rango          | sepal length (cm): 9.9 fuera del rango [4.0, 8.0]
  fila    6 | nulo           | species: valor vacío y el contrato no permite nulos
```

Si el archivo cumple, el validador imprime `OK: 120 filas cumplen el contrato (tipos, nulos, rangos y reglas cruzadas).` Si `train.py` encuentra errores en `train.csv` o `test.csv`, no entrena.

## Control de calidad con Great Expectations

`src/validacion_ge.py` revisa `train.csv` con cuatro expectativas:

1. Existe la columna `sepal length (cm)`.
2. Sus valores están entre 4.0 y 8.0.
3. `species` no tiene nulos.
4. Los valores de `species` pertenecen a `{0, 1, 2}`.

Si alguna falla, el pipeline se detiene y muestra qué expectativa no se cumplió.

## Modelo y resultados de referencia

- **Datos:** Iris, 150 filas, 4 variables numéricas y 3 especies.
- **Separación:** 120 filas para entrenamiento y 30 para prueba (80/20, `random_state=42`).
- **Modelo:** `RandomForestClassifier(n_estimators=100, random_state=42)`.
- **Resultado de referencia:** exactitud de 1.0 en las 30 filas de prueba.
- **MLflow:** las corridas van al experimento `Proyecto_Final_Grado`. Guarda el Run ID que imprime `train.py`; lo necesitará la Semana 3.

Para ver las corridas en el navegador:

```bash
.venv/bin/python -m mlflow ui   # luego abre http://127.0.0.1:5000
```

## Pruebas

`make pruebas` corre 13 pruebas con pytest:

- `tests/test_model.py` (3): los CSV cargan y tienen la columna `species`, el modelo existe y su exactitud es mayor que 0.8.
- `tests/test_validar_datos.py` (10): el contrato es coherente, un registro válido pasa, y cada tipo de error se detecta en su caso.

## Solución de problemas

- **`make: command not found`**: instala GNU Make.
- **Tu `python3` no es 3.13**: `make PYTHON=python3.13`.
- **`FALLA` del validador o `Validación de datos fallida`**: los datos no cumplen el contrato. Revisa la fila y el campo que indica el mensaje.
- **Quieres reinstalar todo**: `make limpiar-entorno && make`.

## Entorno de referencia

Probado en Linux con Python 3.13.18: mlflow 3.18.0, scikit-learn 1.9.1, pandas 3.1.1, dvc 3.67.1, great-expectations 1.25.0, pytest 9.2.0 y joblib 1.6.0.

## Referencias

- Fisher, R. A. (1936). The use of multiple measurements in taxonomic problems. *Annals of Eugenics, 7*(2), 179–188. https://doi.org/10.1111/j.1469-1809.1936.tb02137.x
- Great Expectations. (s. f.). *Great Expectations documentation*. https://docs.greatexpectations.io/
- Guía técnica para el Seminario de Grado II. (s. f.). MLOps course Santoto. https://dialvebe.github.io/mlops-course-santoto/
- Iterative. (s. f.). *DVC documentation*. https://dvc.org/doc
- MLflow. (s. f.). *MLflow documentation*. https://mlflow.org/docs/latest/
- Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M. y Duchesnay, É. (2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research, 12*, 2825–2830.
- pytest-dev team. (s. f.). *pytest documentation*. https://docs.pytest.org/
