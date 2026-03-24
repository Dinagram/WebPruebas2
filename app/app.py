
from datetime import datetime, date, timedelta
import os
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from sqlalchemy import func, and_, case

from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify, send_from_directory
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from extensions import db, login_manager
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import uuid

from config import config

from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
# Primero carga la configuración para que las extensiones la tengan
app.config.from_object(config['development'])

# Ahora configura las demás cosas que dependen de la configuración

db.init_app(app)

UPLOAD_FOLDER = os.path.abspath(os.path.join(app.root_path, '..', 'static', 'uploads'))
LEGACY_UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # Esto puedes dejarlo aquí o en config.py



login_manager_app = LoginManager(app)
TOKEN_SALT = "cliente-access"

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    clean_name = filename.split('/', 1)[1] if filename.startswith('uploads/') else filename
    primary_path = os.path.join(app.config['UPLOAD_FOLDER'], clean_name)
    if os.path.exists(primary_path):
        return send_from_directory(app.config['UPLOAD_FOLDER'], clean_name)
    return send_from_directory(LEGACY_UPLOAD_FOLDER, clean_name)


def _client_token_serializer():
    return URLSafeTimedSerializer(app.config["SECRET_KEY"])


def validate_client_access(user, token):
    if current_user.is_authenticated and current_user.username == user.username:
        return True

    if not token:
        return False

    try:
        payload = _client_token_serializer().loads(
            token,
            salt=TOKEN_SALT,
            max_age=app.config["CLIENT_ACCESS_TOKEN_MAX_AGE"]
        )
    except (SignatureExpired, BadSignature):
        return False

    if payload.get("username") != user.username:
        return False

    if payload.get("nonce") != user.reset_token:
        return False

    login_user(user)
    return True

from models.ModelUser import ModelUser
from models.entities.User import User
from models.Pedido import Pedido, Marcas, Tallas

csrf = CSRFProtect(app)
@login_manager_app.user_loader
def load_user(id):
    return ModelUser.get_by_id(int(id))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        logged_user = ModelUser.login(username, password)
        if logged_user != None:
            if logged_user.password:
                login_user(logged_user)
                if username == "Vaello":
                    return redirect(url_for('storage', nombre=username))
                else:
                    return redirect(url_for('completar_trabajo', nombre=username, indice=0))
            else:
                flash("Invalid password...")
                return render_template('auth/login.html')
        else:
            flash("User not found...")
            return render_template('auth/login.html')
    else:
        return render_template('auth/login.html')
    
@app.route('/selector')
def selector():
    if current_user.username != 'Vaello':
        return redirect(url_for('storage', nombre=current_user.username))

    empresas_raw = db.session.query(User.username).distinct().all()
    conteos = (
        db.session.query(
            Pedido.nombreproveedor,
            func.sum(case((Pedido.estadopedido == 'En curso', 1), else_=0)).label('en_curso'),
            func.sum(case((Pedido.estadopedido == 'Pendiente', 1), else_=0)).label('pendientes')
        )
        .group_by(Pedido.nombreproveedor)
        .all()
    )
    conteos_map = {
        nombre: {
            'en_curso': en_curso or 0,
            'pendientes': pendientes or 0
        }
        for nombre, en_curso, pendientes in conteos
    }
    empresas = []

    for empresa_row in empresas_raw:
        nombre = empresa_row[0]
        if nombre == 'Vaello':
            continue

        resumen = conteos_map.get(nombre, {'en_curso': 0, 'pendientes': 0})
        empresas.append({
            'nombreproveedor': nombre,
            'en_curso': resumen['en_curso'],
            'pendientes': resumen['pendientes']
        })

    return render_template('storage.html', nombre=empresas)

@app.route('/alta')
def alta():
    users = User.query.all()  # obtiene todos los usuarios de la tabla
    return render_template('alta.html', users=users)

@app.route("/add_tallas/<nombre>", methods=["GET", "POST"])
def add_tallas(nombre):
    marcas = Marcas.query.order_by(Marcas.nombre).all()
    return render_template("tallas.html", nombre=nombre, marcas=marcas)

@app.route("/add_marca", methods=["POST"])
def add_marca():
    nombre = request.form.get("nombre_marca").strip()

    if nombre:
        nueva = Marcas(nombre=nombre)
        db.session.add(nueva)
        db.session.commit()

    return redirect(request.referrer)

@app.route("/add_talla", methods=["POST"])
def add_talla():
    data = request.json
    talla = data.get("talla")
    idmarca = data.get("idmarca")

    if talla and idmarca:
        nueva = Tallas(talla=talla, idmarca=idmarca)
        db.session.add(nueva)
        db.session.commit()
        return {"ok": True}

    return {"ok": False}, 400




@app.route('/add_user', methods=['POST'])
@login_required
def add_user():
    username = request.form['username']
    fullname = request.form.get('fullname')
    email = request.form.get('email')
    password = request.form['password']

    # Cifrar la contraseña antes de guardar (buena práctica)
    hashed_password = generate_password_hash(password)

    # Crear nuevo usuario
    new_user = User(username=username, fullname=fullname, email=email, password=hashed_password)

    # Guardar en la BD
    db.session.add(new_user)
    db.session.commit()

    flash('Usuario añadido correctamente.', 'success')
    return redirect(url_for('alta'))


        

from flask import session

@app.route('/completartrabajo/<nombre>', methods=['GET','POST'])
def completar_trabajo(nombre):
    
    token = request.args.get("token") or request.form.get("token")

    user = User.query.filter_by(username=nombre).first()

    if not user or not validate_client_access(user, token):
        abort(403)

    if request.method == "POST":

        pedidos = Pedido.query.filter(
            Pedido.estadopedido != "Finalizado",
            Pedido.nombreproveedor == nombre
        ).all()

        for pedido in pedidos:

            hechos = request.form.get(f"hechos_{pedido.id}")

            if hechos is not None:

                hechos = int(hechos)

                if hechos != pedido.numerohechos:

                    pedido.numerohechos = hechos
                    pedido.fechaactualizacion = datetime.now()

                    if hechos >= pedido.numerototal:
                        pedido.estadopedido = "Finalizado"
                        pedido.fechafinalizacion = datetime.now()
                    else:
                        pedido.estadopedido = "En curso"

        db.session.commit()

        return redirect(url_for('storage', nombre=nombre))


    pedidos = (
        Pedido.query
        .filter(
            Pedido.estadopedido != "Finalizado",
            Pedido.nombreproveedor == nombre
        )
        .order_by(Pedido.proceso, Pedido.idpedido)
        .all()
    )

    procesos = {}

    for p in pedidos:

        proceso = p.proceso or "Sin proceso"

        if proceso not in procesos:
            procesos[proceso] = []

        procesos[proceso].append(p)

    return render_template(
        "completar_trabajo.html",
        procesos=procesos,
        nombre=nombre,
        token=token
    )


@app.route('/cliente/<nombre>')
@login_required
def storage(nombre):
    
    token = request.args.get("token")
    user = User.query.filter_by(username=nombre).first()
    if not user or not validate_client_access(user, token):
        abort(403)

    # Obtener filtros de la URL
    filter_articulo = request.args.get('filter_articulo', '').strip()
    filter_idpedido = request.args.get('filter_idpedido', '').strip()
    filter_transporte = request.args.get('filter_transporte', '').strip()
    filter_proveedor = request.args.get('filter_proveedor', '').strip()

    # Consulta base
    usuarios = db.session.query(User.username).distinct().all()
    usuarios_js = [u.username for u in usuarios if u.username != 'Vaello']

    # Subconsulta para obtener la última fecha por idpedido
    query = Pedido.query
    # Consulta principal: unir con la subconsulta para obtener el registro más reciente
    if nombre == "Vaello":
        query = query
    else:
        query = query.filter(Pedido.nombreproveedor == nombre)

    # Aplicar filtros
    if filter_articulo:
        query = query.filter(Pedido.articulo.ilike(f"%{filter_articulo}%"))

    if filter_idpedido:
        query = query.filter(Pedido.idpedido.ilike(f"%{filter_idpedido}%"))

    if filter_transporte:
        query = query.filter(Pedido.transporte.ilike(f"%{filter_transporte}%"))

    if filter_proveedor:
        query = query.filter(Pedido.nombreproveedor == filter_proveedor)
        
    estado_order = case(
            (Pedido.estadopedido == "En curso", 1),
            (Pedido.estadopedido == "Pendiente", 2),
            (Pedido.estadopedido == "Finalizado", 3),
            else_=4
        )

    # Ordenar por fecha (si existe el campo)
    query = query.order_by(estado_order.asc(), Pedido.fechaalta.asc())

    data = query.all()

    # -----------------------------
    # AGRUPAR POR IDPEDIDO Y PROCESO
    # -----------------------------
    pedidos_dict = {}

    for p in data:

        key = f"{p.idpedido}_{p.proceso}"   # AGRUPACIÓN POR ID + PROCESO

        if key not in pedidos_dict:
            pedidos_dict[key] = {
                "info": p,
                "tallas": []
            }

        pedidos_dict[key]["tallas"].append(p)

    pedidos = list(pedidos_dict.values())
    marcas = Marcas.query.order_by(Marcas.nombre).all()
    marcas_json = [{"idmarca": m.idmarca, "nombre": m.nombre} for m in marcas]

    return render_template(
    "storage.html",
    pedidos=pedidos,
    nombre=nombre,
    usuarios=usuarios_js,
    marcas=marcas_json
)

@app.route("/tallas/<int:idmarca>")
def get_tallas(idmarca):

    tallas = Tallas.query.filter_by(idmarca=idmarca).all()

    return jsonify([
        {
            "id": t.id,
            "talla": t.talla
        }
        for t in tallas
    ])


@app.route("/delete_marca/<int:idmarca>", methods=["POST"])
def delete_marca(idmarca):
    marca = Marcas.query.get_or_404(idmarca)

    # Eliminar primero sus tallas
    Tallas.query.filter_by(idmarca=idmarca).delete()

    db.session.delete(marca)
    db.session.commit()

    return {"ok": True}


@app.route("/delete_talla/<int:idtalla>", methods=["POST"])
def delete_talla(idtalla):
    talla = Tallas.query.get_or_404(idtalla)

    db.session.delete(talla)
    db.session.commit()

    return {"ok": True}

@app.route("/delete_user/<int:id>", methods=["POST"])
def delete_user(id):
    user = User.query.get_or_404(id)

    db.session.delete(user)
    db.session.commit()

    return {"ok": True}

@app.route("/update_all/<nombre>", methods=['POST'])
@login_required
def update_all(nombre):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # ------------------ FILAS NUEVAS -----------------
    ids_pedidos_new = request.form.getlist("idPedido_new")
    procesos_new = request.form.getlist("proceso_new")
    nombres_new = request.form.getlist("nombre_new")
    nombresPedidos_new = request.form.getlist("nombrePedido_new")
    estados_new = request.form.getlist("estado_new")
    hechos_new = request.form.getlist("numerohechos_new")
    totales_new = request.form.getlist("numerototal_new")
    fechasAlta_new = request.form.getlist("fechaAlta_new")
    fechasAct_new = request.form.getlist("fechaActualizacion_new")
    fechasFinal_new = request.form.getlist("fechafinalizacion_new")
    fechasRec_new = request.form.getlist("fecharecogida_new")
    tallas_new = request.form.getlist("talla_new")
    clientes_new = request.form.getlist("cliente_new")
    articulos_new = request.form.getlist("articulo_new")
    observaciones_new = request.form.getlist("observaciones_new")
    transportes_new = request.form.getlist("transporte_new")
    fotos_new = request.files.getlist("fotomodelo_new")

    # Insertar filas nuevas
    for i in range(len(ids_pedidos_new)):
        if ids_pedidos_new[i].strip() or nombres_new[i].strip():
            ruta_foto = None
            file = fotos_new[i] if i < len(fotos_new) else None
            if file and file.filename and allowed_file(file.filename):
                nombre_archivo = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)
                file.save(filepath)
                ruta_foto = f"uploads/{nombre_archivo}"

            nuevo_pedido = Pedido(
                idpedido=ids_pedidos_new[i],
                proceso=procesos_new[i],
                nombreproveedor=nombres_new[i],
                nombrepedido=nombresPedidos_new[i],
                estadopedido=estados_new[i],
                numerohechos=int(hechos_new[i]) if hechos_new[i] else 0,
                numerototal=int(totales_new[i]) if totales_new[i] else 1,
                fechaalta=datetime.fromisoformat(fechasAlta_new[i]) if fechasAlta_new[i] else datetime.now(),
                fechaactualizacion=datetime.fromisoformat(fechasAct_new[i]) if fechasAct_new[i] else datetime.now(),
                fechafinalizacion=datetime.fromisoformat(fechasFinal_new[i]) if fechasFinal_new[i] else None,
                fecharecogida=datetime.fromisoformat(fechasRec_new[i]) if fechasRec_new[i] else None,
                talla=tallas_new[i],
                cliente=clientes_new[i],
                articulo=articulos_new[i],
                observaciones=observaciones_new[i],
                fotomodelo=ruta_foto,
                transporte=transportes_new[i]
            )
            db.session.add(nuevo_pedido)

    # ------------------ ACTUALIZAR FILAS EXISTENTES -----------------
    ids_existentes = set()
    for key in request.form.keys():
        partes = key.split("_")
        if len(partes) > 1 and partes[-1].isdigit():
            ids_existentes.add(partes[-1])

    pedidos_existentes = {
        pedido.id: pedido
        for pedido in Pedido.query.filter(Pedido.id.in_([int(id_num) for id_num in ids_existentes])).all()
    } if ids_existentes else {}
    pedidos_relacionados_map = {}
    grupos_actualizados = set()

    for id_num in ids_existentes:
        pedido_existente = pedidos_existentes.get(int(id_num))
        if not pedido_existente:
            continue

        group_leader_id = request.form.get(f"group_leader_{id_num}", id_num)
        shared_key = group_leader_id if group_leader_id else id_num

        numerohechos = int(request.form.get(f"numerohechos_{id_num}", 0))
        numerototal = int(request.form.get(f"numerototal_{id_num}", 1))

        # FOTO
        file = request.files.get(f"fotomodelo_{id_num}")
        ruta_foto = pedido_existente.fotomodelo

        if file and file.filename and allowed_file(file.filename):
            nombre_archivo = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)
            file.save(filepath)
            ruta_foto = f"uploads/{nombre_archivo}"

        fechafinalizacion = request.form.get(f"fechafinalizacion_{id_num}")
        fecharecogida = request.form.get(f"fecharecogida_{id_num}")

        form_values = {
            "idpedido": request.form.get(f"idpedido_{shared_key}", "").strip(),
            "proceso": request.form.get(f"proceso_{shared_key}", "").strip(),
            "nombreproveedor": request.form.get(f"nombre_{shared_key}", "").strip(),
            "nombrepedido": request.form.get(f"nombrePedido_{shared_key}", "").strip(),
            "estadopedido": request.form.get(f"estado_{shared_key}", "").strip(),
            "numerohechos": numerohechos,
            "numerototal": numerototal,
            "fechafinalizacion": date.fromisoformat(request.form.get(f"fechafinalizacion_{shared_key}")) if request.form.get(f"fechafinalizacion_{shared_key}") else None,
            "fecharecogida": date.fromisoformat(request.form.get(f"fecharecogida_{shared_key}")) if request.form.get(f"fecharecogida_{shared_key}") else None,
            "talla": request.form.get(f"talla_{id_num}", "").strip(),
            "cliente": request.form.get(f"cliente_{shared_key}", "").strip(),
            "articulo": request.form.get(f"articulo_{id_num}", "").strip(),
            "observaciones": request.form.get(f"observaciones_{id_num}", "").strip(),
            "transporte": request.form.get(f"transporte_{id_num}", "").strip(),
            "fotomodelo": ruta_foto
        }

        # Actualizar solo los campos que hayan cambiado
        pedido_existente.numerohechos = form_values["numerohechos"]
        pedido_existente.numerototal = form_values["numerototal"]
        pedido_existente.talla = form_values["talla"]
        pedido_existente.articulo = form_values["articulo"]
        pedido_existente.observaciones = form_values["observaciones"]
        pedido_existente.fotomodelo = form_values["fotomodelo"]
        pedido_existente.fechaactualizacion = datetime.now()

        # -----------------------------
        # ACTUALIZAR CAMPOS COMPARTIDOS
        # -----------------------------
        original_idpedido = request.form.get(f"original_idpedido_{id_num}", pedido_existente.idpedido or "").strip()
        original_proceso = request.form.get(f"original_proceso_{id_num}", pedido_existente.proceso or "").strip()
        group_identity = (shared_key, original_idpedido, original_proceso)

        if group_identity not in grupos_actualizados:
            pedidos_mismo_grupo = pedidos_relacionados_map.get((original_idpedido, original_proceso))
            if pedidos_mismo_grupo is None:
                pedidos_mismo_grupo = (
                    Pedido.query
                    .filter(
                        Pedido.idpedido == original_idpedido,
                        func.coalesce(Pedido.proceso, '') == original_proceso
                    )
                    .all()
                )
                pedidos_relacionados_map[(original_idpedido, original_proceso)] = pedidos_mismo_grupo

            for p in pedidos_mismo_grupo:
                p.idpedido = form_values["idpedido"]
                p.proceso = form_values["proceso"]
                p.nombreproveedor = form_values["nombreproveedor"]
                p.nombrepedido = form_values["nombrepedido"]
                p.estadopedido = form_values["estadopedido"]
                p.cliente = form_values["cliente"]
                p.transporte = form_values["transporte"]
                p.fechafinalizacion = form_values["fechafinalizacion"]
                p.fecharecogida = form_values["fecharecogida"]
                p.fechaactualizacion = datetime.now()

            grupos_actualizados.add(group_identity)

    db.session.commit()
    return redirect(url_for('storage', nombre=nombre))



@app.route("/update_pedido/<int:id>", methods=["POST"])
@login_required
def update_pedido(id):

    pedido = Pedido.query.get_or_404(id)
    pedido_group_id = request.form.get("pedido_group_id")
    original_idpedido = request.form.get("original_idpedido", pedido.idpedido or "").strip()
    original_proceso = request.form.get("original_proceso", pedido.proceso or "").strip()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    pedido.idpedido = request.form.get("idpedido") or pedido.idpedido
    pedido.nombreproveedor = request.form.get("nombreproveedor") or pedido.nombreproveedor
    pedido.proceso = request.form.get("proceso") or pedido.proceso
    pedido.estadopedido = request.form.get("estadopedido") or pedido.estadopedido
    pedido.numerohechos = int(request.form.get("numerohechos") or 0)
    pedido.numerototal = int(request.form.get("numerototal") or 1)
    pedido.nombrepedido = request.form.get("nombrepedido") or pedido.nombrepedido

    fechafinalizacion = request.form.get("fechafinalizacion")
    fecharecogida = request.form.get("fecharecogida")

    pedido.fechafinalizacion = date.fromisoformat(fechafinalizacion) if fechafinalizacion else None
    pedido.fecharecogida = date.fromisoformat(fecharecogida) if fecharecogida else None

    pedido.talla = request.form.get("talla") or pedido.talla
    pedido.cliente = request.form.get("cliente") or pedido.cliente
    pedido.articulo = request.form.get("articulo") or pedido.articulo
    pedido.observaciones = request.form.get("observaciones") or pedido.observaciones
    pedido.transporte = request.form.get("transporte") or pedido.transporte

    pedido.fechaactualizacion = datetime.now()

    # FOTO
    file = request.files.get("fotomodelo")

    if file and file.filename and allowed_file(file.filename):

        nombre_archivo = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)

        file.save(filepath)

        pedido.fotomodelo = f"uploads/{nombre_archivo}"

    if pedido_group_id:
        pedidos_relacionados = (
            Pedido.query
            .filter(
                Pedido.idpedido == original_idpedido,
                func.coalesce(Pedido.proceso, '') == original_proceso
            )
            .all()
        )

        for p in pedidos_relacionados:
            if p.id == pedido.id:
                continue

            p.idpedido = pedido.idpedido
            p.proceso = pedido.proceso
            p.nombreproveedor = pedido.nombreproveedor
            p.nombrepedido = pedido.nombrepedido
            p.estadopedido = pedido.estadopedido
            p.cliente = pedido.cliente
            p.transporte = pedido.transporte
            p.fechafinalizacion = pedido.fechafinalizacion
            p.fecharecogida = pedido.fecharecogida
            p.fechaactualizacion = pedido.fechaactualizacion

    db.session.commit()

    return {"success": True, "fotomodelo": pedido.fotomodelo}

@app.route("/create_pedido", methods=["POST"])
@login_required
def create_pedido():
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    file = request.files.get("fotomodelo")
    ruta_foto = None

    if file and file.filename and allowed_file(file.filename):
        nombre_archivo = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)
        file.save(filepath)
        ruta_foto = f"uploads/{nombre_archivo}"

    fecha_alta = request.form.get("fechaalta")
    fecha_actualizacion = request.form.get("fechaactualizacion")
    fecha_finalizacion = request.form.get("fechafinalizacion")
    fecha_recogida = request.form.get("fecharecogida")

    nuevo_pedido = Pedido(
        idpedido=request.form.get("idpedido", "").strip(),
        proceso=request.form.get("proceso", "").strip(),
        nombreproveedor=request.form.get("nombreproveedor", "").strip(),
        nombrepedido=request.form.get("nombrepedido", "").strip(),
        estadopedido=request.form.get("estadopedido", "").strip(),
        numerohechos=int(request.form.get("numerohechos") or 0),
        numerototal=int(request.form.get("numerototal") or 1),
        fechaalta=datetime.fromisoformat(fecha_alta) if fecha_alta else datetime.now(),
        fechaactualizacion=datetime.fromisoformat(fecha_actualizacion) if fecha_actualizacion else datetime.now(),
        fechafinalizacion=date.fromisoformat(fecha_finalizacion) if fecha_finalizacion else None,
        fecharecogida=date.fromisoformat(fecha_recogida) if fecha_recogida else None,
        talla=request.form.get("talla", "").strip(),
        cliente=request.form.get("cliente", "").strip(),
        articulo=request.form.get("articulo", "").strip(),
        observaciones=request.form.get("observaciones", "").strip(),
        fotomodelo=ruta_foto,
        transporte=request.form.get("transporte", "").strip()
    )

    db.session.add(nuevo_pedido)
    db.session.commit()

    return {
        "success": True,
        "id": nuevo_pedido.id,
        "fotomodelo": nuevo_pedido.fotomodelo
    }

@app.route("/graficos/<nombre>")
def graficos(nombre):

    # -------------------------
    # FECHA LÍMITE (30 días)
    # -------------------------
    hoy = datetime.now()
    hace_30_dias = hoy - timedelta(days=30)

    # ==========================================================
    # 📊 GRÁFICO 1
    # IDPEDIDO distintos sin actualización en últimos 30 días
    # ==========================================================

    subquery_ultima_actualizacion = (
        db.session.query(
            Pedido.idpedido,
            func.max(Pedido.fechaactualizacion).label("ultima_fecha")
        )
        .group_by(Pedido.idpedido)
        .subquery()
    )

    resultado_proveedor = (
        db.session.query(
            Pedido.nombreproveedor,
            func.count(func.distinct(Pedido.idpedido))
        )
        .join(
            subquery_ultima_actualizacion,
            Pedido.idpedido == subquery_ultima_actualizacion.c.idpedido
        )
        .filter(
            (subquery_ultima_actualizacion.c.ultima_fecha == None) |
            (subquery_ultima_actualizacion.c.ultima_fecha < hace_30_dias)
        )
        .group_by(Pedido.nombreproveedor)
        .all()
    )

    proveedores = [r[0] for r in resultado_proveedor]
    pedidos_atrasados = [r[1] for r in resultado_proveedor]

    # -----------------------------
    # GRÁFICO 2 → SOLO EN CURSO / FINALIZADA
    # -----------------------------

    subquery = (
        db.session.query(
            Pedido.idpedido,
            func.max(Pedido.fechaactualizacion).label("max_fecha")
        )
        .group_by(Pedido.idpedido)
        .subquery()
    )

    estados_interes = ["En curso", "Finalizada", "Finalizado"]

    resultados = (
        db.session.query(
            Pedido.nombreproveedor,
            Pedido.estadopedido,
            func.count(Pedido.idpedido)
        )
        .join(
            subquery,
            (Pedido.idpedido == subquery.c.idpedido) &
            (Pedido.fechaactualizacion == subquery.c.max_fecha)
        )
        .filter(Pedido.estadopedido.in_(estados_interes))
        .group_by(Pedido.nombreproveedor, Pedido.estadopedido)
        .all()
    )

    proveedores_estado = sorted({r[0] for r in resultados})
    estados = ["En curso", "Finalizada"]

    data_por_estado = {
        estado: [0] * len(proveedores_estado)
        for estado in estados
    }

    for proveedor, estado, cantidad in resultados:
        if estado == "Finalizado":
            estado = "Finalizada"  # normalizamos
        i = proveedores_estado.index(proveedor)
        data_por_estado[estado][i] = cantidad

    datasets_estado = [
        {
            "label": "En curso",
            "data": data_por_estado["En curso"],
            "backgroundColor": "#00205B"
        },
        {
            "label": "Finalizada",
            "data": data_por_estado["Finalizada"],
            "backgroundColor": "#2ECC46"
        }
    ]

    return render_template(
        "graficos.html",
        proveedores=proveedores,
        pedidos_atrasados=pedidos_atrasados,
        proveedores_estado=proveedores_estado,
        datasets_estado=datasets_estado
    )

    
    





if __name__ == '__main__':
    app.config.from_object(config['development'])  # Primero cargar config
    csrf.init_app(app)
    app.run()
