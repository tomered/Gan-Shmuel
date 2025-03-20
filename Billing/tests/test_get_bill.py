import pytest
import json
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

@patch('app.get_billdb_data')
@patch('app.get_session_list_per_truck')
@patch('app.process_session_data')
def test_get_bill_success(mock_process_session_data,
                          mock_get_session_list,
                          mock_get_billdb_data,
                          client):
    # Setup mocks
    mock_get_billdb_data.return_value = (
        True, 
        True, 
        "Test Provider", 
        2,  # truck count
        [{"id": "T1"}, {"id": "T2"}],  # truck list
        [{"product_id": "corn", "rate": 12}, {"product_id": "wheat", "rate": 15}]  # rates list
    )
    
    mock_get_session_list.return_value = (
        3,  # session count
        {"T1": ["S1", "S2"], "T2": ["S3"]}  # session list per truck
    )
    
    mock_process_session_data.return_value = {
        "corn": {"count": 2, "amount": 3000},
        "wheat": {"count": 1, "amount": 1500}
    }
    
    # Make the request
    response = client.get('/bill/1?from=20240101000000&to=20240131235959')
    
    # Verify response
    assert response.status_code == 201
    
    data = json.loads(response.data)
    assert data["id"] == "1"
    assert data["name"] == "Test Provider"
    assert data["from"] == "20240101000000"
    assert data["to"] == "20240131235959"
    assert data["truckCount"] == 2
    assert data["sessionCount"] == 3
    
    # Check products
    assert len(data["products"]) == 2
    
    corn_product = next((p for p in data["products"] if p["product"] == "corn"), None)
    assert corn_product is not None
    assert corn_product["count"] == "2"  # Should be a string per the spec
    assert corn_product["amount"] == 3000
    assert corn_product["rate"] == 12
    assert corn_product["pay"] == 36000  # 3000 * 12
    
    wheat_product = next((p for p in data["products"] if p["product"] == "wheat"), None)
    assert wheat_product is not None
    assert wheat_product["count"] == "1"  # Should be a string per the spec
    assert wheat_product["amount"] == 1500
    assert wheat_product["rate"] == 15
    assert wheat_product["pay"] == 22500  # 1500 * 15
    
    # Check total
    assert data["total"] == 58500  # 36000 + 22500

@patch('app.get_billdb_data')
def test_get_bill_provider_not_found(mock_get_billdb_data, client):
    # Setup mock to return provider not found
    mock_get_billdb_data.return_value = (
        False, 
        "Provider not found", 
        None, None, None, None
    )
    
    # Make the request
    response = client.get('/bill/999')
    
    # Verify response
    assert response.status_code == 404
    data = json.loads(response.data)
    assert "error" in data
    assert "Provider not found" in data["error"]

@patch('app.get_billdb_data')
def test_get_bill_db_error(mock_get_billdb_data, client):
    # Setup mock to return database error
    mock_get_billdb_data.return_value = (
        False, 
        "Error retrieving data from database", 
        None, None, None, None
    )
    
    # Make the request
    response = client.get('/bill/1')
    
    # Verify response
    assert response.status_code == 500
    data = json.loads(response.data)
    assert "error" in data
    assert "Error retrieving data from database" in data["error"]

def test_get_bill_invalid_time_format(client):
    # Make the request with invalid time format
    response = client.get('/bill/1?from=2024-01-01&to=20240131235959')
    
    # Verify response
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "Invalid 'from' date format" in data["error"]

def test_get_bill_time_order_error(client):
    # Make the request with start time after end time
    response = client.get('/bill/1?from=20240201000000&to=20240101000000')
    
    # Verify response
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "Start time must be before end time" in data["error"]

def test_get_bill_empty_id(client):
    # Make the request with empty ID
    response = client.get('/bill/ ')
    
    # Verify response
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "Provider ID cannot be empty" in data["error"]

@patch('app.get_billdb_data')
@patch('app.get_session_list_per_truck')
def test_get_bill_session_list_error(mock_get_session_list,
                                    mock_get_billdb_data,
                                    client):
    # Setup mocks
    mock_get_billdb_data.return_value = (
        True, 
        True, 
        "Test Provider", 
        2,  # truck count
        [{"id": "T1"}, {"id": "T2"}],  # truck list
        [{"product_id": "corn", "rate": 12}]  # rates list
    )
    
    # Simulate error in get_session_list_per_truck
    mock_get_session_list.return_value = (
        None,  # session count
        "Error fetching data for truck T1: Connection refused"  # Error message
    )
    
    # Make the request
    response = client.get('/bill/1')
    
    # Verify response
    data = json.loads(response.data)
    assert "error" in data
    assert "Error fetching data for truck" in data["error"]

@patch('app.get_billdb_data')
@patch('app.get_session_list_per_truck')
@patch('app.process_session_data')
def test_get_bill_process_session_error(mock_process_session_data,
                                       mock_get_session_list,
                                       mock_get_billdb_data,
                                       client):
    # Setup mocks
    mock_get_billdb_data.return_value = (
        True, 
        True, 
        "Test Provider", 
        2,  # truck count
        [{"id": "T1"}, {"id": "T2"}],  # truck list
        [{"product_id": "corn", "rate": 12}]  # rates list
    )
    
    mock_get_session_list.return_value = (
        3,  # session count
        {"T1": ["S1", "S2"], "T2": ["S3"]}  # session list per truck
    )
    
    # Simulate error in process_session_data - the function returns a string on error
    mock_process_session_data.return_value = "Error processing session S1: Invalid data format"
    
    # Make the request
    response = client.get('/bill/1')
    
    # Looking at your code, when process_session_data returns a string error,
    # it gets assigned directly to the "error" field in the response
    data = json.loads(response.data)
    assert "error" in data
    # The error should be the session list - because there's a check in your code:
    # if isinstance(product_stats, str):
    #     return jsonify({"error": sessionListPerTruck})
    # So the error is actually the sessionListPerTruck value
    assert "Error processing session S1: Invalid data format" in data["error"]
    assert "Error processing session" in data["error"]

@patch('app.get_billdb_data')
@patch('app.get_session_list_per_truck')
@patch('app.process_session_data')
def test_get_bill_no_matching_products(mock_process_session_data,
                                       mock_get_session_list,
                                       mock_get_billdb_data,
                                       client):
    # Setup mocks
    mock_get_billdb_data.return_value = (
        True, 
        True, 
        "Test Provider", 
        2,  # truck count
        [{"id": "T1"}, {"id": "T2"}],  # truck list
        [{"product_id": "corn", "rate": 12}]  # rates list
    )
    
    mock_get_session_list.return_value = (
        3,  # session count
        {"T1": ["S1", "S2"], "T2": ["S3"]}  # session list per truck
    )
    
    # Return session data with no matching products
    mock_process_session_data.return_value = {
        "wheat": {"count": 1, "amount": 1500}  # No corn (which was in rates list)
    }
    
    # Make the request
    response = client.get('/bill/1')
    
    # Verify response - should work but have empty products
    assert response.status_code == 201
    
    data = json.loads(response.data)
    assert data["id"] == "1"
    assert data["name"] == "Test Provider"
    assert data["products"] == []  # No matching products
    assert data["total"] == 0  # Zero total payment
    
    # Additional checks to verify all required fields are present
    assert "from" in data
    assert "to" in data
    assert "truckCount" in data
    assert "sessionCount" in data