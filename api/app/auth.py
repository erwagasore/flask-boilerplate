from flask import current_app, g
from flask_bouncer import MANAGE, CREATE, READ, UPDATE, ALL

from app.errorhandlers import unauthorized
from app.extensions import auth, token, bouncer
from app.awaremodel import User
from app.users.models import RevokedToken


@auth.verify_password
def verify_password(username, password):
    ignore_auth = current_app.config.get('IGNORE_AUTH', False)
    g.user = User.query.get(1) if ignore_auth else User.query.filter_by(
        username=username).first()
    if g.user is not None:
        return ignore_auth or g.user.verify_password(password)
    else:
        return False


@token.verify_token
def verify_token(token):
    ignore_auth = current_app.config.get('IGNORE_AUTH', False)
    g.user = User.query.get(1) if ignore_auth else User.verify_auth_token(token)

    if g.user is None:
        return False

    revoked = RevokedToken.get_revoked(g.user)
    return token not in [_.token for _ in revoked]


@auth.error_handler
def auth_unauthorized():
    return unauthorized()


@token.error_handler
def token_unauthorized():
    return unauthorized()


@bouncer.authorization_method
def define_authorization(user, they):
    if user.is_super():
        # User, Profile, Country, Telco, Deal, SMS, Transaction and Wallet
        they.can(MANAGE, ALL)
        they.cannot(CREATE, 'SMS')
    else:
        def is_creator(item):
            return item.created_by == user

        def is_owner(item):
            return item.account == user

        def is_self(item):
            return item == user

        # User
        they.can((READ, UPDATE), 'User', is_self)

        # add more permissions here
