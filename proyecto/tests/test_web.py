"""Pruebas de las pantallas web (Flask) del incremento 2.

PT-01-L / CA-37: la ruta protegida sin sesión exige iniciar sesión.
También se recorren login, registro, búsqueda, edición y configuración.
"""

import re

import pytest

from proyecto.auth import auth
from proyecto.infraestructura import almacenamiento_datos as ad
from proyecto.main import crear_app

USUARIO, PASSWORD = "admin_prueba", "clave-de-prueba-123"


@pytest.fixture
def app(tmp_path):
    ruta = tmp_path / "web.db"
    aplicacion = crear_app(ruta, secret_key="llave-solo-para-pruebas")
    con = ad.abrir_conexion(ruta)
    auth.crear_usuario(con, USUARIO, PASSWORD)
    con.close()
    aplicacion.config["RUTA_PRUEBA"] = ruta
    return aplicacion


@pytest.fixture
def cliente_http(app):
    return app.test_client()


def token(cliente_http, ruta="/login"):
    html = cliente_http.get(ruta).get_data(as_text=True)
    return re.search(r'name="_token" value="([0-9a-f]+)"', html).group(1)


def iniciar_sesion(cliente_http, password=PASSWORD):
    return cliente_http.post("/login", data={"_token": token(cliente_http), "usuario": USUARIO, "password": password})


@pytest.fixture
def sesion(cliente_http):
    assert iniciar_sesion(cliente_http).status_code == 302
    return cliente_http


@pytest.mark.parametrize("ruta", ["/", "/clientes", "/clientes/nuevo", "/clientes/1", "/configuracion"])
def test_CA37_ruta_protegida_sin_sesion_exige_login(cliente_http, ruta):
    respuesta = cliente_http.get(ruta)
    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]


def test_CA01_login_valido_entra_al_panel(cliente_http):
    respuesta = iniciar_sesion(cliente_http)
    assert respuesta.headers["Location"] == "/"
    assert "Panel" in cliente_http.get("/").get_data(as_text=True)


def test_CA02_login_incorrecto_muestra_error_y_no_da_acceso(cliente_http):
    respuesta = iniciar_sesion(cliente_http, "incorrecta")
    assert respuesta.status_code == 401
    assert auth.MENSAJE_RECHAZO in respuesta.get_data(as_text=True)
    assert cliente_http.get("/").status_code == 302


def test_login_no_redirige_a_otro_sitio(cliente_http):
    t = token(cliente_http)
    respuesta = cliente_http.post("/login?siguiente=//sitio-externo.com",
                                  data={"_token": t, "usuario": USUARIO, "password": PASSWORD})
    assert respuesta.headers["Location"] == "/"


def test_formulario_sin_token_se_rechaza(cliente_http):
    assert cliente_http.post("/login", data={"usuario": USUARIO, "password": PASSWORD}).status_code == 400


def test_salir_cierra_la_sesion(sesion):
    sesion.post("/logout", data={"_token": token(sesion, "/")})
    assert sesion.get("/").status_code == 302


def test_flujo_registrar_buscar_y_editar_cliente(sesion):
    t = token(sesion, "/clientes/nuevo")
    respuesta = sesion.post("/clientes/nuevo", data={
        "_token": t, "nombre": "Cliente de prueba", "telefono": "4770000000",
        "direccion": ["Calle de Prueba 10", ""],
    })
    assert respuesta.status_code == 302
    ruta_cliente = respuesta.headers["Location"]

    html = sesion.get("/clientes?q=4770000000").get_data(as_text=True)
    assert "Cliente de prueba" in html and ruta_cliente in html

    html = sesion.get(ruta_cliente).get_data(as_text=True)
    id_dir = re.search(r'name="direccion_(\d+)"', html).group(1)
    respuesta = sesion.post(ruta_cliente, data={
        "_token": t, "nombre": "Cliente de prueba", "telefono": "4771111111",
        f"direccion_{id_dir}": "Calle Corregida 12", "nueva_direccion": "Av. Ficticia 200",
    })
    assert respuesta.status_code == 302
    html = sesion.get(ruta_cliente).get_data(as_text=True)
    assert "4771111111" in html and "Calle Corregida 12" in html and "Av. Ficticia 200" in html


def test_registrar_sin_direccion_muestra_faltantes(sesion):
    t = token(sesion, "/clientes/nuevo")
    respuesta = sesion.post("/clientes/nuevo", data={"_token": t, "nombre": "X", "telefono": "1", "direccion": [""]})
    assert respuesta.status_code == 400
    assert "al menos una dirección" in respuesta.get_data(as_text=True)


def test_CA10_busqueda_sin_resultados_en_pantalla(sesion):
    assert "No hay clientes que coincidan" in sesion.get("/clientes?q=Inexistente").get_data(as_text=True)


def test_CA08_editar_cliente_inexistente_da_404(sesion):
    t = token(sesion, "/")
    respuesta = sesion.post("/clientes/999", data={"_token": t, "nombre": "X", "telefono": "1"})
    assert respuesta.status_code == 404
    assert sesion.get("/clientes/999").status_code == 404


def test_configuracion_se_guarda_desde_la_pantalla(sesion, app):
    t = token(sesion, "/configuracion")
    datos = {
        "_token": t, "nombre_comercial": "ACL Alarmas y Cámaras de León", "telefono": "4770000000",
        "correo": "contacto@ejemplo.com", "condiciones_default": "Línea 1\r\nLínea 2",
        "vigencia_dias_default": "15", "iva_tasa_default": "0.16", "utilidad_tasa_default": "0.20",
        "metodo_utilidad": "recargo",
    }
    assert "Falta capturar los datos de ACL" in sesion.get("/").get_data(as_text=True)
    assert sesion.post("/configuracion", data=datos).status_code == 302
    assert "Falta capturar" not in sesion.get("/").get_data(as_text=True)

    respuesta = sesion.post("/configuracion", data={**datos, "vigencia_dias_default": "0"})
    assert respuesta.status_code == 400
    assert "No se guardó la configuración" in respuesta.get_data(as_text=True)
