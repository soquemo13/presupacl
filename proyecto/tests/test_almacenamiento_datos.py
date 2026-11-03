"""Pruebas de almacenamiento_datos (RF-02, plan de implementación v1.1).

Cada prueba usa una base temporal (tmp_path) con datos ficticios.
"""

import sqlite3

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
