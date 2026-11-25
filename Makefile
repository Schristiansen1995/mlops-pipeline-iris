# ============================================================================
#  Pipeline MLOps - Semana 2 (Pipelines y Calidad)
#
#  make            entorno + pipeline completo (dvc repro: prepare -> train -> test)
#  make validar    validador propio sobre train.csv y test.csv
#  make pruebas    pytest con salida detallada
#  make limpiar    borra datos, modelo y registros de MLflow (conserva .venv)
#  make ayuda      lista todos los comandos
#
#  Requisitos: GNU Make y Python 3.13 (versión probada). Git es recomendado.
# ============================================================================

PYTHON ?= python3
VENV   := .venv
PY     := $(VENV)/bin/python
DVC    := $(VENV)/bin/dvc
PYTEST := $(VENV)/bin/pytest

# Las herramientas usan el intérprete del entorno virtual, no el del sistema
export PATH := $(CURDIR)/$(VENV)/bin:$(PATH)
# MLflow no envía telemetría durante el pipeline
export MLFLOW_DISABLE_TELEMETRY := true

.DEFAULT_GOAL := all
.NOTPARALLEL:
.PHONY: all entorno dvc-listo pipeline validar pruebas limpiar limpiar-entorno ayuda

all: pipeline
	@echo ""
	@echo "Pipeline completo. Modelo en models/model.pkl."
	@echo "Para ver las corridas de MLflow: $(PY) -m mlflow ui"

# 1) Entorno virtual con las dependencias fijadas en requirements.txt
entorno: $(VENV)/.instalado

$(VENV)/.instalado: requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install -r requirements.txt
	touch $@

# 2) DVC necesita un repositorio inicializado. Con Git se integra con él;
#    sin Git (carpeta descomprimida de un ZIP) se inicia en modo --no-scm.
dvc-listo: entorno
	@test -d .dvc || $(DVC) init -q $(if $(wildcard .git),,--no-scm)

# 3) Pipeline de DVC (dvc.yaml): prepare -> train (validaciones y MLflow) -> test
pipeline: dvc-listo
	$(DVC) repro

# 4) Validador propio (sin librerías externas) sobre los CSV procesados
validar: dvc-listo
	$(DVC) repro prepare
	$(PY) -m src.validar_datos --datos data/processed/train.csv --contrato contrato/contrato_datos.json --con-objetivo
	$(PY) -m src.validar_datos --datos data/processed/test.csv --contrato contrato/contrato_datos.json --con-objetivo

# 5) Pruebas con pytest (si faltan datos o modelo, corre el pipeline antes)
pruebas: pipeline
	$(PYTEST) tests/ -v

limpiar:
	rm -rf data/processed models mlruns mlartifacts mlflow.db .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

limpiar-entorno: limpiar
	rm -rf $(VENV)

ayuda:
	@echo "make                  pipeline completo (entorno + dvc repro)"
	@echo "make validar          validador propio sobre train.csv y test.csv"
	@echo "make pruebas          pytest (corre el pipeline antes si hace falta)"
	@echo "make limpiar          borra datos, modelo y registros de MLflow (conserva .venv)"
	@echo "make limpiar-entorno  borra también .venv"
	@echo "Ver corridas de MLflow: $(PY) -m mlflow ui   (y abre http://127.0.0.1:5000)"
