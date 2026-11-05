"""main: aplicación web local de PresupACL (Flask).

SUPUESTO — validar con el equipo (D09): Flask como framework web.

Ejecutar desde la raíz del repositorio:
    python -m proyecto.auth.auth admin      # solo la primera vez: crea el usuario
    python -m proyecto.main                 # abre http://127.0.0.1:8000

Variables de entorno (opcionales, nunca en el código):
    PRESUPACL_SECRET_KEY  llave de las sesiones; si falta se genera una al
                          arrancar y las sesiones se cierran al reiniciar.
    PRESUPACL_HOST        127.0.0.1 por defecto; 0.0.0.0 para la red local (RNF-06).
    PRESUPACL_PORT        8000 por defecto. No se usa 5000 porque en macOS lo
                          ocupa el Receptor AirPlay y el navegador da error 403.
"""

import functools
import os
import secrets

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for

from proyecto.auth import auth
from proyecto.clientes import clientes_busqueda, clientes_registro
from proyecto.config import settings
from proyecto.infraestructura import almacenamiento_datos


def login_requerido(vista):
    """Protege una ruta: sin sesión se manda a iniciar sesión (CA-37)."""

    @functools.wraps(vista)
    def envoltura(*args, **kwargs):
        if "id_usuario" not in session:
            return redirect(url_for("login", siguiente=request.path))
        return vista(*args, **kwargs)

    return envoltura


def crear_app(ruta_bd=None, secret_key=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = secret_key or os.environ.get("PRESUPACL_SECRET_KEY") or secrets.token_hex(32)
    app.config["RUTA_BD"] = ruta_bd
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # logo de hasta 5 MB

    conexion = almacenamiento_datos.abrir_conexion(ruta_bd)
    almacenamiento_datos.crear_esquema(conexion)
    conexion.close()

    def bd():
        if "bd" not in g:
            g.bd = almacenamiento_datos.abrir_conexion(app.config["RUTA_BD"])
        return g.bd

    @app.teardown_appcontext
    def cerrar_bd(_error):
        conexion = g.pop("bd", None)
        if conexion is not None:
            conexion.close()

    # ---------- Protección CSRF sencilla para formularios ----------
    @app.before_request
    def revisar_token():
        if request.method == "POST":
            if not request.form.get("_token") or request.form.get("_token") != session.get("_token"):
                abort(400, "Formulario vencido; vuelva a cargar la página.")

    @app.context_processor
    def token_formulario():
        if "_token" not in session:
            session["_token"] = secrets.token_hex(16)
        return {"token": session["_token"], "usuario_actual": session.get("usuario")}

    # ---------- RF-01 Inicio de sesión ----------
    @app.route("/login", methods=["GET", "POST"])
    def login():
        siguiente = request.args.get("siguiente", "")
        if request.method == "POST":
            try:
                datos = auth.verificar_credenciales(bd(), request.form.get("usuario"), request.form.get("password"))
            except auth.ErrorAutenticacion as error:
                return render_template("login.html", error=str(error), siguiente=siguiente), 401
            token = session.get("_token")
            session.clear()
            session.update(id_usuario=datos["id_usuario"], usuario=datos["usuario"], _token=token)
            # Solo se aceptan rutas internas para no redirigir a otro sitio.
            destino = siguiente if siguiente.startswith("/") and not siguiente.startswith("//") else url_for("panel")
            return redirect(destino)
        return render_template("login.html", siguiente=siguiente)

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    @login_requerido
    def panel():
        return render_template("panel.html", config_completa=settings.configuracion_completa(bd()))

    # ---------- RF-04 Búsqueda / RF-02 Registro / RF-03 Edición ----------
    @app.route("/clientes")
    @login_requerido
    def clientes():
        texto = request.args.get("q", "")
        respuesta, error = {"resultados": [], "mensaje": None}, None
        if texto.strip():
            try:
                respuesta = clientes_busqueda.buscar_clientes(bd(), texto)
            except clientes_busqueda.ErrorBusqueda as falla:
                error = str(falla)
        return render_template("clientes.html", q=texto, error=error, **respuesta)

    @app.route("/clientes/nuevo", methods=["GET", "POST"])
    @login_requerido
    def cliente_nuevo():
        datos = {"nombre": "", "telefono": "", "direcciones": [""]}
        if request.method == "POST":
            datos = {
                "nombre": request.form.get("nombre", ""),
                "telefono": request.form.get("telefono", ""),
                "direcciones": [d for d in request.form.getlist("direccion") if d.strip()],
            }
            try:
                id_cliente = clientes_registro.registrar_cliente(bd(), datos["nombre"], datos["telefono"], datos["direcciones"])
            except clientes_registro.ErrorValidacion as error:
                datos["direcciones"] = datos["direcciones"] or [""]
                return render_template("cliente_nuevo.html", datos=datos, error=str(error), faltantes=error.campos_faltantes), 400
            except almacenamiento_datos.ErrorAlmacenamiento as error:
                return render_template("cliente_nuevo.html", datos=datos, error=str(error), faltantes=[]), 500
            flash("Cliente registrado.")
            return redirect(url_for("cliente_detalle", id_cliente=id_cliente))
        return render_template("cliente_nuevo.html", datos=datos, error=None, faltantes=[])

    @app.route("/clientes/<int:id_cliente>", methods=["GET", "POST"])
    @login_requerido
    def cliente_detalle(id_cliente):
        if request.method == "POST":
            editadas = {
                int(clave.removeprefix("direccion_")): valor
                for clave, valor in request.form.items()
                if clave.startswith("direccion_") and clave.removeprefix("direccion_").isdigit()
            }
            try:
                clientes_registro.editar_cliente(
                    bd(), id_cliente, request.form.get("nombre"), request.form.get("telefono"),
                    editadas, request.form.getlist("nueva_direccion"),
                )
            except almacenamiento_datos.ErrorNoEncontrado as error:
                abort(404, str(error))
            except (clientes_registro.ErrorValidacion, almacenamiento_datos.ErrorAlmacenamiento) as error:
                cliente = almacenamiento_datos.obtener_cliente(bd(), id_cliente)
                return render_template("cliente_detalle.html", cliente=cliente, error=str(error)), 400
            flash("Cambios guardados.")
            return redirect(url_for("cliente_detalle", id_cliente=id_cliente))

        cliente = almacenamiento_datos.obtener_cliente(bd(), id_cliente)
        if cliente is None:
            abort(404, f"No existe el cliente {id_cliente}.")
        return render_template("cliente_detalle.html", cliente=cliente, error=None)

    # ---------- RF-21 Configuración de ACL ----------
    @app.route("/configuracion", methods=["GET", "POST"])
    @login_requerido
    def configuracion():
        config = settings.obtener_configuracion(bd())
        if request.method == "POST":
            datos = {campo: request.form.get(campo) for campo in almacenamiento_datos.CAMPOS_CONFIGURACION}
            datos["logo_ruta"] = config.get("logo_ruta")
            try:
                logo = request.files.get("logo")
                if logo and logo.filename:
                    datos["logo_ruta"] = settings.guardar_logo(logo.read(), logo.filename)
                settings.guardar_configuracion(bd(), datos)
            except settings.ErrorConfiguracion as error:
                return render_template("configuracion.html", config=datos, error=str(error), campos=error.campos), 400
            flash("Configuración guardada.")
            return redirect(url_for("configuracion"))
        return render_template("configuracion.html", config=config, error=None, campos=[])

    @app.errorhandler(404)
    def no_encontrado(error):
        return render_template("error.html", mensaje=error.description), 404

    @app.errorhandler(400)
    def solicitud_invalida(error):
        return render_template("error.html", mensaje=error.description), 400

    return app


if __name__ == "__main__":
    crear_app().run(
        host=os.environ.get("PRESUPACL_HOST", "127.0.0.1"),
        port=int(os.environ.get("PRESUPACL_PORT", "8000")),
        debug=False,
    )
