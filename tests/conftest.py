# tests/conftest.py
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import create_app
from extensions import mongo

from tests.test_config import TestConfig

@pytest.fixture
def app():
    """
    Fixture to create a Flask application instance for testing.
    """
    app = create_app()
    app.config.from_object(TestConfig)
    with app.app_context():
        # Initialize the database
        mongo.init_app(app)
        yield app
        
@pytest.fixture
def client(app):
    """
    Fixture to create a test client for the Flask application.
    """
    return app.test_client()

@pytest.fixture
def clear_db(app):
    """
    Fixture to clear the database before each test.
    """
    with app.app_context():
        collections = mongo.db.list_collection_names()
        for collection in collections:
            mongo.db.drop_collection(collection)
    