import pytest
from unittest.mock import patch, MagicMock
import json
import mysql.connector  # Added for IntegrityError

# Fixture to mock validate_time function
@pytest.fixture
def mock_validate_time():
    with patch('app.validate_time') as mock:
        yield mock

# Fixture to mock requests.get
@pytest.fixture
def mock_requests_get():
    with patch('app.requests.get') as mock:
        yield mock

        
# POST /truck

def test_register_truck_success(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = ('1',)  # Provider exists
    
    response = client.post('/truck', 
                          json={'id': 'TRUCK1', 'provider': '1'}, 
                          content_type='application/json')
    
    assert response.status_code == 201
    response_data = json.loads(response.data)
    assert response_data == {'message': 'Truck registered successfully'}
    
    mock_cursor.execute.assert_any_call("SELECT id FROM Provider WHERE id = %s", ('1',))
    mock_cursor.execute.assert_any_call("INSERT INTO Trucks (id, provider_id) VALUES (%s, %s)", 
                                       ('TRUCK1', '1'))
    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()

def test_register_truck_missing_fields(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    
    # Missing 'id'
    response = client.post('/truck', 
                          json={'provider': '1'}, 
                          content_type='application/json')
    
    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert response_data == {'error': "Both 'id' and 'provider' fields are required"}
    
    mock_cursor.execute.assert_not_called()
    mock_conn.commit.assert_not_called()

def test_register_truck_provider_not_found(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = None  # Provider doesn't exist
    
    response = client.post('/truck', 
                          json={'id': 'TRUCK1', 'provider': '1'}, 
                          content_type='application/json')
    
    assert response.status_code == 404
    response_data = json.loads(response.data)
    assert response_data == {'error': 'Provider not found'}
    
    mock_cursor.execute.assert_called_once_with("SELECT id FROM Provider WHERE id = %s", ('1',))
    mock_conn.commit.assert_not_called()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()

def test_register_truck_id_exists(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = ('1',)  # Provider exists
    mock_cursor.execute.side_effect = [
        None,  # For the SELECT query
        mysql.connector.IntegrityError("Duplicate entry")  # For the INSERT query
    ]
    
    response = client.post('/truck', 
                          json={'id': 'TRUCK1', 'provider': '1'}, 
                          content_type='application/json')
    
    assert response.status_code == 409
    response_data = json.loads(response.data)
    assert response_data == {'error': 'Truck ID already exists'}
    
    mock_cursor.execute.assert_any_call("SELECT id FROM Provider WHERE id = %s", ('1',))
    mock_cursor.execute.assert_any_call("INSERT INTO Trucks (id, provider_id) VALUES (%s, %s)", 
                                       ('TRUCK1', '1'))
    mock_conn.commit.assert_not_called()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


# PUT /truck

def test_update_truck_success(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.side_effect = [('1',), ('TRUCK1',)]  # Provider exists, truck exists
    
    response = client.put('/truck/TRUCK1', 
                         json={'provider': '1'}, 
                         content_type='application/json')
    
    assert response.status_code == 201
    response_data = json.loads(response.data)
    assert response_data == {'message': 'Truck provider changed successfully'}
    
    mock_cursor.execute.assert_any_call("SELECT id FROM Provider WHERE id = %s", ('1',))
    mock_cursor.execute.assert_any_call("SELECT id FROM Trucks WHERE id = %s", ('TRUCK1',))
    mock_cursor.execute.assert_any_call("UPDATE Trucks SET provider_id=%s where id=%s", ('1', 'TRUCK1'))
    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()

def test_update_truck_missing_provider(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    
    response = client.put('/truck/TRUCK1', 
                         json={}, 
                         content_type='application/json')
    
    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert response_data == {'error': 'provider is required'}
    
    mock_cursor.execute.assert_not_called()
    mock_conn.commit.assert_not_called()

def test_update_truck_provider_not_found(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = None  # Provider doesn't exist
    
    response = client.put('/truck/TRUCK1', 
                         json={'provider': '1'}, 
                         content_type='application/json')
    
    assert response.status_code == 404
    response_data = json.loads(response.data)
    assert response_data == {'error': 'Provider not found in Trucks'}
    
    mock_cursor.execute.assert_called_once_with("SELECT id FROM Provider WHERE id = %s", ('1',))
    mock_conn.commit.assert_not_called()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()

def test_update_truck_truck_not_found(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.side_effect = [('1',), None]  # Provider exists, truck doesn't exist
    
    response = client.put('/truck/TRUCK1', 
                         json={'provider': '1'}, 
                         content_type='application/json')
    
    assert response.status_code == 404
    response_data = json.loads(response.data)
    assert response_data == {'error': 'Truck not found in Trucks'}
    
    mock_cursor.execute.assert_any_call("SELECT id FROM Provider WHERE id = %s", ('1',))
    mock_cursor.execute.assert_any_call("SELECT id FROM Trucks WHERE id = %s", ('TRUCK1',))
    mock_conn.commit.assert_not_called()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()

def test_update_truck_database_error(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.side_effect = [('1',), ('TRUCK1',)]  # Provider and truck exist
    mock_cursor.execute.side_effect = [None, None, Exception("Database error")]  # Error on UPDATE
    
    response = client.put('/truck/TRUCK1', 
                         json={'provider': '1'}, 
                         content_type='application/json')
    
    assert response.status_code == 500
    response_data = json.loads(response.data)
    assert response_data == {'error': 'Database error'}
    
    mock_cursor.execute.assert_any_call("SELECT id FROM Provider WHERE id = %s", ('1',))
    mock_cursor.execute.assert_any_call("SELECT id FROM Trucks WHERE id = %s", ('TRUCK1',))
    mock_cursor.execute.assert_any_call("UPDATE Trucks SET provider_id=%s where id=%s", ('1', 'TRUCK1'))
    mock_conn.commit.assert_not_called()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


# GET /truck

def test_get_truck_sessions_success(client, mock_validate_time, mock_requests_get):
    mock_validate_time.return_value = ('2023-01-01', '2023-01-02', None)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'id': 'TRUCK1', 'tara': 5000, 'sessions': ['session1', 'session2']}
    mock_requests_get.return_value = mock_response
    
    response = client.get('/truck/TRUCK1?from=2023-01-01&to=2023-01-02')
    
    assert response.status_code == 200
    assert json.loads(response.data) == {'id': 'TRUCK1', 'tara': 5000, 'sessions': ['session1', 'session2']}

def test_get_truck_sessions_invalid_time(client, mock_validate_time, mock_requests_get):
    mock_validate_time.return_value = (None, None, ('Invalid time format', 400))
    
    response = client.get('/truck/TRUCK1?from=invalid&to=2023-01-02')
    
    assert response.status_code == 400
    assert json.loads(response.data) == {'error': 'Invalid time format'}

def test_get_truck_sessions_empty_id(client, mock_validate_time, mock_requests_get):
    mock_validate_time.return_value = ('2023-01-01', '2023-01-02', None)
    
    response = client.get('/truck/ ')  # Space-only ID
    
    assert response.status_code == 400
    assert json.loads(response.data) == {'error': 'Truck ID cannot be empty'}
    mock_validate_time.assert_called_once_with(None, None)  # Adjusted expectation

def test_get_truck_sessions_truck_not_found(client, mock_validate_time, mock_requests_get):
    mock_validate_time.return_value = ('2023-01-01', '2023-01-02', None)
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = 'Not found'
    mock_requests_get.return_value = mock_response
    
    response = client.get('/truck/TRUCK1?from=2023-01-01&to=2023-01-02')
    
    assert response.status_code == 404
    assert json.loads(response.data) == {'error': 'Truck with ID TRUCK1 not found'}

def test_get_truck_sessions_external_api_error(client, mock_validate_time, mock_requests_get):
    mock_validate_time.return_value = ('2023-01-01', '2023-01-02', None)
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = 'Server error'
    mock_requests_get.return_value = mock_response
    
    response = client.get('/truck/TRUCK1?from=2023-01-01&to=2023-01-02')
    
    assert response.status_code == 500
    assert json.loads(response.data) == {'error': 'External API error: Server error'}

def test_get_truck_sessions_missing_time_params(client, mock_validate_time, mock_requests_get):
    mock_validate_time.return_value = (None, None, ('Missing time parameters', 400))
    
    response = client.get('/truck/TRUCK1')
    
    assert response.status_code == 400
    assert json.loads(response.data) == {'error': 'Missing time parameters'}