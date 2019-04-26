import os
from flask import Flask, Response, json
from flask_bouncer import Unauthorized as Forbidden

from app.config import config
from app.extensions import init_extensions
from app.errorhandlers import (
    bad_request, forbidden, not_found, method_not_supported, conflict)


class APIResult():
    """
    Transform flask result into json formatted response
    """
    def __init__(self, value, status=200, **headers):
        self.value = value
        self.status = status
        self.headers = headers

    def to_response(self):
        rv = Response(json.dumps(self.value), status=self.status,
                      mimetype='application/json')
        rv.headers.extend(self.headers)
        return rv


class APIException(Exception):
    """
    Handle exception as an APIResult
    """
    def __init__(self, message, status=400):
        self.message = message
        self.status = status

    def to_result(self):
        error = "conflict" if self.status == 409 else self.message.lower()
        payload = {
            'error': error, 'message': self.message, 'status': self.status
        }
        return APIResult(payload, status=self.status)


class APIFlask(Flask):
    """
    Extend flask to handle APIResult while making response
    """
    def make_response(self, rv):
        if isinstance(rv, APIResult):
            return rv.to_response()
        return Flask.make_response(self, rv)


def create_app(mode=os.environ.get('FLASK_MODE', 'app.config.Development')):
    """
    Flask application instantiation with extensions and blueprints
    """
    app = APIFlask(__name__)
    # add configurations
    app_config = config.get(mode)
    app.config.from_object(app_config)
    app_config().init_app(app)

    # initialize all extensions
    init_extensions(app)

    # register blueprints
    # add blueprint registration statements here
    from app.users import users
    app.register_blueprint(users)

    # register error handlers
    app.register_error_handler(400, bad_request)
    app.register_error_handler(Forbidden, forbidden)
    app.register_error_handler(404, not_found)
    app.register_error_handler(405, method_not_supported)
    app.register_error_handler(APIException, conflict)

    return app
