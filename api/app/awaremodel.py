from datetime import datetime
from inflection import tableize
from flask import g, url_for, current_app
from sqlalchemy.sql import expression, sqltypes
from sqlalchemy.event import listens_for
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.declarative import declared_attr
from itsdangerous import JSONWebSignatureSerializer as Serializer, BadSignature
from itsdangerous import URLSafeTimedSerializer

from app.extensions import db, bcrypt


class TablenameGenerator(object):
    """Auto generate tablename from model's name"""
    @declared_attr
    def __tablename__(cls):
        return tableize(cls.__name__)


class utcnow(expression.FunctionElement):
    type = db.DateTime()


@compiles(utcnow, 'postgresql')
def pg_utcnow(element, compiler, **kwargs):
    return "TIMEZONE('utc', CURRENT_TIMESTAMP)"


class Timestamp(object):
    """Give models awareness of time the are created and altered on"""
    created_at = db.Column(db.DateTime, server_default=utcnow())
    modified_at = db.Column(db.DateTime, server_default=utcnow(), onupdate=utcnow())


def get_columns(model):
    return model.__table__.columns


def get_relationships(model):
    return model.__mapper__.relationships


def get_url(obj, **kwargs):
    req = kwargs.pop('request', None)
    extra = kwargs.pop('extra', None)
    extra = '_{}'.format(extra) if extra else ''
    kwargs.update({'id': obj.id, '_external': True})

    if req:
        endpoint = '{}.read{}'.format(req.endpoint.split(".")[0], extra)
    else:
        endpoint = '{}.read{}'.format(obj.__class__.__tablename__, extra)
    return url_for(endpoint, **kwargs)


def import_data(obj, method, data):
    columns = get_columns(obj)
    date_type = (sqltypes.DateTime, sqltypes.Date, sqltypes.Time, sqltypes.TIMESTAMP)
    int_type = (sqltypes.Integer, sqltypes.BigInteger, sqltypes.SmallInteger)
    dec_type = (sqltypes.REAL, sqltypes.DECIMAL, sqltypes.Numeric, sqltypes.Float)

    if method == 'POST':
        required = [_ for _ in columns.keys() if not columns.get(_).nullable]
        for key in set(required).difference(data.keys()):
            setattr(obj, key, None)

    for key in set(data.keys()).intersection(columns.keys()):
        if key == 'password' and hasattr(obj, 'set_password'):
            obj.set_password(data[key])
        elif isinstance(columns.get(key).type, date_type):
            setattr(obj, key, datetime.strptime(data[key], '%Y-%m-%d'))
        elif isinstance(columns.get(key).type, sqltypes.Boolean):
            setattr(obj, key, bool(data[key]))
        elif isinstance(columns.get(key).type, int_type):
            setattr(obj, key, int(data[key]))
        elif isinstance(columns.get(key).type, dec_type):
            setattr(obj, key, float(data[key]))
        else:
            setattr(obj, key, str(data[key]) if len(data[key]) > 0 else None)
    return obj


def export_data(obj, **kwargs):
    data = dict()
    columns = get_columns(obj)
    relationships = get_relationships(obj)
    date_type = (sqltypes.DateTime, sqltypes.Date, sqltypes.Time, sqltypes.TIMESTAMP)
    int_type = (sqltypes.BigInteger, sqltypes.SmallInteger, sqltypes.Integer)
    dec_type = (sqltypes.REAL, sqltypes.DECIMAL, sqltypes.Numeric, sqltypes.Float)

    data['self_url'] = obj.get_url(**kwargs)

    for key in columns.keys():
        if key in obj.IGNORE_FIELDS:
            continue

        # assign null for data without any value
        col_value = getattr(obj, key)
        if col_value is None:
            data[key] = None
            continue

        # check if the column type is datetime and convert to datetime for serialization
        if isinstance(columns.get(key).type, date_type):
            data[key] = col_value.isoformat()
            continue

        if isinstance(columns.get(key).type, sqltypes.Boolean):
            data[key] = str(col_value).lower()
            continue

        if isinstance(columns.get(key).type, int_type):
            data[key] = int(col_value)
            continue

        if isinstance(columns.get(key).type, dec_type):
            data[key] = float(col_value)
            continue

        data[key] = str(col_value)

    for key in relationships.keys():
        req = kwargs.get('request', None)
        if req:
            endpoint = '{}.list_{}'.format(req.endpoint.split('.')[0], key)
        else:
            endpoint = '{}.list_{}'.format(obj.__tablename__, key)
        try:
            data['{}_url'.format(key)] = url_for(endpoint, id=obj.id, _external=True)
        except Exception:
            pass

    return data


class User(db.Model, TablenameGenerator, Timestamp):
    IGNORE_FIELDS = ['id', 'password']

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(127), unique=True, nullable=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True)
    force = db.Column(db.Boolean, default=False)
    confirmed_at = db.Column(db.DateTime)
    last_login_at = db.Column(db.DateTime)
    current_login_at = db.Column(db.DateTime)
    last_login_ip = db.Column(db.String(45))
    current_login_ip = db.Column(db.String(45))
    revoked_token_count = db.Column(db.Integer, default=0)
    login_count = db.Column(db.Integer, default=0)

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, hex(id(self)))

    def save(self):
        db.session.add(self)
        db.session.commit()

    def remove(self):
        db.session.delete(self)
        db.session.commit()

    def is_super(self):
        return self.force

    def is_confirmed(self):
        return bool(self.confirmed_at)

    def get_url(self, request=None):
        return get_url(self, request=request)

    def export_data(self, **kwargs):
        return export_data(self, **kwargs)

    def import_data(self, method, data):
        return import_data(self, method, data)

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def verify_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    def generate_auth_token(self):
        s = Serializer(
            current_app.config['SECRET_KEY'], algorithm_name='none', signer_kwargs={'sep': '&'})
        payload = {'id': self.id, 'revoked_token_count': self.revoked_token_count}
        return s.dumps(payload).decode('utf-8')

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(
            current_app.config['SECRET_KEY'], algorithm_name='none', signer_kwargs={'sep': '&'})
        try:
            data = s.loads(token)
        except BadSignature:
            return None
        return User.query.get(data['id'])

    def generate_confirmation_token(self):
        s = URLSafeTimedSerializer(current_app.config.get('SECRET_KEY'))
        return s.dumps(self.email, salt=current_app.config.get('SECURITY_PASSWORD_SALT'))

    @staticmethod
    def verify_confirmation_token(token, max_age=3600):
        s = URLSafeTimedSerializer(current_app.config.get('SECRET_KEY'))
        try:
            email = s.loads(
                token, salt=current_app.config.get('SECURITY_PASSWORD_SALT'), max_age=max_age)
        except BadSignature:
            return None
        return email


auth_model = User
auth_tablename = auth_model.__tablename__


def _user_or_anon_id():
    return g.user.id if hasattr(g, 'user') else -1


class Agent(object):
    """Give models awareness of the agent of the model instance"""
    @declared_attr
    def created_by_id(cls):
        return db.Column(
            db.Integer,
            db.ForeignKey('{}.id'.format(auth_tablename), onupdate="CASCADE",
                          ondelete="CASCADE", use_alter=True), default=_user_or_anon_id)

    @declared_attr
    def created_by(cls):
        return db.relationship(
            auth_model,
            primaryjoin='{}.id == {}.created_by_id'.format(auth_model.__name__, cls.__name__),
            remote_side='{}.id'.format(auth_model.__name__)
        )

    @declared_attr
    def modified_by_id(cls):
        return db.Column(
            db.Integer,
            db.ForeignKey('{}.id'.format(auth_tablename), onupdate="CASCADE",
                          ondelete="CASCADE", use_alter=True), default=_user_or_anon_id)

    @declared_attr
    def modified_by(cls):
        return db.relationship(
            auth_model,
            primaryjoin='{}.id == {}.modified_by_id'.format(
                auth_model.__name__, cls.__name__),
            remote_side='{}.id'.format(auth_model.__name__)
        )


class AwareModel(db.Model, TablenameGenerator, Timestamp, Agent):
    """A more advanced sqlalchemy based model class with the awareness of itself"""
    __abstract__ = True
    IGNORE_FIELDS = []

    id = db.Column(db.Integer, primary_key=True)
    active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, hex(id(self)))

    def save(self):
        db.session.add(self)
        db.session.commit()

    def remove(self):
        db.session.delete(self)
        db.session.commit()

    def get_url(self, **kwargs):
        return get_url(self, **kwargs)

    def export_data(self, **kwargs):
        return export_data(self, **kwargs)

    def import_data(self, method, data):
        return import_data(self, method, data)


@listens_for(AwareModel, 'before_insert', propagate=True)
def awaremodel_before_insert(mapper, connection, target):
    # When a model with inherited from Awaremodel is created
    # force modified_by to be the logged in user
    target.modified_by_id = _user_or_anon_id()


@listens_for(AwareModel, 'before_update', propagate=True)
def awaremodel_before_update(mapper, connection, target):
    # When a model with inherited from Awaremodel is updated
    # force modified_by to be the logged in user
    target.modified_by_id = _user_or_anon_id()
