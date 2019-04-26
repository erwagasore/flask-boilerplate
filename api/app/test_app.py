import json
import pytest
from flask import url_for

from app import app
from app import test as tst, initdb
from app.factory import APIResult, APIException
from app.awaremodel import User
from app.countries.models import Country
from app.telcos.models import Telco


@pytest.mark.usefixtures('client_class')
class TestApp:
    def test_config(self, config):
        assert config['PROJECT_DIR'].endswith('/api')
        assert config['DB_URI'] == 'postgresql://{}:{}@db-test:{}/{}_test'.format(
            config['DB_USER'], config['DB_PASS'],
            config['DB_PORT'], config['DB']
        )

    def test_api_results(self):
        result = APIResult({'name': 'foo'})
        assert result.status == 200
        assert result.value == {'name': 'foo'}
        assert result.headers == dict()

        response = result.to_response()
        assert response.content_type == 'application/json'
        assert response.status_code == 200
        assert response.data.decode('utf-8') == json.dumps({'name': 'foo'})

        result = APIResult({'name': 'bar'}, status=201, custom_header='lala')
        assert result.status == 201
        assert result.value == {'name': 'bar'}
        assert result.headers == {'custom_header': 'lala'}

        response = result.to_response()
        assert response.content_type == 'application/json'
        assert response.status_code == 201
        assert response.data.decode('utf-8') == json.dumps({'name': 'bar'})
        assert 'custom_header' in response.headers.keys()
        assert 'lala' in result.headers.values()

    def test_api_exceptions(self):
        exception = APIException('error')
        assert exception.status == 400
        assert exception.message == 'error'

        result = exception.to_result()
        assert result.status == 400
        assert result.value == {
            'error': 'error', 'message': 'error', 'status': 400
        }

        exception = APIException('not found', 404)
        assert exception.status == 404
        assert exception.message == 'not found'

        result = exception.to_result()
        assert result.status == 404
        assert result.value == {
            'error': 'not found', 'message': 'not found', 'status': 404
        }

    def test_flask_make_response(self, app):
        response_text = "Output Text"

        response = app.make_response(response_text)
        assert response.data.decode('utf-8') == response_text

        api_result = APIResult({'text': "Output"})
        response = app.make_response(api_result)
        assert response.content_type == 'application/json'
        assert response.status_code == 200
        assert response.data.decode('utf-8') == api_result.to_response().data.decode('utf-8')

    def test_conftest(self, user, db_session, super_credentials):
        resp = self.client.get(
            url_for('users.list'), headers=super_credentials,
            content_type='application/json')
        assert resp.status_code == 200
        assert len(resp.get_json()['users']) == 2

    def test_command(self, db_session):
        # test testing command :)
        runner = app.test_cli_runner()
        result = runner.invoke(tst, ['app/test_app_cli.py'])
        assert result.exit_code == 0

        # test initdb command
        # create superuser and seed data
        result = runner.invoke(
            initdb, ['', '-u', 'remy', '-e', 'remy@pindo.io', '-p', 'remy'])
        assert result.exit_code == 0
        assert result.exception is None

        # check for users both super and anon
        superuser = User.query.first()
        assert User.query.count() == 2
        assert User.query.get(-1).username == 'anon'
        assert superuser.username == 'remy'

        # duplicate superuser
        result = runner.invoke(
            initdb, ['-u', 'remy', '-e', 'remy@pindo.io', '-p', 'pindo'])
        assert result.exit_code == 1

    def test_unhautorized_token_fake_creds(self, user, db_session, fake_credentials):
        resp = self.client.get(
            url_for('users.list'), headers=fake_credentials, content_type='application/json')
        assert resp.status_code == 401

    def test_unhautorized_token_empty_creds(self, user, db_session, empty_credentials):
        resp = self.client.get(
            url_for('users.list'), headers=empty_credentials,
            content_type='application/json')
        assert resp.status_code == 401
