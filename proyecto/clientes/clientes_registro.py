"""clientes_registro: registrar clientes nuevos con sus direcciones (RF-02, HU-02).

Responsabilidad (sección 2.5 de la especificación v2.5): validar los datos que
captura el usuario y pedir el guardado a almacenamiento_datos. Este módulo no
ejecuta SQL.

Contrato acordado en T-02 (plan de implementación v1.2):
    registrar_cliente(conexion, nombre, telefono, direcciones) -> id_cliente
    Si faltan datos, lanza ErrorValidacion con la lista de campos faltantes y
    no llama al almacenamiento.

Supuesto de D07 (por validar con ACL): nombre, teléfono y direcciones se
recortan de espacios; un valor vacío o solo con espacios cuenta como faltante.
El teléfono se guarda como texto, sin formato obligatorio ni unicidad.
"""

from proyecto.infraestructura import almacenamiento_datos

# Nombres que se muestran al usuario en el mensaje de error.
ETIQUETAS = {"nombre": "nombre", "telefono": "teléfono", "direcciones": "al menos una dirección"}


class ErrorValidacion(Exception):
    """Faltan datos obligatorios; no se guardó nada (CA-05, CA-68)."""

    def __init__(self, campos_faltantes):
        self.campos_faltantes = campos_faltantes
        etiquetas = ", ".join(ETIQUETAS[c] for c in campos_faltantes)
        super().__init__(f"Faltan datos obligatorios: {etiquetas}. No se guardó el cliente.")


def _limpiar(texto):
    """Quita espacios al inicio y al final; None se trata como vacío."""
    return (texto or "").strip()


def validar_cliente(nombre, telefono, direcciones):
    """Regresa la lista de campos faltantes (vacía si todo está completo)."""
    faltantes = []
    if not _limpiar(nombre):
        faltantes.append("nombre")
    if not _limpiar(telefono):
        faltantes.append("telefono")
    # CA-68: se necesita al menos una dirección y ninguna puede venir en blanco.
    if not direcciones or any(not _limpiar(d) for d in direcciones):
        faltantes.append("direcciones")
    return faltantes


def registrar_cliente(conexion, nombre, telefono, direcciones):
    """Valida los datos y guarda el cliente con sus direcciones (RF-02).

    Regresa el id_cliente creado. Si falta algún dato lanza ErrorValidacion
    con todos los campos faltantes juntos (CA-05, CA-68).
    """
    faltantes = validar_cliente(nombre, telefono, direcciones)
    if faltantes:
        raise ErrorValidacion(faltantes)

    return almacenamiento_datos.crear_cliente_con_direcciones(
        conexion,
        _limpiar(nombre),
        _limpiar(telefono),
        [_limpiar(d) for d in direcciones],
    )
