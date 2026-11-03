"""almacenamiento_datos: único módulo de PresupACL que accede a la base de datos.

Responsabilidad (sección 3.8 de la especificación v2.4): centralizar la conexión
a SQLite, las consultas parametrizadas, las transacciones y la integridad
referencial. Ningún otro módulo debe ejecutar SQL.

Incremento 1 (RF-02): solo se crean las tablas clientes y direcciones_cliente.
Las otras siete tablas se agregan en el incremento que las use.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

# data/presupacl.db en la raíz del repositorio. Las pruebas pasan su propia ruta.
RUTA_BD_PREDETERMINADA = Path(__file__).resolve().parents[2] / "data" / "presupacl.db"

# Esquema según el diccionario de datos (sección 3.4 de v2.4).
# Los CHECK evitan guardar textos vacíos aunque un módulo se salte la validación.
ESQUEMA = """
CREATE TABLE IF NOT EXISTS clientes (
    id_cliente      INTEGER PRIMARY KEY,
    nombre          TEXT NOT NULL CHECK (length(trim(nombre)) > 0),
    telefono        TEXT NOT NULL CHECK (length(trim(telefono)) > 0),
    creado_en       TEXT NOT NULL,
    actualizado_en  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS direcciones_cliente (
    id_direccion    INTEGER PRIMARY KEY,
    id_cliente      INTEGER NOT NULL REFERENCES clientes (id_cliente),
    direccion       TEXT NOT NULL CHECK (length(trim(direccion)) > 0)
);
"""


class ErrorAlmacenamiento(Exception):
    """Error al leer o escribir en la base de datos."""


def abrir_conexion(ruta_bd=None):
    """Abre la base de datos con las llaves foráneas activadas.

    SQLite trae las llaves foráneas apagadas por defecto, por eso se activan
    en cada conexión (prueba P11). Si la carpeta no existe, se crea.
    """
    ruta = Path(ruta_bd) if ruta_bd else RUTA_BD_PREDETERMINADA
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(ruta)
    conexion.execute("PRAGMA foreign_keys = ON")
    conexion.row_factory = sqlite3.Row
    return conexion


def crear_esquema(conexion):
    """Crea las tablas si no existen. Se puede llamar varias veces sin perder datos."""
    conexion.executescript(ESQUEMA)


def _ahora_iso():
    """Fecha y hora local del servidor en ISO 8601 (supuesto de D08, por validar con ACL)."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def crear_cliente_con_direcciones(conexion, nombre, telefono, direcciones):
    """Guarda un cliente y todas sus direcciones en una sola transacción (RF-02).

    Recibe datos ya validados por clientes_registro. Si cualquier INSERT falla,
    se revierte todo y no queda un cliente a medias (prueba P12). Todas las
    consultas son parametrizadas (prueba P13).

    Regresa el id_cliente creado o lanza ErrorAlmacenamiento.
    """
    if not direcciones:
        # Barrera de integridad: un cliente sin dirección no se guarda (CA-68).
        raise ErrorAlmacenamiento("El cliente debe tener al menos una dirección; no se guardó.")

    ahora = _ahora_iso()
    try:
        with conexion:  # confirma al terminar o revierte si hay excepción
            cursor = conexion.execute(
                "INSERT INTO clientes (nombre, telefono, creado_en, actualizado_en) VALUES (?, ?, ?, ?)",
                (nombre, telefono, ahora, ahora),
            )
            id_cliente = cursor.lastrowid
            for direccion in direcciones:
                conexion.execute(
                    "INSERT INTO direcciones_cliente (id_cliente, direccion) VALUES (?, ?)",
                    (id_cliente, direccion),
                )
    except sqlite3.Error as error:
        raise ErrorAlmacenamiento("No se pudo guardar el cliente; no se guardó ningún dato.") from error
    return id_cliente


def obtener_cliente(conexion, id_cliente):
    """Consulta un cliente con sus direcciones. Regresa None si no existe."""
    fila = conexion.execute(
        "SELECT id_cliente, nombre, telefono, creado_en, actualizado_en FROM clientes WHERE id_cliente = ?",
        (id_cliente,),
    ).fetchone()
    if fila is None:
        return None

    direcciones = conexion.execute(
        "SELECT id_direccion, direccion FROM direcciones_cliente WHERE id_cliente = ? ORDER BY id_direccion",
        (id_cliente,),
    ).fetchall()

    cliente = dict(fila)
    cliente["direcciones"] = [dict(d) for d in direcciones]
    return cliente
