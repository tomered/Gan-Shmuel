import json 

def test_add_provider_success(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    response = client.post('/provider', json={'name': 'Test Provider'}, content_type='application/json')
    print(response.status_code, response.data.decode())  # Debug output
    assert response.status_code == 201
    response_data = json.loads(response.data)
    assert 'id' in response_data
    assert response_data['id'] == '1'
    mock_cursor.execute.assert_any_call("SELECT id FROM Provider WHERE name = %s", ('Test Provider',))
    mock_cursor.execute.assert_any_call("INSERT INTO Provider (name) VALUES (%s)", ('Test Provider',))
    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()