import os
from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import Error
import datetime


def get_db_connection():
    """Create a connection to the MySQL database"""
    # Try to connect multiple times (useful when starting up)

    try:
        conn = mysql.connector.connect(
            host="db",
            user="root",
            password="secret",
            database="billdb",
            connection_timeout=5
        )
        return conn
    except Error as e:
        raise Exception(f"Could not connect to MySQL database: {e}")


app = Flask(__name__)

# GET /health - Health check for app to db


@app.route('/health', methods=["GET"])
def health():
    # Connect to database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Execute "SELECT 1" on the mysqlDB
        cursor.execute("SELECT 1")

        cursor.fetchall()
        cursor.close()
        conn.close()

        return "OK", 200
    # Error handling for connectivity is done in get_db_connection.
    except Exception as e:
        return "Failure", 500


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

    except Exception as e:-14
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
    
# POST /truck registers a truck in the system, provider - known provider id, 
# id - the truck license plate
@app.route("/truck", methods=["POST"])
def register_truck():
    data = request.json
    truck_id = data.get("id")
    provider_id = data.get("provider")
    
    if not truck_id or not provider_id:
        return jsonify({"error": "Both 'id' and 'provider' fields are required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if provider exists
    cursor.execute("SELECT id FROM Provider WHERE id = %s", (provider_id,))
    provider = cursor.fetchone()
    
    if not provider:
        cursor.close()
        conn.close()
        return jsonify({"error": "Provider not found"}), 404
    
    try:
        # Insert truck record
        cursor.execute("INSERT INTO Trucks (id, provider_id) VALUES (%s, %s)", (truck_id, provider_id))
        conn.commit()
    except mysql.connector.IntegrityError:
        cursor.close()
        conn.close()
        return jsonify({"error": "Truck ID already exists"}), 409
    
    cursor.close()
    conn.close()
    
    return jsonify({"message": "Truck registered successfully"}), 201

    
@app.route('/truck/<id>', methods=['GET'])
def get_truck_sessions(id):
    t1 = request.args.get('from')
    t2 = request.args.get('to')
    
    if t1 is None:
        now = datetime.datetime.now()
        t1 = datetime.datetime(now.year, now.month, 1).strftime('%Y%m%d%H%M%S')
    else:
        try:
            datetime.datetime.strptime(t1, '%Y%m%d%H%M%S')
        except ValueError:
            return jsonify({"error": "Invalid 'from' date format. Use yyyymmddhhmmss"}), 400
            
    if t2 is None:
        t2 = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    else:
        try:
            datetime.datetime.strptime(t2, '%Y%m%d%H%M%S')
        except ValueError:
            return jsonify({"error": "Invalid 'to' date format. Use yyyymmddhhmmss"}), 400
    
    if t1 > t2:
        return jsonify({"error": "Start time must be before end time"}), 400

    if not id.strip():
        return jsonify({"error": "Truck ID cannot be empty"}), 400
    
    api = f"http://43.205.160.125:8082/item/{id}?from={t1}&to={t2}"
    
    response = requests.get(api)

    if response.status_code == 200:
        return response.json(), 200
    elif response.status_code == 404:
        return jsonify({"error": f"Truck with ID {id} not found"}), 404
    else:
        return jsonify({"error": f"External API error: {response.status_code}"}), response.status_code

if __name__ == '__main__':
    # TODO: Check if host 0.0.0.0 is the correct way to do this
    app.run(host='0.0.0.0', debug=True, port=5000)


