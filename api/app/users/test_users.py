import time
from datetime import timedelta, date
import base64
import pytest
from flask import url_for, json
from itsdangerous import URLSafeTimedSerializer

from app.extensions import mail
from app.awaremodel import User
from app.profiles.models import Profile
from app.wallets.models import Wallet
from app.sms.models import SMS
from app.telcos.models import Telco
from app.countries.models import Country

from app.users.models import RevokedToken
from app.users.routes import confirm, recovery

from app.tasks.send_usage_email import async_send_usage_email, send_usage


@pytest.mark.usefixtures('client_class')
class TestUsers:

    def test_users_routes(self, app, monkeypatch, celery_app, db_session,
                          credentials, super_credentials):
        pass
