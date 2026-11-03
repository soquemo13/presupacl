"""almacenamiento_datos: único módulo de PresupACL que accede a la base de datos.

Responsabilidad (sección 3.8 de la especificación v2.4): centralizar la conexión
a SQLite, las consultas parametrizadas, las transacciones y la integridad
referencial. Ningún otro módulo debe ejecutar SQL.

Incremento 1 (RF-02): solo se crean las tablas clientes y direcciones_cliente.
Las otras siete tablas se agregan en el incremento que las use.
"""

import sqlite3
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
