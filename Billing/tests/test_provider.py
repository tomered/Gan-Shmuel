import json 

# POST /provider
def test_add_provider_success(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    response = client.post('/provider', json={'name': 'Test Provider'}, content_type='application/json')
    
    assert response.status_code == 201
    response_data = json.loads(response.data)
    
    assert 'id' in response_data
    assert response_data['id'] == '1'
    
    mock_cursor.execute.assert_any_call("SELECT id FROM Provider WHERE name = %s", ('Test Provider',))
    mock_cursor.execute.assert_any_call("INSERT INTO Provider (name) VALUES (%s)", ('Test Provider',))
    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()

    
def test_add_provider_missing_name(client, mock_db_connection):
    response = client.post('/provider', json={}, content_type='application/json')
    
    assert response.status_code == 400
    assert response.get_json() == {'error': 'Name is required'}


def test_add_provider_provider_exists(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    # Simulate a provider already existing in the database
    mock_cursor.fetchone.return_value = (1,)  # Simulate existing provider with id 1

    response = client.post('/provider', json={'name': 'Test Provider'})

    assert response.status_code == 409
    assert response.get_json() == {'error': 'Provider with this name already exists'}

    # Verify that SELECT query was called to check for existing provider
    mock_cursor.execute.assert_any_call("SELECT id FROM Provider WHERE name = %s", ('Test Provider',))


def test_add_provider_server_error(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    # Simulate a database error (e.g., connection failure)
    mock_cursor.execute.side_effect = Exception("Database connection error")

    response = client.post('/provider', json={'name': 'Test Provider'})

    assert response.status_code == 500
    assert response.get_json() == {'error': 'Database connection error'}
