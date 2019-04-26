import pytest
from datetime import datetime
from flask import g, current_app
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

from app.worker import celery
from app.awaremodel import User
from app.factory import create_app
from app.extensions import db as _db
from app.users.routes import registration_setup


@pytest.fixture(scope='session')
def app(request):
    """
    Flask test application availabe per test session
    """
    _app = create_app('app.config.Testing')
    ctx = _app.app_context()
    ctx.push()
    yield _app
    ctx.pop()


@pytest.fixture(scope='class', autouse=True)
def db(app):
    """
    Test database table creation and cleanup per test session
    """
    _db.app = app
    _db.create_all()
    yield _db
    # proposed drop_all fix for postgres by Mike Bayer
    # http://jrheard.tumblr.com/post/12759432733/dropping-all-tables-on-postgres-using
    _db.reflect()
    _db.drop_all()


@pytest.fixture
def db_session(db, monkeypatch):
    """
    Database session within test function
    """
    conn = db.engine.connect()
    trans = conn.begin()
    # Patch Flask-SQLAlchemy to use our connection
    monkeypatch.setattr(db, 'get_engine', lambda *args: conn)
    yield db.session
    db.session.remove()
    trans.rollback()
    conn.close()


@pytest.fixture
def superuser(db_session):
    """
    Create a superuser
    """
    user = User(username='super', email='super@foo.bar', force=True,
                confirmed_at=datetime.utcnow())
    user.set_password('super')
    g.user = user
    user.save()
    yield User.query.filter_by(username='super').first()
    user.remove()


@pytest.fixture
def super_credentials(superuser):
    """
    Get formatted authentication header based on user fixture for superuser
    """
    token = superuser.generate_auth_token()
    return dict(Authorization='Bearer {}'.format(token))


@pytest.fixture
def user(db_session):
    """
    Returns a user
    """
    user = User(username='user', email='user@foo.bar')
    user.set_password('user')
    g.user = user
    user.save()
    registration_setup(user)
    yield User.query.filter_by(username='user').first()
    user.remove()


@pytest.fixture
def credentials(user):
    """
    Get formatted authentication header based on user fixture
    """
    token = user.generate_auth_token()
    return dict(Authorization='Bearer {}'.format(token))


@pytest.fixture
def fake_credentials():
    """
    Generate a fake credentials
    """
    s = Serializer(current_app.config['SECRET_KEY'], expires_in=3600)
    token = s.dumps({'id': 10}).decode('utf-8')
    return dict(Authorization='Bearer {}'.format(token))


@pytest.fixture
def empty_credentials():
    """
        Empty credentials
    """
    return dict(Authorization='Bearer {}'.format(''))


@pytest.fixture(scope='module')
def celery_app(request):
    celery.conf.update(CELERY_ALWAYS_EAGER=True)
    return celery
