from flask_sqlalchemy import SQLAlchemy

class Config:
    SECRET_KEY = 'Bioweh??3jiqwgf2'
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Para evitar warnings

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "postgresql://usuario:minueva123@localhost/datosweb_utf8"


config = {
    'development': DevelopmentConfig
}
