from flask import Blueprint


users = Blueprint('users', __name__, url_prefix='/users')
from app.users import routes    # NOQA


@users.before_request
def before_request():
    pass


@users.after_request
def after_request(response):
    return response
