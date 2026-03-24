from .entities.UserOnline import UserOnline


class ModelUserOnline:

    @classmethod
    def login(cls, username, password):
        try:
            user = UserOnline.query.filter_by(username=username).first()
            if user and UserOnline.check_password(user.password, password):
                return user
            return None
        except Exception as ex:
            raise Exception(f"Error en login: {ex}")

    @classmethod
    def get_by_id(cls, id):
        try:
            return UserOnline.query.get(int(id))
        except Exception as ex:
            raise Exception(f"Error en get_by_id: {ex}")
