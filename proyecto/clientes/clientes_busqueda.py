"""clientes_busqueda: buscar un cliente existente por nombre o teléfono (RF-04, HU-04).

No ejecuta SQL: pide la consulta a almacenamiento_datos.
"""

from proyecto.infraestructura import almacenamiento_datos

MENSAJE_SIN_RESULTADOS = "No hay clientes que coincidan con la búsqueda."
MENSAJE_FALLA = "No se pudo consultar los clientes. Intente de nuevo; no se muestran resultados."


class ErrorBusqueda(Exception):
    """Falla del repositorio de clientes (CA-40)."""


def buscar_clientes(conexion, texto):
    """Regresa {"resultados": [...], "mensaje": str | None}.

    - Con coincidencias: la lista de clientes y mensaje None (CA-09).
    - Sin coincidencias: lista vacía y MENSAJE_SIN_RESULTADOS (CA-10).
    - Texto vacío: lista vacía y un mensaje que pide escribir algo.
    - Si la BD falla lanza ErrorBusqueda, sin resultados inventados (CA-40).
    """
    texto = (texto or "").strip()
    if not texto:
        return {"resultados": [], "mensaje": "Escriba un nombre o teléfono para buscar."}
    try:
        resultados = almacenamiento_datos.buscar_clientes(conexion, texto)
    except almacenamiento_datos.ErrorAlmacenamiento as error:
        raise ErrorBusqueda(MENSAJE_FALLA) from error
    return {"resultados": resultados, "mensaje": None if resultados else MENSAJE_SIN_RESULTADOS}
