import os 
from flask import Flask, request, jsonify
import mysql.connector
import time

def get_db_connection():
    """Create a connection to the MySQL database"""
    # Try to connect multiple times (useful when starting up)
    for _ in range(10):
        try:
            conn = mysql.connector.connect(
                host="db",
                user="root",
                password="secret",
                database="billdb"
            )
            return conn
        except mysql.connector.Error:
            # Wait and retry
            time.sleep(3)
    
    raise Exception("Could not connect to MySQL database")

app = Flask(__name__)

@app.route('/provider', methods=['POST'])
def add_provider():
    try:
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({'error': 'Name is required'}), 400
        
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        check_query = "SELECT id FROM Provider WHERE name = %s"
        cursor.execute(check_query, (data['name'],))
        existing = cursor.fetchone()
        
        if existing:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Provider with this name already exists'}), 409
        
        insert_query = "INSERT INTO Provider (name) VALUES (%s)"
        cursor.execute(insert_query, (data['name'],))
        
        provider_id = cursor.lastrowid
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'id': str(provider_id)}), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/provider/<int:id>', methods=['PUT'])
def update_provider(id):
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'error': 'Name is required'}), 400
        
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if provider exists
        check_query = "SELECT id FROM Provider WHERE id = %s"
        cursor.execute(check_query, (id,))
        existing = cursor.fetchone()
        
        if not existing:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Provider not found'}), 404
        
        # Check if the new name already exists with a different ID
        check_name_query = "SELECT id FROM Provider WHERE name = %s AND id != %s"
        cursor.execute(check_name_query, (data['name'], id))
        name_exists = cursor.fetchone()
        
        if name_exists:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Another provider with this name already exists'}), 409
        
        # Update the provider
        update_query = "UPDATE Provider SET name = %s WHERE id = %s"
        cursor.execute(update_query, (data['name'], id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'id': str(id), 'name': data['name']}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
if __name__ == '__main__':
    # TODO: Check if host 0.0.0.0 is the correct way to do this
    app.run(host='0.0.0.0', debug=True, port=4000)





