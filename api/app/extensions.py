from flask_bouncer import Bouncer


bouncer = Bouncer()


def init_extensions(app):
    bouncer.init_app(app)
