from datetime import datetime

from sqlalchemy import Index

from extensions import db


class PedidoOnline(db.Model):
    __tablename__ = 'pedidos'
    __table_args__ = (
        Index('ix_online_datosweb_idpedido', 'idpedido'),
        Index('ix_online_datosweb_nombreproveedor', 'nombreproveedor'),
        Index('ix_online_datosweb_estadopedido', 'estadopedido'),
        Index('ix_online_datosweb_proceso', 'proceso'),
        Index('ix_online_datosweb_fechaalta', 'fechaalta'),
        Index('ix_online_datosweb_fechaactualizacion', 'fechaactualizacion'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    idpedido = db.Column(db.String(100))
    nombreproveedor = db.Column(db.String(100))
    estadopedido = db.Column(db.String(50))
    numerohechos = db.Column(db.Integer)
    numerototal = db.Column(db.Integer)
    nombrepedido = db.Column(db.String(100))
    fechaactualizacion = db.Column(db.DateTime)
    fechaalta = db.Column(db.DateTime)
    fechafinalizacion = db.Column(db.Date)
    fecharecogida = db.Column(db.Date)
    talla = db.Column(db.String(50))
    cliente = db.Column(db.String(100))
    articulo = db.Column(db.String(100))
    observaciones = db.Column(db.Text)
    fotomodelo = db.Column(db.String(255))
    transporte = db.Column(db.String(100))
    proceso = db.Column(db.String(50))


class MarcasOnline(db.Model):
    __tablename__ = 'marcas'

    idmarca = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    fechasubida = db.Column(db.DateTime, default=datetime.now)

    tallas = db.relationship('TallasOnline', backref='marca', lazy=True)


class TallasOnline(db.Model):
    __tablename__ = 'tallas'

    id = db.Column(db.Integer, primary_key=True)
    talla = db.Column(db.String(50), nullable=False)
    idmarca = db.Column(db.Integer, db.ForeignKey('marcas.idmarca'), nullable=False)
