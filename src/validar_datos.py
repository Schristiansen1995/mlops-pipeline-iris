"""
Validación de datos de entrada contra el Contrato de Datos.

Usa SOLO la biblioteca estándar de Python (csv, json, math, argparse).
No necesita pandas, numpy ni ninguna otra librería externa.

Tipos de error que reporta:
  faltante       la columna que exige el contrato no existe en el registro
  nulo           el valor está vacío (None o texto en blanco) y el contrato no lo permite
  tipo           el valor no es del tipo declarado (por ejemplo, texto donde se espera número)
  rango          el número está fuera de [minimo, maximo], o el texto no está en valores_permitidos
  regla_cruzada  dos campos se contradicen entre sí (por ejemplo, un pétalo más ancho que largo)

Uso:
  python -m src.validar_datos --datos data/processed/train.csv --con-objetivo
"""
import argparse
import csv
import json
import math
import sys

# Textos que se consideran nulos cuando vienen de un CSV o de un JSON.
TEXTOS_NULOS = {"", "na", "nan", "null", "none"}

# Cada regla cruzada del contrato se identifica por un id. Aquí vive la lógica de cada una.
# Cada función devuelve True si el registro cumple la regla.
FUNCIONES_REGLAS = {
    "petalo_mas_largo_que_ancho": lambda r: r["petal length (cm)"] > r["petal width (cm)"],
}


def cargar_contrato(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def _es_nulo(valor):
    if valor is None:
        return True
    return isinstance(valor, str) and valor.strip().lower() in TEXTOS_NULOS


def _tipo_correcto(valor, tipo):
    # OJO: en Python, bool es subclase de int. Para el contrato, True NO es un número.
    if isinstance(valor, bool):
        return False
    if tipo == "entero":
        return isinstance(valor, int)
    if tipo == "decimal":
        return isinstance(valor, (int, float)) and math.isfinite(valor)
    if tipo == "texto":
        return isinstance(valor, str)
    raise ValueError(f"Tipo no soportado en el contrato: {tipo!r}")


def _error(campo, tipo_error, mensaje):
    return {"campo": campo, "tipo_error": tipo_error, "mensaje": mensaje}


def validar_registro(registro, contrato, con_objetivo=False):
    """Revisa UN registro (dict). Devuelve la lista de errores; lista vacía = registro válido."""
    campos = list(contrato["campos"])
    if con_objetivo:
        campos.append(contrato["objetivo"])

    errores = []
    for campo in campos:
        nombre = campo["nombre"]

        if nombre not in registro:
            errores.append(_error(nombre, "faltante", "la columna no existe en el registro"))
            continue

        valor = registro[nombre]
        if _es_nulo(valor):
            if not campo.get("nulo_permitido", False):
                errores.append(_error(nombre, "nulo", "valor vacío y el contrato no permite nulos"))
            continue

        if not _tipo_correcto(valor, campo["tipo"]):
            errores.append(_error(nombre, "tipo", f"se esperaba {campo['tipo']}, llegó {valor!r}"))
            continue

        if "valores_permitidos" in campo and valor not in campo["valores_permitidos"]:
            errores.append(_error(nombre, "rango", f"{valor!r} no está en {campo['valores_permitidos']}"))
            continue

        minimo, maximo = campo.get("minimo"), campo.get("maximo")
        if (minimo is not None and valor < minimo) or (maximo is not None and valor > maximo):
            errores.append(_error(nombre, "rango", f"{valor} fuera del rango [{minimo}, {maximo}]"))

    # Reglas cruzadas: solo se evalúan si ninguno de sus campos tiene ya un error.
    campos_con_error = {e["campo"] for e in errores}
    for regla in contrato.get("reglas_cruzadas", []):
        involucrados = regla["campos"]
        if any(c in campos_con_error or c not in registro for c in involucrados):
            continue
        if not FUNCIONES_REGLAS[regla["id"]](registro):
            errores.append(_error(involucrados[0], "regla_cruzada", regla["descripcion"]))
    return errores


def validar_filas(filas, contrato, con_objetivo=False):
    """Valida una lista de registros. Devuelve [(numero_de_fila, errores), ...] solo de las filas con problemas.
    El número de fila es el de la hoja de cálculo: la fila 1 es el encabezado."""
    reporte = []
    for numero, fila in enumerate(filas, start=2):
        errores = validar_registro(fila, contrato, con_objetivo)
        if errores:
            reporte.append((numero, errores))
    return reporte


def _convertir(celda, tipo):
    if celda is None or _es_nulo(celda):
        return None
    texto = celda.strip()
    if tipo is None or tipo == "texto":
        return texto
    try:
        if tipo == "entero":
            return int(texto)
        if tipo == "decimal":
            return float(texto)
    except ValueError:
        pass
    return celda  # no se pudo convertir: se queda como texto y la validación lo reporta como tipo


def cargar_csv(ruta, contrato, con_objetivo=False):
    """Lee un CSV y convierte cada celda al tipo que pide el contrato.
    Una celda que no se puede convertir (por ejemplo 'cinco' en un decimal) se deja como texto
    para que validar_registro la marque como error de tipo. Las celdas vacías pasan a None."""
    tipos = {c["nombre"]: c["tipo"] for c in contrato["campos"]}
    if con_objetivo:
        tipos[contrato["objetivo"]["nombre"]] = contrato["objetivo"]["tipo"]

    filas = []
    with open(ruta, newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            limpia = {}
            for columna, celda in fila.items():
                if columna is None:  # celdas de más en una fila; el contrato no las usa
                    continue
                limpia[columna] = _convertir(celda, tipos.get(columna))
            filas.append(limpia)
    return filas


def verificar_ejemplos_contrato(contrato):
    """Comprueba que el contrato sea coherente consigo mismo: el ejemplo válido debe pasar
    y el ejemplo inválido debe producir EXACTAMENTE los errores que el contrato declara."""
    problemas = []
    if validar_registro(contrato["ejemplo_entrada_valida"], contrato):
        problemas.append("el ejemplo de entrada válida tiene errores")

    obtenidos = {(e["campo"], e["tipo_error"])
                 for e in validar_registro(contrato["ejemplo_entrada_invalida"], contrato)}
    esperados = {(e["campo"], e["tipo_error"]) for e in contrato["errores_esperados_ejemplo_invalido"]}
    if obtenidos != esperados:
        problemas.append(
            f"errores del ejemplo inválido: se esperaban {sorted(esperados)} "
            f"y salieron {sorted(obtenidos)}"
        )
    return problemas


def main(argv=None):
    parser = argparse.ArgumentParser(description="Valida un CSV contra el Contrato de Datos (sin librerías externas).")
    parser.add_argument("--datos", required=True, help="Ruta del CSV a validar.")
    parser.add_argument("--contrato", default="contrato/contrato_datos.json", help="Ruta del contrato JSON.")
    parser.add_argument("--con-objetivo", action="store_true",
                        help="Exige también la columna objetivo (datos de entrenamiento).")
    parser.add_argument("--mostrar", type=int, default=10, help="Máximo de errores a imprimir.")
    args = parser.parse_args(argv)

    contrato = cargar_contrato(args.contrato)
    problemas = verificar_ejemplos_contrato(contrato)
    if problemas:
        print("FALLA: el contrato no es coherente consigo mismo:")
        for problema in problemas:
            print(f"  - {problema}")
        return 2
    print(f"Contrato {contrato['contrato']} v{contrato['version']}: ejemplos coherentes.")

    filas = cargar_csv(args.datos, contrato, args.con_objetivo)
    if not filas:
        print(f"FALLA: {args.datos} no tiene filas de datos.")
        return 1

    reporte = validar_filas(filas, contrato, args.con_objetivo)
    if not reporte:
        print(f"OK: {len(filas)} filas cumplen el contrato (tipos, nulos, rangos y reglas cruzadas).")
        return 0

    detalle = [(numero, e) for numero, errores in reporte for e in errores]
    print(f"FALLA: {len(detalle)} error(es) en {len(reporte)} de {len(filas)} filas.")
    for numero, e in detalle[: args.mostrar]:
        print(f"  fila {numero:>4} | {e['tipo_error']:<14} | {e['campo']}: {e['mensaje']}")
    if len(detalle) > args.mostrar:
        print(f"  ... y {len(detalle) - args.mostrar} errores más (usa --mostrar para verlos)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
