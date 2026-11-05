"""Pruebas de auth (RF-01): PT-01-N y PT-01-E. PT-01-L (ruta sin sesión) está en test_web.py."""

import pytest

from proyecto.auth import auth
from proyecto.infraestructura import almacenamiento_datos as ad

USUARIO = "admin_prueba"
PASSWORD = "clave-de-prueba-123"


@pytest.fixture
def conexion(tmp_path):
    con = ad.abrir_conexion(tmp_path / "prueba.db")
    ad.crear_esquema(con)
    auth.crear_usuario(con, USUARIO, PASSWORD)
    yield con
    con.close()


def test_CA01_credenciales_validas_conceden_acceso(conexion):
    sesion = auth.verificar_credenciales(conexion, USUARIO, PASSWORD)
    assert sesion["usuario"] == USUARIO


@pytest.mark.parametrize(
    "usuario, password",
    [(USUARIO, "incorrecta"), ("no_existe", PASSWORD), (USUARIO, ""), ("", "")],
)
def test_CA02_credenciales_incorrectas_se_rechazan(conexion, usuario, password):
    with pytest.raises(auth.ErrorAutenticacion) as error:
        auth.verificar_credenciales(conexion, usuario, password)
    assert str(error.value) == auth.MENSAJE_RECHAZO


def test_RNF03_la_contrasena_no_se_guarda_en_texto_plano(conexion):
    guardado = ad.obtener_usuario(conexion, USUARIO)["password_hash"]
    assert PASSWORD not in guardado
    assert guardado != PASSWORD


def test_hash_no_depende_de_scrypt(conexion):
    """El Python de macOS no trae hashlib.scrypt; se usa pbkdf2."""
    assert ad.obtener_usuario(conexion, USUARIO)["password_hash"].startswith("pbkdf2:sha256:")


def test_usuario_repetido_se_rechaza(conexion):
    with pytest.raises(ad.ErrorAlmacenamiento):
        auth.crear_usuario(conexion, USUARIO, "otra")


@pytest.mark.parametrize("usuario, password", [("", "x"), ("   ", "x"), ("nuevo", "")])
def test_crear_usuario_sin_datos_se_rechaza(conexion, usuario, password):
    with pytest.raises(ValueError):
        auth.crear_usuario(conexion, usuario, password)


def test_comando_crea_usuario_con_contrasena_de_variable_de_entorno(tmp_path, monkeypatch):
    monkeypatch.setattr(ad, "RUTA_BD_PREDETERMINADA", tmp_path / "cli.db")
    monkeypatch.setenv("PRESUPACL_PASSWORD", PASSWORD)
    assert auth.main(["admin_cli"]) == 0

    con = ad.abrir_conexion(tmp_path / "cli.db")
    assert auth.verificar_credenciales(con, "admin_cli", PASSWORD)["usuario"] == "admin_cli"
    con.close()
