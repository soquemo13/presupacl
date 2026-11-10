"""Pruebas de clientes_busqueda (RF-04): PT-04-N, PT-04-L y PT-04-E."""

import sqlite3

import pytest

from proyecto.clientes import clientes_busqueda as cb
from proyecto.clientes import clientes_registro as cr
from proyecto.infraestructura import almacenamiento_datos as ad


@pytest.fixture
def conexion(tmp_path):
    con = ad.abrir_conexion(tmp_path / "prueba.db")
    ad.crear_esquema(con)
    cr.registrar_cliente(con, "Cliente de Prueba", "4770000000", ["Calle de Prueba 10", "Av. Ficticia 200"])
    cr.registrar_cliente(con, "Otra Empresa_50%", "4771234567", ["Calle Ajena 5"])
    yield con
    con.close()


def nombres(respuesta):
    return [c["nombre"] for c in respuesta["resultados"]]


@pytest.mark.parametrize("texto", ["Cliente de Prueba", "cliente de", "4770000000", "47700"])
def test_CA09_buscar_por_nombre_o_telefono(conexion, texto):
    respuesta = cb.buscar_clientes(conexion, texto)
    assert nombres(respuesta) == ["Cliente de Prueba"]
    assert respuesta["resultados"][0]["num_direcciones"] == 2
    assert respuesta["mensaje"] is None


def test_CA10_sin_coincidencias_indica_que_no_hay_resultados(conexion):
    respuesta = cb.buscar_clientes(conexion, "Nombre Inexistente")
    assert respuesta == {"resultados": [], "mensaje": cb.MENSAJE_SIN_RESULTADOS}


@pytest.mark.parametrize("texto, esperado", [("_", ["Otra Empresa_50%"]), ("%", ["Otra Empresa_50%"]), ("'; DROP TABLE clientes; --", [])])
def test_comodines_y_comillas_se_buscan_literalmente(conexion, texto, esperado):
    assert nombres(cb.buscar_clientes(conexion, texto)) == esperado
    assert ad.buscar_clientes(conexion, "Cliente")  # la tabla sigue ahí (P13)


def test_texto_vacio_no_consulta(conexion):
    assert cb.buscar_clientes(conexion, "   ")["resultados"] == []


def test_CA40_falla_del_repositorio_se_informa_sin_resultados(tmp_path):
    con = ad.abrir_conexion(tmp_path / "sin_esquema.db")  # sin tablas: la lectura falla
    with pytest.raises(cb.ErrorBusqueda) as error:
        cb.buscar_clientes(con, "Cliente")
    assert str(error.value) == cb.MENSAJE_FALLA
    assert isinstance(error.value.__cause__.__cause__, sqlite3.Error)
    con.close()
