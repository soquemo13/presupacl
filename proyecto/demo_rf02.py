"""Demostración por consola del incremento 1 (RF-02).

Crea data/presupacl.db si no existe, registra un cliente ficticio con dos
direcciones, lo vuelve a leer de la BD y muestra un registro rechazado.

Ejecutar desde la raíz del repositorio:
    python -m proyecto.demo_rf02
"""

from proyecto.clientes import clientes_registro
from proyecto.infraestructura import almacenamiento_datos


def main():
    conexion = almacenamiento_datos.abrir_conexion()
    almacenamiento_datos.crear_esquema(conexion)
    print(f"Base de datos: {almacenamiento_datos.RUTA_BD_PREDETERMINADA}")

    id_cliente = clientes_registro.registrar_cliente(
        conexion,
        "Cliente de prueba",
        "4770000000",
        ["Calle de Prueba 10, León", "Av. Ficticia 200, León"],
    )
    cliente = almacenamiento_datos.obtener_cliente(conexion, id_cliente)
    print(f"\nCliente guardado (id {cliente['id_cliente']}): {cliente['nombre']} · {cliente['telefono']}")
    for direccion in cliente["direcciones"]:
        print(f"  - {direccion['direccion']}")

    print("\nIntento de registro sin teléfono ni direcciones:")
    try:
        clientes_registro.registrar_cliente(conexion, "Otro cliente", "", [])
    except clientes_registro.ErrorValidacion as error:
        print(f"  {error}")

    conexion.close()


if __name__ == "__main__":
    main()
