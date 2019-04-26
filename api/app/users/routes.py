from flask import request, g
from flask_bouncer import requires, ensure

from app.auth import auth, token
from app.factory import APIResult
from app.awaremodel import User
from app.decorators import validate_with, paginate
from app.constants import CREATE, READ, UPDATE, DELETE, LIST

from app.users import users
from app.users.models import RevokedToken
from app.users.schema import create_user, update_user


@users.route('/', methods=['POST'])
@requires(CREATE, User)
@validate_with(create_user)
def create():
    user = User()
    user.import_data(request.method, request.get_json())
    user.save()
    return APIResult({'self_url': user.get_url()}, 201, Link=user.get_url())


@users.route('/<int:id>', methods=['GET'])
@token.login_required
@requires(READ, User)
def read(id):
    user = User.query.get_or_404(id)
    ensure(READ, user)
    return APIResult(user.export_data())


@users.route('/token')
@auth.login_required
@requires(READ, User)
def get_token():
    return APIResult({'token': g.user.generate_auth_token()})


@users.route('/refresh/token')
@auth.login_required
@requires(UPDATE, User)
def refresh_token():
    user = g.user
    # revoke the current_token by adding in revoked-tokens
    revoked_token = RevokedToken(token=user.generate_auth_token(), user_id=user.id)
    revoked_token.save()
    # increment the user revoked_count
    user.revoked_token_count += 1
    user.save()
    # re-generate the new token
    return APIResult({'token': user.generate_auth_token()})


@users.route('/<int:id>', methods=['PUT'])
@token.login_required
@requires(UPDATE, User)
@validate_with(update_user)
def update(id):
    user = User.query.get_or_404(id)
    ensure(UPDATE, user)
    user.import_data(request.method, request.get_json())
    user.save()
    return APIResult({'self_url': user.get_url()})


@users.route('/<int:id>', methods=['DELETE'])
@token.login_required
@requires(DELETE, User)
def delete(id):
    user = User.query.get_or_404(id)
    ensure(DELETE, user)
    user.remove()
    return APIResult({}, 204)


@users.route('/', methods=['GET'])
@token.login_required
@requires(LIST, User)
@paginate('users')
def list():
    return User.query
