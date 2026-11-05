"""Integración de RF-02 de punta a punta (T-06).

clientes_registro valida y almacenamiento_datos guarda en una BD SQLite real
(archivo temporal). Cubre PT-02-N, PT-02-L, PT-02-E, PT-02-E2 y P01.
"""

import pytest

from proyecto.clientes import clientes_registro as cr
from proyecto.infraestructura import almacenamiento_datos as ad

NOMBRE = "Cliente de prueba"
TELEFONO = "4770000000"
DIRECCIONES = ["Calle de Prueba 10, León", "Av. Ficticia 200, León"]


@pytest.fixture
def ruta_bd(tmp_path):
    return tmp_path / "presupacl.db"


@pytest.fixture
def conexion(ruta_bd):
    con = ad.abrir_conexion(ruta_bd)
    ad.crear_esquema(con)
    yield con
    con.close()


def contar_clientes(conexion):
    return conexion.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]


def test_PT02N_registrar_y_consultar_dos_direcciones(conexion):
    id_cliente = cr.registrar_cliente(conexion, NOMBRE, TELEFONO, DIRECCIONES)

    cliente = ad.obtener_cliente(conexion, id_cliente)
    assert (cliente["nombre"], cliente["telefono"]) == (NOMBRE, TELEFONO)
    assert [d["direccion"] for d in cliente["direcciones"]] == DIRECCIONES


def test_PT02L_registrar_con_exactamente_una_direccion(conexion):
    id_cliente = cr.registrar_cliente(conexion, NOMBRE, TELEFONO, DIRECCIONES[:1])

    assert len(ad.obtener_cliente(conexion, id_cliente)["direcciones"]) == 1


@pytest.mark.parametrize("nombre, telefono", [("", TELEFONO), (NOMBRE, "")])
def test_PT02E_falta_nombre_o_telefono_no_se_guarda(conexion, nombre, telefono):
    with pytest.raises(cr.ErrorValidacion):
        cr.registrar_cliente(conexion, nombre, telefono, DIRECCIONES)

    assert contar_clientes(conexion) == 0


def test_PT02E2_sin_direcciones_no_se_guarda(conexion):
    with pytest.raises(cr.ErrorValidacion):
        cr.registrar_cliente(conexion, NOMBRE, TELEFONO, [])

    assert contar_clientes(conexion) == 0


def test_P01_cliente_registrado_persiste_al_reabrir(ruta_bd):
    con = ad.abrir_conexion(ruta_bd)
    ad.crear_esquema(con)
    id_cliente = cr.registrar_cliente(con, NOMBRE, TELEFONO, DIRECCIONES)
    con.close()

    con = ad.abrir_conexion(ruta_bd)
    cliente = ad.obtener_cliente(con, id_cliente)
    con.close()
    assert cliente["nombre"] == NOMBRE
    assert len(cliente["direcciones"]) == 2
