import os
from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import Error
import pandas as pd

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


@app.route("/rates", methods=["POST"])
def add_rate():
    try:
        # Get data from file
        data = request.get_json()
        filename = data["filename"]
        filepath = f'/in/{filename}.xlsx'
        
        if not os.path.exists(filepath):
            raise FileNotFoundError (f"Error: The file '{filepath}' does not exist")
        
        data_frame = pd.read_excel(f"/in/{filename}.xlsx", engine = "openpyxl")
        file_data = data_frame.to_records(index=False).tolist()

        conn = get_db_connection() 
        cursor = conn.cursor(buffered=True)

        for rate in file_data:
            row_dict = dict(zip(data_frame.columns, rate))
            
            cursor.execute("SELECT * FROM Rates WHERE product_id=%s", (row_dict["Product"],))
            existing_product = cursor.fetchone()

            if existing_product:
                cursor.execute("UPDATE Rates SET rate=%s, scope=%s WHERE product_id=%s",(row_dict["Rate"], row_dict["Scope"], row_dict["Product"]))
            else :
                cursor.execute("INSERT INTO Rates (product_id, rate, scope) VALUES (%s, %s, %s)", (row_dict["Product"],row_dict["Rate"], row_dict["Scope"]))
            
        conn.commit()
        cursor.close()
        conn.close()
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404  # Return 404 if file is not found
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return data


if __name__ == '__main__':
    # TODO: Check if host 0.0.0.0 is the correct way to do this
    app.run(host='0.0.0.0', debug=True, port=5000)
