import functools
from voluptuous import Invalid
from flask import request

from app.factory import APIException


def validate_with(schema):
    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            try:
                schema(request.get_json())
            except Invalid as e:
                raise APIException("{} {}".format('.'.join(map(str, e.path)), e.msg), 409)
            return f(*args, **kwargs)
        return wrapped
    return decorator
