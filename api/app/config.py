import os
from flask.cli import load_dotenv
from celery.schedules import crontab


class Base:
    """
    Base configuration
    """
    PROJECT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    load_dotenv(os.path.join(PROJECT_DIR, '.flaskenv'))

    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY')

    DB = os.environ.get('POSTGRES_DB')
    DB_USER = os.environ.get('POSTGRES_USER')
    DB_PASS = os.environ.get('POSTGRES_PASSWORD')
    DB_HOST = os.environ.get('POSTGRES_HOST')
    DB_TEST_HOST = os.environ.get('POSTGRES_TEST_HOST', 'localhost')
    DB_PORT = os.environ.get('POSTGRES_PORT')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis configuration
    REDIS_URI = 'redis://redis:6379/0'

    # Celery configuration
    CELERY_TASK_STARTED = True
    CELERY_SEND_TASK_ERROR_EMAILS = True
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['application/json']
    CELERY_BROKER_URL = REDIS_URI
    CELERY_RESULT_BACKEND = CELERY_BROKER_URL

    # deal with configuration requiring flask application instance
    def init_app(self, app):
        # e.g. --> app.url_map.strict_slashes = False
        pass


class Development(Base):
    """Development configuration"""
    DEBUG = True
    DB_URI = 'postgresql://{}:{}@{}:{}/{}'.format(
        Base.DB_USER, Base.DB_PASS, Base.DB_HOST, Base.DB_PORT, Base.DB)
    SQLALCHEMY_DATABASE_URI = DB_URI


class Testing(Development):
    """Testing configuration"""
    TESTING = True
    DB_URI = 'postgresql://{}:{}@{}:{}/{}_test'.format(
        Base.DB_USER, Base.DB_PASS, Base.DB_TEST_HOST, Base.DB_PORT, Base.DB
    )
    SQLALCHEMY_DATABASE_URI = DB_URI


class Production(Development):
    """Production configuration"""
    DEBUG = False
    load_dotenv(os.path.join(Base.PROJECT_DIR, '.env'))
    DB_URI = 'postgresql://{}:{}@db:{}/{}'.format(
        Base.DB_USER, Base.DB_PASS, Base.DB_PORT, Base.DB
    )
    SQLALCHEMY_DATABASE_URI = DB_URI


config = {
    'app.config.Development': Development,
    'app.config.Testing': Testing,
    'app.config.Production': Production
}
