import pytest
from unittest.mock import patch, MagicMock
from app import app

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_db_connection():
    with patch('app.get_db_connection') as mock_get_db_connection:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # No existing provider
        mock_cursor.lastrowid = 1  # Simulated ID after insert
        mock_conn.cursor.return_value = mock_cursor  # cursor() returns mock_cursor
        mock_get_db_connection.return_value = mock_conn  # Return just the connection
        yield mock_conn, mock_cursor  # Yield both for test assertions