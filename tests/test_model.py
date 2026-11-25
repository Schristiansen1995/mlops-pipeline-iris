"""Pruebas del modelo entrenado (etapa 'test' de dvc.yaml)."""
import joblib
import pandas as pd
from sklearn.metrics import accuracy_score


def test_data_loading():
    train = pd.read_csv('data/processed/train.csv')
    test = pd.read_csv('data/processed/test.csv')
    assert not train.empty and not test.empty
    assert 'species' in train.columns


def test_model_exists():
    model = joblib.load('models/model.pkl')
    assert model is not None


def test_model_accuracy():
    model = joblib.load('models/model.pkl')
    test = pd.read_csv('data/processed/test.csv')
    X_test = test.drop('species', axis=1)
    y_test = test['species']
    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    assert accuracy > 0.8
