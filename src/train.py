"""Etapa 'train' del pipeline (dvc.yaml): valida los datos, entrena el Random Forest con MLflow y guarda el modelo.

Antes de entrenar, los datos pasan dos controles de calidad:
  1) el validador propio, sin librerías externas, contra contrato/contrato_datos.json;
  2) Great Expectations (src/validacion_ge.py).
Si cualquiera de los dos falla, el entrenamiento no arranca.
"""
import os
import sys

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)  # permite importar src/ aunque se ejecute como script: python src/train.py

from src.validacion_ge import validar_train  # noqa: E402
from src.validar_datos import cargar_contrato, cargar_csv, validar_filas  # noqa: E402

RUTA_CONTRATO = os.path.join(RAIZ, 'contrato', 'contrato_datos.json')


def main():
    # 1) Validación propia contra el contrato (sin librerías externas), en train y en test
    contrato = cargar_contrato(RUTA_CONTRATO)
    for ruta in ('data/processed/train.csv', 'data/processed/test.csv'):
        filas = cargar_csv(ruta, contrato, con_objetivo=True)
        errores = validar_filas(filas, contrato, con_objetivo=True)
        if errores:
            raise SystemExit(f"Validación de contrato fallida en {ruta}: {len(errores)} fila(s) con errores. "
                             "Corre `make validar` para ver el detalle.")
        print(f"Validador propio: {ruta} cumple el contrato.")

    # 2) Validación con Great Expectations
    validar_train('data/processed/train.csv')

    # 3) Entrenamiento con MLflow
    mlflow.set_experiment("Proyecto_Final_Grado")
    with mlflow.start_run() as run:
        n_estimators = 100
        mlflow.log_param("n_estimators", n_estimators)

        train = pd.read_csv('data/processed/train.csv')
        X_train = train.drop('species', axis=1)
        y_train = train['species']

        model = RandomForestClassifier(n_estimators=n_estimators, random_state=42)
        model.fit(X_train, y_train)

        test = pd.read_csv('data/processed/test.csv')
        X_test = test.drop('species', axis=1)
        y_test = test['species']
        accuracy = model.score(X_test, y_test)

        mlflow.log_metric("accuracy", accuracy)
        # Confiamos en los tipos del modelo porque lo entrenamos aquí mismo (requisito de MLflow 3 con scikit-learn).
        mlflow.sklearn.log_model(
            model,
            name="iris_model",
            skops_trusted_types=["sklearn.tree._tree.Tree"],
        )

        # Guardar el modelo localmente para el pipeline de DVC
        os.makedirs('models', exist_ok=True)
        joblib.dump(model, 'models/model.pkl')

        print(f"Run ID: {run.info.run_id}")
        print(f"Modelo entrenado con accuracy: {accuracy}")


if __name__ == '__main__':
    main()
