from .entities.User import User

class ModelUser:

    @classmethod
    def login(cls, username, password):
        try:
            user = User.query.filter_by(username=username).first()
            if user and User.check_password(user.password, password):
                return user
            return None
        except Exception as ex:
            raise Exception(f"Error en login: {ex}")

    @classmethod
    def get_by_id(cls, id):
        try:
            return User.query.get(int(id))
        except Exception as ex:
            raise Exception(f"Error en get_by_id: {ex}")