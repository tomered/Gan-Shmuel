import pytest
import json
import os
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
        mock_cursor.fetchone.return_value = None  # No existing provider by default
        mock_cursor.lastrowid = 1  # Simulated ID after insert
        mock_conn.cursor.return_value = mock_cursor  # cursor() returns mock_cursor
        mock_get_db_connection.return_value = mock_conn  # Return just the connection
        yield mock_conn, mock_cursor  # Yield both for test assertions

# Tests for POST /rates endpoint
@patch('os.path.exists')
@patch('pandas.read_excel')
def test_add_rate_success_new_product(mock_read_excel, mock_exists, client, mock_db_connection):
    """Test adding a new rate successfully."""
    # Setup
    mock_conn, mock_cursor = mock_db_connection
    mock_exists.return_value = True
    
    # Create a mock DataFrame
    mock_df = MagicMock()
    mock_df.columns = ["Product", "Rate", "Scope"]
    mock_df.to_records.return_value.tolist.return_value = [("PROD1", 10.5, "All")]
    mock_read_excel.return_value = mock_df
    
    # Configure cursor behavior
    mock_cursor.fetchone.return_value = None  # No existing product
    
    # Make the request
    response = client.post('/rates', json={"filename": "test_rates"})
    
    # Assertions
    assert response.status_code == 201
    
    mock_exists.assert_called_once_with('/in/test_rates.xlsx')
    mock_read_excel.assert_called_once_with('/in/test_rates.xlsx', engine='openpyxl')
    
    # Check that INSERT was called with correct params
    mock_cursor.execute.assert_any_call(
        "INSERT INTO Rates (product_id, rate, scope) VALUES (%s, %s, %s)", 
        ("PROD1", 10.5, "All")
    )
    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()

@patch('os.path.exists')
@patch('pandas.read_excel')
def test_add_rate_update_existing_product(mock_read_excel, mock_exists, client, mock_db_connection):
    """Test updating an existing rate successfully."""
    # Setup
    mock_conn, mock_cursor = mock_db_connection
    mock_exists.return_value = True
    
    # Create a mock DataFrame
    mock_df = MagicMock()
    mock_df.columns = ["Product", "Rate", "Scope"]
    mock_df.to_records.return_value.tolist.return_value = [("PROD1", 15.75, "All")]
    mock_read_excel.return_value = mock_df
    
    # Configure cursor to return an existing product
    mock_cursor.fetchone.return_value = {"product_id": "PROD1", "rate": 10.5, "scope": "All"}
    
    # Make the request
    response = client.post('/rates', json={"filename": "test_rates"})
    
    # Assertions
    assert response.status_code == 200
    
    # Check that UPDATE was called with correct params
    mock_cursor.execute.assert_any_call(
        "UPDATE Rates SET rate=%s, scope=%s WHERE product_id=%s",
        (15.75, "All", "PROD1")
    )
    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()

@patch('os.path.exists')
@patch('pandas.read_excel')
def test_add_rate_for_specific_provider(mock_read_excel, mock_exists, client, mock_db_connection):
    """Test adding a rate for a specific provider."""
    # Setup
    mock_conn, mock_cursor = mock_db_connection
    mock_exists.return_value = True
    
    # Create a mock DataFrame
    mock_df = MagicMock()
    mock_df.columns = ["Product", "Rate", "Scope"]
    mock_df.to_records.return_value.tolist.return_value = [("PROD1", 20.0, "PROVIDER123")]
    mock_read_excel.return_value = mock_df
    
    # Mock cursor to return a provider on first call and no existing product on second
    mock_cursor.fetchone.side_effect = [{"id": "PROVIDER123"}, None]
    
    # Make the request
    response = client.post('/rates', json={"filename": "test_rates"})
    
    # Assertions
    assert response.status_code == 201
    
    # Check provider exists query
    mock_cursor.execute.assert_any_call(
        "SELECT * FROM Provider WHERE id=%s", 
        ("PROVIDER123",)
    )
    
    # Check that INSERT was called with correct params
    mock_cursor.execute.assert_any_call(
        "INSERT INTO Rates (product_id, rate, scope) VALUES (%s, %s, %s)", 
        ("PROD1", 20.0, "PROVIDER123")
    )
    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()

@patch('os.path.exists')
def test_add_rate_file_not_found(mock_exists, client):
    """Test handling when Excel file doesn't exist."""
    # Setup
    mock_exists.return_value = False
    
    # Make the request
    response = client.post('/rates', json={"filename": "nonexistent"})
    
    # Assertions
    assert response.status_code == 404
    response_data = json.loads(response.data)
    assert "error" in response_data
    assert "does not exist" in response_data["error"]

@patch('os.path.exists')
@patch('pandas.read_excel')
def test_add_rate_provider_not_found(mock_read_excel, mock_exists, client, mock_db_connection):
    """Test handling when provider doesn't exist."""
    # Setup
    mock_conn, mock_cursor = mock_db_connection
    mock_exists.return_value = True
    
    # Create a mock DataFrame
    mock_df = MagicMock()
    mock_df.columns = ["Product", "Rate", "Scope"]
    mock_df.to_records.return_value.tolist.return_value = [("PROD1", 10.5, "NONEXISTENT")]
    mock_read_excel.return_value = mock_df
    
    # Make cursor return None (no provider found)
    mock_cursor.fetchone.return_value = None
    
    # Make the request
    response = client.post('/rates', json={"filename": "test_rates"})
    
    # Assertions
    assert response.status_code == 404
    response_data = json.loads(response.data)
    assert "error" in response_data
    assert "does not exist" in response_data["error"]

@patch('os.path.exists')
@patch('pandas.read_excel')
def test_add_rate_general_exception(mock_read_excel, mock_exists, client, mock_db_connection):
    """Test handling of general exceptions."""
    # Setup
    mock_conn, mock_cursor = mock_db_connection
    mock_exists.return_value = True
    
    # Make read_excel raise an exception
    mock_read_excel.side_effect = Exception("Database connection failed")
    
    # Make the request
    response = client.post('/rates', json={"filename": "test_rates"})
    
    # Assertions
    assert response.status_code == 500
    response_data = json.loads(response.data)
    assert "error" in response_data

# Tests for GET /rates endpoint
def test_rates_download_success(client, mock_db_connection):
    """Test successful download of rates."""
    # Setup
    mock_conn, mock_cursor = mock_db_connection
    
    # Mock data to be returned from database
    mock_rates = [
        {"product_id": "PROD1", "rate": 10.5, "scope": "All"},
        {"product_id": "PROD2", "rate": 15.75, "scope": "PROVIDER123"}
    ]
    mock_cursor.fetchall.return_value = mock_rates
    
    # Mock DataFrame.to_excel to avoid actual file operations
    with patch('pandas.DataFrame.to_excel'):
        # Make the request
        response = client.get('/rates')
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "message" in response_data
        assert "Rates successfully downloaded" in response_data["message"]
        
        # Check that correct SQL query was executed
        mock_cursor.execute.assert_called_once_with(
            "SELECT product_id, rate, scope FROM Rates"
        )
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

def test_rates_download_no_rates(client, mock_db_connection):
    """Test download when no rates are available."""
    # Setup
    mock_conn, mock_cursor = mock_db_connection
    
    # Return empty list (no rates)
    mock_cursor.fetchall.return_value = []
    
    # Make the request
    response = client.get('/rates')
    
    # Assertions
    assert response.status_code == 404
    response_data = json.loads(response.data)
    assert "error" in response_data
    assert "No rates available" in response_data["error"]
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()

def test_rates_download_exception(client, mock_db_connection):
    """Test handling of exceptions during download."""
    # Setup
    mock_conn, mock_cursor = mock_db_connection
    
    # Make cursor.execute raise an exception
    mock_cursor.execute.side_effect = Exception("Database error")
    
    # Make the request
    response = client.get('/rates')
    
    # Assertions
    assert response.status_code == 500
    response_data = json.loads(response.data)
    assert "error" in response_data
    assert "Error downloading rates" in response_data["error"]