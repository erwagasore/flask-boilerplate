from celery import Celery
from sqlalchemy import MetaData

from flask_sqlalchemy import SQLAlchemy, BaseQuery
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
from flask_bouncer import Bouncer

from app.config import Base


convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}


class ActiveQuery(BaseQuery):
    def all(self):
        return list(self.from_self().filter_by(active=True))


# instantiate the extension
db = SQLAlchemy(query_class=ActiveQuery, metadata=MetaData(naming_convention=convention))
migrate = Migrate()
bcrypt = Bcrypt()
auth = HTTPBasicAuth()
token = HTTPTokenAuth()
bouncer = Bouncer()
celery = Celery(__name__, broker=Base.CELERY_BROKER_URL)


def init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    CORS(app)
    bouncer.init_app(app)
    celery.conf.update(app.config)
