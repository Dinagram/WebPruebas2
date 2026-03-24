from flask_login import UserMixin
from werkzeug.security import check_password_hash

from app.extensions import db


class UserOnline(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    fullname = db.Column(db.String(100))
    email = db.Column(db.String(100))
    reset_token = db.Column(db.String(200), nullable=True)

    def __init__(self, username, password, email, fullname="", reset_token=None):
        self.username = username
        self.password = password
        self.fullname = fullname
        self.email = email
        self.reset_token = reset_token

    @classmethod
    def check_password(cls, hashed_password, password):
        return check_password_hash(hashed_password, password)
