import unittest
from app import app  # Import your Flask app
from unittest.mock import patch, MagicMock


class TestProvider(unittest.TestCase):
    @patch('mysql.connector.connect')
    def test_post_provider(self, mock_connect):
        # Create mock connection object
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Setup mock connection and cursor
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 1

        # Use Flask's test client to simulate a request
        with app.test_client() as client:
            response = client.post('/provider', json={'name': 'testtt'})

        self.assertEqual(response.status_code, 200)
        self.assertIn('id', response.json)
        self.assertIn('name', response.json)
        self.assertEqual(response.json['name'], 'testtt')
        self.assertEqual(response.json['id'], 1)

        mock_cursor.execute.assert_called_once_with(
            'INSERT INTO Provider (name) VALUES (%s)', ('testtt',)
        )
        
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

if __name__ == '__main__':
    unittest.main()
