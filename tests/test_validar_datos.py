"""Pruebas del validador propio y del contrato. Solo usan la biblioteca estándar (y pytest para correr)."""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)  # permite importar src/ sin instalar nada

from src.validar_datos import (  # noqa: E402
    cargar_contrato,
    cargar_csv,
    validar_registro,
    verificar_ejemplos_contrato,
)

CONTRATO = cargar_contrato(os.path.join(RAIZ, "contrato", "contrato_datos.json"))
CAMPO_LARGO_PETALO = "petal length (cm)"
CAMPO_ANCHO_PETALO = "petal width (cm)"


def pares_de_error(registro, con_objetivo=False):
    """Devuelve {(campo, tipo_error)} para comparar fácilmente."""
    return {(e["campo"], e["tipo_error"]) for e in validar_registro(registro, CONTRATO, con_objetivo)}


def registro_valido():
    registro = dict(CONTRATO["ejemplo_entrada_valida"])
    registro["species"] = 0
    return registro


def test_los_ejemplos_del_contrato_son_coherentes():
    assert verificar_ejemplos_contrato(CONTRATO) == []


def test_registro_valido_pasa():
    assert pares_de_error(registro_valido(), con_objetivo=True) == set()


def test_detecta_tipo_incorrecto():
    registro = registro_valido()
    registro["sepal length (cm)"] = "5.1"  # texto donde se espera número
    assert ("sepal length (cm)", "tipo") in pares_de_error(registro, con_objetivo=True)


def test_un_booleano_no_es_un_numero():
    registro = registro_valido()
    registro[CAMPO_ANCHO_PETALO] = True
    assert (CAMPO_ANCHO_PETALO, "tipo") in pares_de_error(registro, con_objetivo=True)


def test_detecta_nulos_y_textos_vacios():
    registro = registro_valido()
    registro["sepal width (cm)"] = None
    assert ("sepal width (cm)", "nulo") in pares_de_error(registro, con_objetivo=True)
    registro["sepal width (cm)"] = "   "
    assert ("sepal width (cm)", "nulo") in pares_de_error(registro, con_objetivo=True)


def test_detecta_fuera_de_rango():
    registro = registro_valido()
    registro[CAMPO_LARGO_PETALO] = 12.5
    assert (CAMPO_LARGO_PETALO, "rango") in pares_de_error(registro, con_objetivo=True)


def test_detecta_especie_no_permitida():
    registro = registro_valido()
    registro["species"] = 7  # solo se permiten 0, 1 y 2
    assert ("species", "rango") in pares_de_error(registro, con_objetivo=True)


def test_detecta_columna_faltante():
    registro = registro_valido()
    del registro[CAMPO_ANCHO_PETALO]
    assert (CAMPO_ANCHO_PETALO, "faltante") in pares_de_error(registro, con_objetivo=True)


def test_detecta_regla_cruzada():
    registro = registro_valido()
    registro[CAMPO_LARGO_PETALO] = 0.5
    registro[CAMPO_ANCHO_PETALO] = 0.6  # el pétalo queda más ancho que largo
    assert (CAMPO_LARGO_PETALO, "regla_cruzada") in pares_de_error(registro, con_objetivo=True)


def test_carga_csv_convierte_tipos_y_marca_nulos():
    contenido = (
        "sepal length (cm),sepal width (cm),petal length (cm),petal width (cm),species\n"
        "5.1,3.5,1.4,0.2,0\n"
        "cinco,3.0,1.4,0.2,0\n"
        ",3.0,1.4,0.2,0\n"
    )
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = os.path.join(carpeta, "prueba.csv")
        with open(ruta, "w", encoding="utf-8", newline="") as f:
            f.write(contenido)
        filas = cargar_csv(ruta, CONTRATO, con_objetivo=True)

    assert isinstance(filas[0]["sepal length (cm)"], float)
    assert isinstance(filas[0]["species"], int)
    assert pares_de_error(filas[1], con_objetivo=True) == {("sepal length (cm)", "tipo")}
    assert pares_de_error(filas[2], con_objetivo=True) == {("sepal length (cm)", "nulo")}
