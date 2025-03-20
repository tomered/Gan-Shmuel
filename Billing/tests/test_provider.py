import json

# POST /provider


def test_add_provider_success(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    response = client.post(
        '/provider', json={'name': 'Test Provider'}, content_type='application/json')

    assert response.status_code == 201
    response_data = json.loads(response.data)

    assert 'id' in response_data
    assert response_data['id'] == '1'

    mock_cursor.execute.assert_any_call(
        "SELECT id FROM Provider WHERE name = %s", ('Test Provider',))
    mock_cursor.execute.assert_any_call(
        "INSERT INTO Provider (name) VALUES (%s)", ('Test Provider',))
    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


def test_add_provider_missing_name(client, mock_db_connection):
    response = client.post('/provider', json={},
                           content_type='application/json')

    assert response.status_code == 400
    assert response.get_json() == {'error': 'Name is required'}


def test_add_provider_provider_exists(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    # Simulate a provider already existing in the database
    # Simulate existing provider with id 1
    mock_cursor.fetchone.return_value = (1,)

    response = client.post('/provider', json={'name': 'Test Provider'})

    assert response.status_code == 409
    assert response.get_json() == {
        'error': 'Provider with this name already exists'}

    # Verify that SELECT query was called to check for existing provider
    mock_cursor.execute.assert_any_call(
        "SELECT id FROM Provider WHERE name = %s", ('Test Provider',))


def test_add_provider_server_error(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    # Simulate a database error (e.g., connection failure)
    mock_cursor.execute.side_effect = Exception("Database connection error")

    response = client.post('/provider', json={'name': 'Test Provider'})

    assert response.status_code == 500
    assert response.get_json() == {'error': 'Database connection error'}


# PUT /provider
def test_update_provider_success(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    # Provider exists, no name conflict
    mock_cursor.fetchone.side_effect = [('1',), None]

    response = client.put('/provider/1',
                          json={'name': 'Updated Provider'},
                          content_type='application/json')

    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data == {'id': '1', 'name': 'Updated Provider'}

    mock_cursor.execute.assert_any_call(
        "SELECT id FROM Provider WHERE id = %s", (1,))
    mock_cursor.execute.assert_any_call("SELECT id FROM Provider WHERE name = %s AND id != %s",
                                        ('Updated Provider', 1))
    mock_cursor.execute.assert_any_call("UPDATE Provider SET name = %s WHERE id = %s",
                                        ('Updated Provider', 1))
    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


def test_update_provider_missing_name(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    
    response = client.put('/provider/1', 
                         json={}, 
                         content_type='application/json')
    
    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert response_data == {'error': 'Name is required'}
    
    mock_cursor.execute.assert_not_called()  # No DB calls should happen
    mock_conn.commit.assert_not_called()


def test_update_provider_not_found(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = None  # Provider doesn't exist
    
    response = client.put('/provider/1', 
                         json={'name': 'Updated Provider'}, 
                         content_type='application/json')
    
    assert response.status_code == 404
    response_data = json.loads(response.data)
    assert response_data == {'error': 'Provider not found'}
    
    mock_cursor.execute.assert_called_once_with("SELECT id FROM Provider WHERE id = %s", (1,))
    mock_conn.commit.assert_not_called()


def test_update_provider_name_conflict(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.side_effect = [('1',), ('2',)]  # Provider exists, name taken by another
    
    response = client.put('/provider/1', 
                         json={'name': 'Existing Provider'}, 
                         content_type='application/json')
    
    assert response.status_code == 409
    response_data = json.loads(response.data)
    assert response_data == {'error': 'Another provider with this name already exists'}
    
    mock_cursor.execute.assert_any_call("SELECT id FROM Provider WHERE id = %s", (1,))
    mock_cursor.execute.assert_any_call("SELECT id FROM Provider WHERE name = %s AND id != %s", 
                                       ('Existing Provider', 1))
    mock_conn.commit.assert_not_called()


def test_update_provider_db_error(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.execute.side_effect = Exception("Database error")  # Simulate DB failure
    
    response = client.put('/provider/1', 
                         json={'name': 'Updated Provider'}, 
                         content_type='application/json')
    
    assert response.status_code == 500
    response_data = json.loads(response.data)
    assert response_data == {'error': 'Database error'}
    
    mock_cursor.execute.assert_called()  # At least one execute call attempted
    mock_conn.commit.assert_not_called()