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
        # Register
        # post without any data
        resp = self.client.post(
            url_for('users.register'), data=json.dumps(None), headers=credentials,
            content_type='application/json')
        assert resp.status_code == 409

        # post a non-json format
        data = dict(username='foo', email='foo@bar.baz', password='foo', active=False)
        resp = self.client.post(
            url_for('users.register'), data=data, headers=credentials,
            content_type='application/json')
        assert resp.status_code == 400

        # post all required fields for the user
        data = dict(username='foo', email='foo@bar.baz', password='foo', force=True)
        resp = self.client.post(
            url_for('users.register'), data=json.dumps(data), headers=credentials,
            content_type='application/json')
        assert resp.status_code == 201
        assert 'self_url' in resp.json.keys()

        # does the user created have been commited to the database?
        user = User.query.filter_by(username='foo').first()
        assert user.email == data['email']
        assert user.is_confirmed() is False

        # create this user credentials
        token = user.generate_auth_token()
        user_credentials = dict(Authorization='Bearer {}'.format(token))

        # verify that the password have been serialized before storing in the database
        assert user.password != 'foo'
        assert user.verify_password(data['password']) is True

        # try to register a user with existing username
        data = dict(username='foo', email='anotheruser@bar.baz', password='foo')
        resp = self.client.post(
            url_for('users.register'), data=json.dumps(data), headers=credentials,
            content_type='application/json')
        assert resp.status_code == 409
        assert resp.get_json()['message'] == 'username already exists in the database'

        # Read
        # try to read the user with normal credentials
        resp = self.client.get(url_for('users.read', id=user.id), headers=credentials)
        assert resp.status_code == 403

        # now read with this user himself
        resp = self.client.get(url_for('users.read', id=user.id), headers=user_credentials)
        assert resp.status_code == 200
        assert resp.get_json()['username'] == user.username

        # now read with the superuser
        resp = self.client.get(url_for('users.read', id=user.id), headers=super_credentials)
        assert resp.status_code == 200
        assert resp.get_json()['username'] == user.username

        # Update
        # try to update user with normal credentials
        data = dict(username='other', email='other@bar.baz', password='other')
        resp = self.client.put(
            url_for('users.update', id=user.id), data=json.dumps(data), headers=credentials,
            content_type='application/json')
        assert resp.status_code == 403

        # now you can update a user only if you are that user or superuser
        data = dict(username='other', password='other')
        resp = self.client.put(
            url_for('users.update', id=user.id), data=json.dumps(data),
            headers=user_credentials, content_type='application/json')
        assert resp.status_code == 200

        data = dict(username='another', email='another@bar.baz', password='another')
        resp = self.client.put(
            url_for('users.update', id=user.id), data=json.dumps(data),
            headers=super_credentials, content_type='application/json')
        assert resp.status_code == 200

        # Delete
        # try to delete user with normal credentials
        resp = self.client.delete(
            url_for('users.delete', id=user.id), headers=credentials,
            content_type='application/json')
        assert resp.status_code == 403

        # now you can delete a user with superuser
        resp = self.client.delete(
            url_for('users.delete', id=user.id), headers=super_credentials,
            content_type='application/json')
        assert resp.status_code == 204

        resp = self.client.get(
            url_for('users.read', id=user.id), headers=credentials,
            content_type='application/json')
        assert resp.status_code == 404

        # List
        # try to list users with normal credentials
        resp = self.client.get(
            url_for('users.list'), headers=credentials, content_type='application/json')
        assert resp.status_code == 403

        # now list users being a superuser
        resp = self.client.get(
            url_for('users.list'), headers=super_credentials,
            content_type='application/json')
        assert resp.status_code == 200
        assert len(resp.get_json()['users']) == 2
        assert '/users/1' in resp.get_json()['users'][0]

        # listing users with expanded parameter and see if we can access elements of user
        resp = self.client.get(
            url_for('users.list', expanded=1), headers=super_credentials,
            content_type='application/json')
        assert resp.status_code == 200
        assert len(resp.get_json()['users']) == 2
        assert '/users/1' in resp.get_json()['users'][0]['self_url']

        # add an extra user who is in active
        inactive = User(
            username='inactive', email='inactive@foo.bar', password='inactive', active=False)
        inactive.save()

        # the number of users listed should remain 2
        resp = self.client.get(
            url_for('users.list'), headers=super_credentials,
            content_type='application/json')
        assert resp.status_code == 200
        assert len(resp.get_json()['users']) == 2

        # test __repr__
        assert 'User' in str(user)

        # Get token
        # try to access token with a wrong HTTP method e.g. PATCH
        resp = self.client.patch(url_for('users.get_token'), content_type='application/json')
        assert resp.status_code == 405

        # try to get token with a wrong user
        auth = base64.b64encode(b'wronguser:wronguser').decode('utf-8')
        creds = {'Authorization': 'Basic {}'.format(auth)}
        resp = self.client.get(
            url_for('users.get_token'), headers=creds, content_type='application/json')
        assert resp.status_code == 401

        # get_token for authenticated user
        auth = base64.b64encode(b'user:user').decode('utf-8')
        creds = {'Authorization': 'Basic {}'.format(auth)}
        resp = self.client.get(
            url_for('users.get_token'), headers=creds, content_type='application/json')
        assert resp.status_code == 200

        # Refresh token
        # first lets store the first token before refreshing
        old_token = resp.get_json()['token']

        resp = self.client.get(
            url_for('users.refresh_token'), headers=creds, content_type='application/json')
        assert resp.status_code == 200
        assert resp.get_json()['token'] != old_token
        revoked_token = RevokedToken.query.filter_by(token=old_token).first()
        assert revoked_token.token == old_token
        assert revoked_token is not None

        # Registration
        # post all required fields for the user
        data = dict(username='foo', email='foo@bar.baz', password='foo', force=True)
        resp = self.client.post(
            url_for('users.register'), data=json.dumps(data),
            content_type='application/json')
        assert resp.status_code == 201
        assert 'self_url' in resp.json.keys()

        user = User.query.filter_by(username='foo').first()
        profile = Profile.query.filter_by(user_id=user.id).first()
        assert profile.user_id == user.id

        wallet = Wallet.query.filter_by(account_id=user.id).first()
        assert wallet.account_id == user.id

        # Confirmation
        # use a wrong token
        token = 'wrongtokenindeed'
        resp = self.client.get(
            url_for('users.confirm', token=token), headers=super_credentials,
            content_type='application/json')
        assert resp.status_code == 404

        # use a valid token
        token = user.generate_confirmation_token()
        resp = self.client.get(
            url_for('users.confirm', token=token), headers=super_credentials,
            content_type='application/json')
        assert resp.status_code == 200
        assert resp.get_json()['message'] == 'your account is now confirmed'

        # use a valid token for the second time
        resp = self.client.get(
            url_for('users.confirm', token=token), headers=super_credentials,
            content_type='application/json')
        assert resp.status_code == 200
        assert resp.get_json()['message'] == 'account already confirmed. Proceed to login'

        def mock_verification(token):
            secret_key = app.config.get('SECRET_KEY')
            salt = app.config.get('SECURITY_PASSWORD_SALT')
            s = URLSafeTimedSerializer(secret_key)
            return s.loads(token, salt=salt, max_age=0.5)

        monkeypatch.setattr(User, 'verify_confirmation_token', mock_verification)
        time.sleep(1)
        resp = confirm(token).to_response()
        assert resp.status_code == 200
        assert resp.get_json()['message'] == 'the confirmation link has expired'

        # Forgot password
        data = dict(email='foo@bar')
        resp = self.client.post(
            url_for('users.forgot'), data=json.dumps(data), content_type='application/json')
        assert resp.status_code == 409
        assert 'expected an Email' in resp.get_json()['message']

        data = dict(email='foo@bar.baz')
        resp = self.client.post(
            url_for('users.forgot'), data=json.dumps(data), content_type='application/json')
        assert resp.status_code == 200
        assert resp.get_json()['message'] == 'a recovery link has been sent via email'

        # Recovery
        # use a wrong token
        token = 'wrongtokenindeed'
        data = dict()
        resp = self.client.put(
            url_for('users.recovery', token=token), data=json.dumps(data),
            headers=super_credentials, content_type='application/json')
        assert resp.status_code == 409

        token = 'wrongtokenindeed'
        data = dict(password='foo', confirm_password='bar')
        resp = self.client.put(
            url_for('users.recovery', token=token), data=json.dumps(data),
            content_type='application/json')
        assert resp.status_code == 409
        assert 'password and confirm password must match' in resp.get_json()['message']

        # use a valid token
        token = user.generate_confirmation_token()
        data = dict(password='foo', confirm_password='foo')
        resp = self.client.put(
            url_for('users.recovery', token=token), data=json.dumps(data),
            content_type='application/json')
        assert resp.status_code == 200
        assert resp.get_json()['message'] == 'your account coordinates are up-to-date'

        def mock_recovery(token):
            secret_key = app.config.get('SECRET_KEY')
            salt = app.config.get('SECURITY_PASSWORD_SALT')
            s = URLSafeTimedSerializer(secret_key)
            return s.loads(token, salt=salt, max_age=0.5)

        monkeypatch.setattr(User, 'verify_confirmation_token', mock_recovery)
        time.sleep(1)
        resp = recovery(token).to_response()
        assert resp.status_code == 200
        assert resp.get_json()['message'] == 'the recovery link has expired'

        # User information
        # balance
        token = user.generate_auth_token()
        user_credentials = {'Authorization': 'Bearer {}'.format(token)}
        resp = self.client.get(
            url_for('users.balance', id=user.id), headers=user_credentials,
            content_type='application/json')
        assert resp.status_code == 200
        assert resp.get_json()['amount'] == 2.0

        # check emty sms
        sms = SMS.query.filter_by(account_id=user.id).all()
        assert len(sms) == 0

        # create an sms
        country = Country(name='Rwanda', mcc='635', region_code='RW', country_code=250)
        country.save()
        telco = Telco(name='MTN', mnc='10', country_id=country.id)
        telco.save()
        sms = SMS(
            to='+250785383100', text='Hello Remy', sender='Pindo', telco_id=telco.id,
            account_id=user.id)
        sms.report_id = '1900990910920'
        sms.save()
        assert len(user.sms.all()) != 0

        # Update DLR
        data = {'id': sms.report_id, 'id_smsc': 'ACDDG-SDSF', 'message_status': 'DELIVRD',
                'level': 3, 'sub': 1, 'subdate': '1902111200', 'donedate': '1902111200',
                'dlvrd': '001', 'err': '000'}
        resp = self.client.post(url_for('sms_v1.update_from_dlr'), data=json.dumps(data),
                                headers=super_credentials, content_type='text/html')
        assert resp.status_code == 200

        # list sms
        resp = self.client.get(
            url_for('users.list_sms', id=user.id), headers=user_credentials,
            content_type='application/json')
        assert resp.status_code == 200
        assert resp.get_json()['pages']['total'] == 1

        # custom range usage
        resp = self.client.get(
            url_for('users.usage', id=user.id, days=10), headers=user_credentials,
            content_type='application/json')
        start = (date.today() - timedelta(days=10)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        end = (date.today() + timedelta(days=1)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        assert resp.status_code == 200
        assert resp.get_json()['days'] == 10
        assert resp.get_json()['sms_count'] == 1
        assert resp.get_json()['delivered'] == 1
        assert resp.get_json()['expired'] == 0
        assert resp.get_json()['undelivered'] == 0
        assert resp.get_json()['from'] == start
        assert resp.get_json()['to'] == end

        # when the range is not provided
        resp = self.client.get(
            url_for('users.usage', id=user.id), headers=user_credentials,
            content_type='application/json')
        assert resp.status_code == 200
        start = (date.today() - timedelta(days=7)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        end = (date.today() + timedelta(days=1)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        assert resp.status_code == 200
        assert resp.get_json()['days'] == 7
        assert resp.get_json()['from'] == start
        assert resp.get_json()['to'] == end

        # test send task email
        with mail.record_messages() as outbox:
            send_usage()
            assert len(outbox) == 1

        # test async usage
        task = async_send_usage_email.apply_async()
        assert task.status == 'SUCCESS'
