import pytest
import json
from app import app
from unittest.mock import patch, MagicMock

# SETUPs
@pytest.fixture
def client():
    # Create a test client for the app
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_db_connection():
    # Mock the database connection and cursor.
    with patch('app.get_db_connection') as mock_get_db:
        # Setup mock objects
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Configure the mocks
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        mock_cursor.lastrowid = 1

        yield mock_get_db, mock_conn, mock_cursor


# /POST PROVIDER TESTS
def test_add_provider_success(client, mock_db_connection):
    """Test successfully adding a new provider."""
    _, mock_conn, mock_cursor = mock_db_connection

    # Make the request
    response = client.post('/provider',
                           json={'name': 'Test Provider'},
                           content_type='application/json')

    # Check response
    assert response.status_code == 201
    response_data = json.loads(response.data)
    assert 'id' in response_data
    assert response_data['id'] == '1'

    # Verify DB calls
    mock_cursor.execute.assert_any_call("SELECT id FROM Provider WHERE name = %s",
                                        ('Test Provider',))
    mock_cursor.execute.assert_any_call("INSERT INTO Provider (name) VALUES (%s)",
                                        ('Test Provider',))
    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()
