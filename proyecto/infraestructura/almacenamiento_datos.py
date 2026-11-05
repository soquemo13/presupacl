"""almacenamiento_datos: único módulo de PresupACL que accede a la base de datos.

Responsabilidad (sección 3.8 de la especificación v2.5): centralizar la conexión
a SQLite, las consultas parametrizadas, las transacciones y la integridad
referencial. Ningún otro módulo debe ejecutar SQL.

Cada tabla se agrega en el incremento que la usa:
- Incremento 1 (RF-02): clientes, direcciones_cliente.
- Incremento 2 (RF-01): usuarios.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

# data/presupacl.db en la raíz del repositorio. Las pruebas pasan su propia ruta.
RUTA_BD_PREDETERMINADA = Path(__file__).resolve().parents[2] / "data" / "presupacl.db"

# Esquema según el diccionario de datos (sección 3.4 de v2.5).
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

CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario      INTEGER PRIMARY KEY,
    usuario         TEXT NOT NULL UNIQUE CHECK (length(trim(usuario)) > 0),
    password_hash   TEXT NOT NULL
);
"""


class ErrorAlmacenamiento(Exception):
    """Error al leer o escribir en la base de datos."""


class ErrorNoEncontrado(ErrorAlmacenamiento):
    """El registro que se quiere modificar no existe."""


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


def actualizar_cliente(conexion, id_cliente, nombre, telefono, direcciones_editadas, direcciones_nuevas):
    """Edita un cliente existente en una sola transacción (RF-03).

    direcciones_editadas: {id_direccion: texto nuevo}; cada id debe pertenecer
    al cliente. direcciones_nuevas: lista de textos a agregar. No se borran
    direcciones, así el cliente siempre conserva al menos una (CA-39) y las
    cotizaciones que ya las usan no pierden la referencia.

    Si el cliente no existe lanza ErrorNoEncontrado y no crea nada (CA-08).
    """
    try:
        with conexion:
            cursor = conexion.execute(
                "UPDATE clientes SET nombre = ?, telefono = ?, actualizado_en = ? WHERE id_cliente = ?",
                (nombre, telefono, _ahora_iso(), id_cliente),
            )
            if cursor.rowcount == 0:
                raise ErrorNoEncontrado(f"No existe el cliente {id_cliente}; no se guardaron cambios.")
            for id_direccion, direccion in direcciones_editadas.items():
                cursor = conexion.execute(
                    "UPDATE direcciones_cliente SET direccion = ? WHERE id_direccion = ? AND id_cliente = ?",
                    (direccion, id_direccion, id_cliente),
                )
                if cursor.rowcount == 0:
                    raise ErrorNoEncontrado(
                        f"La dirección {id_direccion} no pertenece al cliente {id_cliente}; no se guardaron cambios."
                    )
            for direccion in direcciones_nuevas:
                conexion.execute(
                    "INSERT INTO direcciones_cliente (id_cliente, direccion) VALUES (?, ?)",
                    (id_cliente, direccion),
                )
    except sqlite3.Error as error:
        raise ErrorAlmacenamiento("No se pudieron guardar los cambios del cliente.") from error


# ---------- Usuarios (RF-01) ----------

def crear_usuario(conexion, usuario, password_hash):
    """Guarda un usuario con su contraseña ya convertida en hash por auth.

    Este módulo nunca recibe la contraseña en texto plano (RNF-03).
    Regresa el id_usuario o lanza ErrorAlmacenamiento si el usuario ya existe.
    """
    try:
        with conexion:
            cursor = conexion.execute(
                "INSERT INTO usuarios (usuario, password_hash) VALUES (?, ?)",
                (usuario, password_hash),
            )
    except sqlite3.IntegrityError as error:
        raise ErrorAlmacenamiento(f"El usuario «{usuario}» ya existe o no es válido.") from error
    except sqlite3.Error as error:
        raise ErrorAlmacenamiento("No se pudo guardar el usuario.") from error
    return cursor.lastrowid


def obtener_usuario(conexion, usuario):
    """Regresa {id_usuario, usuario, password_hash} o None si no existe."""
    fila = conexion.execute(
        "SELECT id_usuario, usuario, password_hash FROM usuarios WHERE usuario = ?",
        (usuario,),
    ).fetchone()
    return dict(fila) if fila else None
