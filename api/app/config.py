import os

from flask.cli import load_dotenv


class Base:
    """
    Base configurations
    """
    PROJECT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    load_dotenv(os.path.join(PROJECT_DIR, '.flaskenv'))

    TESTING = False
    SQLACHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY')

    def init_app(self, app):
        """
        Initialize configuration requires application instance
        """
        # ignoring slashes on url
        # app.url_map.strict_slashes = False
        pass


class Development(Base):
    """
    Development configurations
    """
    pass


class Testing(Base):
    """
    Testing configurations
    """
    TESTING = True


class Production(Base):
    """
    Production configurations
    """
    DEBUG = False


# expose all configurations as a dictionary
# keys must be their complete namespace
config = {
    'app.config.Development': Development,
    'app.config.Testing': Testing,
    'app.config.Production': Production
}
