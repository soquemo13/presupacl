"""Pruebas de almacenamiento_datos (RF-02, plan de implementación v1.1).

Cada prueba usa una base temporal (tmp_path) con datos ficticios.
"""

import sqlite3
from datetime import datetime

import pytest

from proyecto.infraestructura import almacenamiento_datos as ad


@pytest.fixture
def conexion(tmp_path):
    con = ad.abrir_conexion(tmp_path / "prueba.db")
    ad.crear_esquema(con)
    yield con
    con.close()


# ---------- T-03: esquema y llaves foráneas ----------

def test_abrir_conexion_activa_llaves_foraneas(tmp_path):
    con = ad.abrir_conexion(tmp_path / "prueba.db")
    assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    con.close()


def test_abrir_conexion_crea_la_carpeta_si_no_existe(tmp_path):
    ruta = tmp_path / "data" / "presupacl.db"
    con = ad.abrir_conexion(ruta)
    con.close()
    assert ruta.exists()


def test_crear_esquema_crea_las_dos_tablas(conexion):
    tablas = {f["name"] for f in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"clientes", "direcciones_cliente"} <= tablas


def test_crear_esquema_dos_veces_no_falla(conexion):
    ad.crear_esquema(conexion)


def test_P11_direccion_con_cliente_inexistente_se_rechaza(conexion):
    with pytest.raises(sqlite3.IntegrityError):
        conexion.execute(
            "INSERT INTO direcciones_cliente (id_cliente, direccion) VALUES (?, ?)",
            (999, "Calle de Prueba 10, León"),
        )


# ---------- T-04: guardado transaccional y consulta ----------

NOMBRE = "Cliente de prueba"
TELEFONO = "4770000000"


def contar(conexion, tabla):
    return conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]


def test_CA04_normal_cliente_con_dos_direcciones(conexion):
    direcciones = ["Calle de Prueba 10, León", "Av. Ficticia 200, León"]
    id_cliente = ad.crear_cliente_con_direcciones(conexion, NOMBRE, TELEFONO, direcciones)

    cliente = ad.obtener_cliente(conexion, id_cliente)
    assert cliente["nombre"] == NOMBRE
    assert cliente["telefono"] == TELEFONO
    assert [d["direccion"] for d in cliente["direcciones"]] == direcciones


def test_CA38_limite_cliente_con_una_sola_direccion(conexion):
    id_cliente = ad.crear_cliente_con_direcciones(conexion, NOMBRE, TELEFONO, ["Calle de Prueba 10, León"])

    cliente = ad.obtener_cliente(conexion, id_cliente)
    assert len(cliente["direcciones"]) == 1


def test_fechas_de_alta_en_formato_iso(conexion):
    id_cliente = ad.crear_cliente_con_direcciones(conexion, NOMBRE, TELEFONO, ["Calle de Prueba 10, León"])

    cliente = ad.obtener_cliente(conexion, id_cliente)
    assert datetime.fromisoformat(cliente["creado_en"])
    assert cliente["creado_en"] == cliente["actualizado_en"]


def test_P13_limite_texto_con_comillas_se_guarda_literal(conexion):
    nombre = "O'Neil\"; DROP TABLE clientes; --"
    id_cliente = ad.crear_cliente_con_direcciones(conexion, nombre, TELEFONO, ["Calle 'Prueba' 10"])

    cliente = ad.obtener_cliente(conexion, id_cliente)
    assert cliente["nombre"] == nombre
    assert cliente["direcciones"][0]["direccion"] == "Calle 'Prueba' 10"
    assert contar(conexion, "clientes") == 1


def test_P12_error_falla_en_segunda_direccion_revierte_todo(conexion):
    # La segunda dirección es None y viola NOT NULL: simula una falla a la mitad.
    with pytest.raises(ad.ErrorAlmacenamiento):
        ad.crear_cliente_con_direcciones(conexion, NOMBRE, TELEFONO, ["Calle de Prueba 10, León", None])

    assert contar(conexion, "clientes") == 0
    assert contar(conexion, "direcciones_cliente") == 0


def test_error_sin_direcciones_no_guarda_nada(conexion):
    with pytest.raises(ad.ErrorAlmacenamiento):
        ad.crear_cliente_con_direcciones(conexion, NOMBRE, TELEFONO, [])

    assert contar(conexion, "clientes") == 0


def test_error_nombre_vacio_rechazado_por_la_bd(conexion):
    with pytest.raises(ad.ErrorAlmacenamiento):
        ad.crear_cliente_con_direcciones(conexion, "   ", TELEFONO, ["Calle de Prueba 10, León"])

    assert contar(conexion, "clientes") == 0


def test_obtener_cliente_inexistente_regresa_none(conexion):
    assert ad.obtener_cliente(conexion, 999) is None


def test_P01_datos_persisten_al_cerrar_y_reabrir(tmp_path):
    ruta = tmp_path / "presupacl.db"
    con = ad.abrir_conexion(ruta)
    ad.crear_esquema(con)
    id_cliente = ad.crear_cliente_con_direcciones(
        con, NOMBRE, TELEFONO, ["Calle de Prueba 10, León", "Av. Ficticia 200, León"]
    )
    con.close()

    con = ad.abrir_conexion(ruta)
    cliente = ad.obtener_cliente(con, id_cliente)
    con.close()
    assert cliente["nombre"] == NOMBRE
    assert len(cliente["direcciones"]) == 2
