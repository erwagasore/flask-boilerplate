#!/usr/bin/env python
from app.factory import create_app
from app.extensions import celery    # NOQA


app = create_app()
app.app_context().push()
