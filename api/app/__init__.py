import click
import subprocess
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.factory import create_app
from app.awaremodel import User


app = create_app()
context_settings = dict(ignore_unknown_options=True, allow_extra_args=True)


@app.cli.command(context_settings=context_settings)
@click.option('-x', '--exitfirst', is_flag=True, default=False,
              help="Exit instantly on first error of failed test")
@click.option('--strict', is_flag=True, default=False,
              help="Run tests in strict mode warnings become errors")
@click.option('--pdb', is_flag=True, default=False,
              help="Start an interactive Python debugger on errors")
@click.option('--flake8', is_flag=True, default=False,
              help="Run linting test")
@click.option('--cov', default='app', type=click.Path(exists=True),
              help="Enable coverage on the application")
@click.option('--cov-report', default='term-missing',
              help="Start an interactive Python debugger on errors")
@click.option('--cov-config', default='.coveragerc',
              type=click.Path(exists=True, dir_okay=False), help="Config file for coverage")
@click.option('--no-cov', is_flag=True, help="Disable coverage report completely")
@click.option('--no-cov-on-fail', is_flag=True, default=True,
              help="No coverage report if test run fails")
@click.argument('file-or-dir', nargs=-1, type=click.Path(exists=True), required=True)
@click.pass_context
def test(ctx, exitfirst, strict, pdb, flake8,
         cov, cov_report, cov_config, no_cov, no_cov_on_fail,
         file_or_dir):
    """
    Runs application tests.
    """
    arguments = ctx.params.pop('file_or_dir')

    params = []
    for param in ctx.params.items():
        key, value = param
        key = '-'.join(key.split('_'))

        if isinstance(value, bool):
            if value is True:
                params.append('--{}'.format(key))
        else:
            params.append('--{} {}'.format(key, value))

    params.extend(arguments)
    # pytest.main(params) coverage FAILS check link below
    # https://github.com/pytest-dev/pytest/issues/1357
    cmd = 'py.test {}'.format(' '.join(params))
    subprocess.call(cmd, shell=True)


@app.cli.command(context_settings=context_settings)
@click.option('--username', '-u', prompt=True, help='Please enter username')
@click.option('--email', '-e', prompt=True, help='Please enter email')
@click.option('--password', '-p', prompt=True, hide_input=True, confirmation_prompt=True,
              help='Please enter password')
def initdb(username, email, password):
    """
    Initialize database with seed data
    """
    click.echo("Initialize the database seeding")

    try:
        click.echo("Creating superuser")
        # create superuser
        super = User(username=username, email=email, force=True,
                     confirmed_at=datetime.utcnow())
        super.set_password(password)
        super.save()
    except IntegrityError:
        raise click.ClickException("Superuser already exists in the database")

    anon = User(id=-1, username='anon', email='anon@pindo.io', active=False)
    anon.set_password('anonymous')
    anon.save()

    # Begin adding seed data here
