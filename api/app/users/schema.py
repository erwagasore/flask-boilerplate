from voluptuous import Invalid, Schema, Required, Length, All, Email, REMOVE_EXTRA

from app.validators import Exist, DoesntExist
from app.awaremodel import User


create_user = Schema(
    {
        Required('username'): All(str, Length(min=3, max=127), Exist(User, 'username')),
        Required('email'): All(Email(), Exist(User, 'email')),
        Required('password'): All(str, Length(min=3, max=255)),
        'force': bool
    },
    extra=REMOVE_EXTRA
)

update_user = Schema(
    {
        'username': All(str, Length(min=3, max=127), Exist(User, 'username')),
        'email': All(Email(), Exist(User, 'email')),
        'password': All(str, Length(min=3, max=255)),
        'active': bool,
        'force': bool
    },
    extra=REMOVE_EXTRA
)


forgot_user = Schema(
    {
        Required('email'): All(Email(), DoesntExist(User, 'email'))
    },
    extra=REMOVE_EXTRA
)


def password_match(keys):
    if keys['password'] != keys['confirm_password']:
        raise Invalid('password and confirm password must match')
    return keys


recovery_user = Schema(
    All({
        Required('password'): All(str, Length(min=3, max=255)),
        Required('confirm_password'): All(str, Length(min=3, max=255))
    }, password_match),
    extra=REMOVE_EXTRA
)
