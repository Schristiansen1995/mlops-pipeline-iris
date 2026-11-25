"""Validación de calidad con Great Expectations sobre data/processed/train.csv.

Usa la API actual de Great Expectations (1.x). La guía del curso muestra la API antigua
(ge.from_pandas), que ya no existe en las versiones nuevas; las expectativas son las mismas.
"""
import great_expectations as gx
import pandas as pd


def validar_train(ruta='data/processed/train.csv'):
    df = pd.read_csv(ruta)

    contexto = gx.get_context(mode="ephemeral")
    fuente = contexto.data_sources.add_pandas("fuente_train")
    activo = fuente.add_dataframe_asset("train")
    definicion = activo.add_batch_definition_whole_dataframe("lote_completo")
    lote = definicion.get_batch(batch_parameters={"dataframe": df})

    suite = contexto.suites.add(gx.ExpectationSuite(name="suite_train_iris"))
    suite.add_expectation(gx.expectations.ExpectColumnToExist(column="sepal length (cm)"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(
        column="sepal length (cm)", min_value=4.0, max_value=8.0))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="species"))
    suite.add_expectation(gx.expectations.ExpectColumnDistinctValuesToBeInSet(
        column="species", value_set=[0, 1, 2]))

    resultado = lote.validate(suite)
    if not resultado.success:
        for r in resultado.results:
            if not r.success:
                print(f"Expectativa fallida: {r.expectation_config.type} {r.expectation_config.kwargs}")
    assert resultado.success, "Validación de datos fallida"
    print("Great Expectations: todas las validaciones de train.csv pasaron.")
    return resultado
