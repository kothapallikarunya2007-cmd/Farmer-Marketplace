import os
from pathlib import Path
from flask import Flask, jsonify, send_from_directory
from dotenv import load_dotenv
from sqlalchemy import text
from werkzeug.exceptions import HTTPException
from extensions import db

load_dotenv(Path(__file__).with_name('.env'))


def create_app(config=None):
    app = Flask(__name__, static_folder='public', static_url_path='')
    uri = os.getenv('DATABASE_URL', 'sqlite:///farmer_marketplace.db')
    if uri.startswith('postgres://'):
        uri = uri.replace('postgres://', 'postgresql+psycopg://', 1)
    elif uri.startswith('postgresql://'):
        uri = uri.replace('postgresql://', 'postgresql+psycopg://', 1)
    if os.getenv('VERCEL') and not uri.startswith('postgresql+psycopg://'):
        raise RuntimeError('Vercel requires a hosted PostgreSQL DATABASE_URL.')
    app.config.update(SQLALCHEMY_ENGINE_OPTIONS={'pool_pre_ping': True}, SQLALCHEMY_DATABASE_URI=uri, SQLALCHEMY_TRACK_MODIFICATIONS=False,
                      MAX_CONTENT_LENGTH=1024 * 1024)
    if config:
        app.config.update(config)
    db.init_app(app)
    from routes import api
    app.register_blueprint(api)

    @app.get('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')

    @app.get('/health')
    def health():
        db.session.execute(text('SELECT 1'))
        return jsonify(status='ok', database='connected')

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    @app.errorhandler(Exception)
    def server_error(error):
        db.session.rollback()
        app.logger.exception('Request failed')
        return jsonify(error='The request could not be completed. Please try again.'), 500

    @app.cli.command('init-db')
    def init_db():
        from initialize_db import initialize
        initialize()

    @app.cli.command('seed-demo')
    def seed_demo():
        from testdata import seed
        seed()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(port=5000, debug=False)
