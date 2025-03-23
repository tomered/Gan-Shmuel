import pytest
from unittest.mock import patch, MagicMock
import mysql.connector
import os
from weight import app  # Assuming app.py contains your Flask app

# Set environment variables for testing (optional, if not set elsewhere)
@pytest.fixture(autouse=True)
def set_env_vars():
    os.environ['DB_HOST'] = 'weight-test-db'  # Mock value for tests
    yield
    # Cleanup if needed, though not critical for these mocks

# Fixture for Flask test client
@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

# Fixture to mock the database connection (replaces connect_db or get_db_connection)
@pytest.fixture
def mock_db_connection():
    with patch('app.connect_db') as mock_connect:  # Mocking connect_db function
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        yield mock_conn, mock_cursor

# Alternative fixture for a global mydb (if used in app.py)
@pytest.fixture
def mock_mydb():
    with patch('app.mydb') as mock_db:
        mock_cursor = MagicMock()
        mock_db.cursor.return_value = mock_cursor
        yield mock_db

# Fixture to mock validate_time (for get_truck_sessions)
@pytest.fixture
def mock_validate_time():
    with patch('app.validate_time') as mock:
        yield mock

# Fixture to mock requests.get (for get_truck_sessions)
@pytest.fixture
def mock_requests_get():
    with patch('app.requests.get') as mock:
        yield mock