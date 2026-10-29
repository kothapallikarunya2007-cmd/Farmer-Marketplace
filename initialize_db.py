"""Idempotent schema setup; existing local records are preserved."""
from sqlalchemy import inspect, text
from app import app
from extensions import db


def initialize():
    db.create_all()
    columns={c['name'] for c in inspect(db.engine).get_columns('products')}
    additions={'category':"VARCHAR(40) NOT NULL DEFAULT 'Vegetables'",'unit':"VARCHAR(20) NOT NULL DEFAULT 'kg'",'active':'BOOLEAN NOT NULL DEFAULT TRUE'}
    with db.engine.begin() as connection:
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(text(f'ALTER TABLE products ADD COLUMN {name} {definition}'))
    print('Database schema ready; existing records preserved.')


if __name__=='__main__':
    with app.app_context():
        initialize()
