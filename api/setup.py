from setuptools import setup, find_packages


setup(
    name='Flask-Boilerplate',
    version='0.0.1',
    package=find_packages(),
    install_requires=[
        'Flask==1.0.2',

        # database related
        'Flask-SQLAlchemy==2.3.2',
        'Flask-Migrate==2.4.0',

        # authentication & security
        'Flask-Cors==3.0.7',
        'Flask-Bcrypt==0.7.1',
        'Flask-HTTPAuth==3.2.4',
        'Flask-Bouncer==0.1.13',

        # testing
        'pytest==4.4.1',
        'pytest-cov==2.6.1',
        'pytest-flask==0.14.0',
        'pytest-flake8== 1.0.4',

        'redis==3.2.1',
        'celery==4.3.0',
        'gunicorn==19.9.0',
        'voluptuous==0.11.5',
        'inflection==0.3.1',
        'psycopg2-binary==2.8.2'
    ],
    classifiers=[
        'Development Status :: 1 - Alpha',
        'Environment :: Application Programming Interface',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: REST API'
    ]
)
