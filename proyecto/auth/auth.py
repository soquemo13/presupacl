"""auth: inicio de sesión de PresupACL (RF-01, HU-01).

Valida credenciales contra la tabla usuarios. Las contraseñas se guardan
solo como hash (RNF-03) usando werkzeug.security, que viene con Flask.
SUPUESTO — validar con el equipo (D09): Flask/werkzeug para hash y sesiones.

No hay bloqueo por intentos fallidos: CA-03 quedó fuera del alcance (sección 1.6).

Crear el primer usuario (no hay contraseñas en el código):
    python -m proyecto.auth.auth <usuario>
La contraseña se pide por teclado, o se toma de la variable de entorno
PRESUPACL_PASSWORD si existe.
"""

import getpass
import os
import sys

from werkzeug.security import check_password_hash, generate_password_hash

from proyecto.infraestructura import almacenamiento_datos

MENSAJE_RECHAZO = "Usuario o contraseña incorrectos."

# pbkdf2 en lugar del scrypt predeterminado de werkzeug: el Python 3.9 que trae
# macOS (Command Line Tools) usa LibreSSL y no tiene hashlib.scrypt.
METODO_HASH = "pbkdf2:sha256:600000"


class ErrorAutenticacion(Exception):
    """Credenciales rechazadas (CA-02)."""


def crear_usuario(conexion, usuario, password):
    """Registra un usuario administrativo guardando solo el hash de su contraseña."""
    usuario = (usuario or "").strip()
    if not usuario or not password:
        raise ValueError("El usuario y la contraseña son obligatorios.")
    return almacenamiento_datos.crear_usuario(conexion, usuario, generate_password_hash(password, method=METODO_HASH))


def verificar_credenciales(conexion, usuario, password):
    """Regresa {id_usuario, usuario} si las credenciales son válidas (CA-01).

    Con usuario inexistente o contraseña incorrecta lanza ErrorAutenticacion
    con el mismo mensaje, para no revelar cuál de los dos falló (CA-02).
    """
    registro = almacenamiento_datos.obtener_usuario(conexion, (usuario or "").strip())
    if registro is None or not password or not check_password_hash(registro["password_hash"], password):
        raise ErrorAutenticacion(MENSAJE_RECHAZO)
    return {"id_usuario": registro["id_usuario"], "usuario": registro["usuario"]}


def main(argumentos=None):
    argumentos = sys.argv[1:] if argumentos is None else argumentos
    if len(argumentos) != 1:
        print("Uso: python -m proyecto.auth.auth <usuario>")
        return 1
    password = os.environ.get("PRESUPACL_PASSWORD") or getpass.getpass("Contraseña: ")
    conexion = almacenamiento_datos.abrir_conexion()
    almacenamiento_datos.crear_esquema(conexion)
    try:
        crear_usuario(conexion, argumentos[0], password)
    except (ValueError, almacenamiento_datos.ErrorAlmacenamiento) as error:
        print(error)
        return 1
    finally:
        conexion.close()
    print(f"Usuario «{argumentos[0]}» creado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
