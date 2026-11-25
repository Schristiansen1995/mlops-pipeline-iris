"""Etapa 'prepare' del pipeline (dvc.yaml): carga Iris, separa train/test 80/20 y guarda dos CSV."""
import os

import pandas as pd
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split

# Cargar datos de Iris
iris = load_iris()
data = pd.DataFrame(data=iris.data, columns=iris.feature_names)
data['species'] = iris.target  # 0 = setosa, 1 = versicolor, 2 = virginica

# Dividir en train/test (80/20, semilla 42)
train, test = train_test_split(data, test_size=0.2, random_state=42)

# Guardar sin índice
os.makedirs('data/processed', exist_ok=True)
train.to_csv('data/processed/train.csv', index=False)
test.to_csv('data/processed/test.csv', index=False)

print(f"Train: {len(train)} filas. Test: {len(test)} filas.")
