import os
from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import Error
import datetime
import pandas as pd
import datetime
import requests


def get_db_connection():
    """Create a connection to the MySQL database"""
    # Try to connect multiple times (useful when starting up)

    try:
        conn = mysql.connector.connect(
            host="billing-db",
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

        # Check if file exists
        if not os.path.exists(filepath):
            raise FileNotFoundError (f"Error: The file '{filepath}' does not exist")

        # Read data from excel file in /in dir
        data_frame = pd.read_excel(f"/in/{filename}.xlsx", engine = "openpyxl")
        file_data = data_frame.to_records(index=False).tolist()

        # DB connection
        conn = get_db_connection() 
        cursor = conn.cursor(buffered=True)

        for rate in file_data:
            # Create dictionary out of data
            row_dict = dict(zip(data_frame.columns, rate))

            # If provider id is specified, check if provider exists
            if(row_dict["Scope"] != "All"):
                cursor.execute("SELECT * FROM Provider WHERE id=%s", (row_dict["Scope"],))
                existing_provider = cursor.fetchone()
                if not existing_provider:
                    raise LookupError(f"Provider with ID {row_dict["Scope"]} does not exist")

            # Check if product for specified scope already exists
            cursor.execute("SELECT * FROM Rates WHERE product_id=%s AND scope=%s", (row_dict["Product"], row_dict["Scope"]))
            existing_product = cursor.fetchone()


            status = None
            # Update existing product
            if existing_product:
                cursor.execute("UPDATE Rates SET rate=%s, scope=%s WHERE product_id=%s",(row_dict["Rate"], row_dict["Scope"], row_dict["Product"]))
                status = 200
            # Create new product
            else :
                cursor.execute("INSERT INTO Rates (product_id, rate, scope) VALUES (%s, %s, %s)", (row_dict["Product"],row_dict["Rate"], row_dict["Scope"]))
                status = 201
                
        conn.commit()
        cursor.close()
        conn.close()

    except LookupError as e :
        return jsonify({'error': str(e)}), 404  # Return 404 if provider is not found
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404  # Return 404 if file is not found
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return data, status

    
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
    t1, t2, error = validate_time(request.args.get('from'), request.args.get('to'))

    if error:
        return jsonify({"error": error[0]}), error[1]
    if not id.strip():
        return jsonify({"error": "Truck ID cannot be empty"}), 400
    
    api = f"http://web_weight:5000/item/{id}?from={t1}&to={t2}"
    
    response = requests.get(api)

    if response.status_code == 200:
        return response.json(), 200
    elif response.status_code == 404:
        return jsonify({"error": f"Truck with ID {id} not found"}), 404
    else:
        return jsonify({"error": f"External API error: {response.text}"}), response.status_code

    
# PUT /truck/{id}  can be used to update provider id 
@app.route('/truck/<string:id>', methods=['PUT'])
def update_truck(id):
    data = request.json
    truck_id = id
    provider_id = data.get("provider")
    
    # check how to validate truck id ?
    if not provider_id:
        #return jsonify({"error": 'provider' field is required"}), 400"
        return jsonify({'error': 'provider is required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if provider exists in Provider table
    cursor.execute("SELECT id FROM Provider WHERE id = %s", (provider_id,))
    provider = cursor.fetchone()
    
    if not provider:
        cursor.close()
        conn.close()
        return jsonify({"error": "Provider not found in Trucks"}), 404

    # Check if truck exists in Trucks table
    cursor.execute("SELECT id FROM Trucks WHERE id = %s", (truck_id,))
    truck = cursor.fetchone()
    
    if not truck:
        cursor.close()
        conn.close()
        return jsonify({"error": "Truck not found in Trucks"}), 404
    
    try:
        # Change provider in Truck table
        cursor.execute("UPDATE Trucks SET provider_id=%s where id=%s", (provider_id, truck_id,))
        conn.commit()
    except Exception as e:
        cursor.close()
        conn.close()        
        return jsonify({'error': str(e)}), 500
    
    # Closing the valid conncetion  
    cursor.close()
    conn.close()
    
    return jsonify({"message": "Truck provider changed successfully"}), 201


@app.route('/rates', methods=["GET"])
def rates_download():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT product_id, rate, scope FROM Rates"
        cursor.execute(query)
        rates = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not rates:
            return jsonify({"error": "No rates available for download"}), 404
        
        df = pd.DataFrame(rates)
        excel_path = "../in/rates.xlsx"
        df.to_excel(excel_path, index=False)
        
        # Return a success response
        return jsonify({"message": "Rates successfully downloaded to Excel", "file_path": excel_path}), 200
    except Exception as e:
        return jsonify({"error": f"Error downloading rates: {str(e)}"}), 500
    
@app.route('/bill/<id>', methods=['GET'])
def get_bill(id):
    if not id.strip():
        return jsonify({"error": "Provider ID cannot be empty"}), 400

    t1, t2, error = validate_time(request.args.get('from'), request.args.get('to'))
    success, result_or_error, name, truckCount, truckList = get_billdb_data(id)
    sessionCount, sessionListPerTruck = get_session_list_per_truck(truckList,t1,t2)

    #Error checks on frunctions
    if error:
        return jsonify({"error": error[0]}), error[1]
    elif not success:
        return jsonify({"error": result_or_error}), 404 if "not found" in result_or_error else 500
    elif isinstance(sessionListPerTruck, str):
        return jsonify({"error": sessionListPerTruck})
    
    products = [
        create_product("Apples", 2, 500, 250),
        create_product("Oranges", 1, 300, 320),
        create_product("Grapes", 3, 200, 450)
    ]
    total_payment = sum(product["pay"] for product in products)

    data = {
        "id": id,
        "name": name,
        "from": t1,
        "to": t2,
        "truckCount": truckCount,
        "sessionCount": sessionCount,
        "products": products,
        "total": total_payment
    }
    
def get_session_list_per_truck(truckList,t1,t2):
    truck_sessions_dict = {}
    for truck in truckList:
        try:
            truck_id = truck['id']
            api = f"http://web_weight:5000/item/{truck_id}?from={t1}&to={t2}"
            response = requests.get(api)
            truck_data = response.json()
            truck_sessions_dict[truck_id] = truck_data.get('sessions', [])

        except requests.exceptions.RequestException as e:
            return None, f"Error fetching data for truck {truck_id}: {e}"
        except Exception as e:
            return None, f"Error processing truck {truck_id}: {e}"
        
    total_sessions = sum(len(sessions) for sessions in truck_sessions_dict.values())
    
    return total_sessions, truck_sessions_dict

def validate_time(t1, t2):
    if t1 is None:
        now = datetime.datetime.now()
        t1 = datetime.datetime(now.year, now.month, 1).strftime('%Y%m%d%H%M%S')
    else:
        try:
            datetime.datetime.strptime(t1, '%Y%m%d%H%M%S')
        except ValueError:
            return None, None, ("Invalid 'from' date format. Use yyyymmddhhmmss", 400)
        
    if t2 is None:
        t2 = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    else:
        try:
            datetime.datetime.strptime(t2, '%Y%m%d%H%M%S')
        except ValueError:
            return None, None, ("Invalid 'to' date format. Use yyyymmddhhmmss", 400)
    
    if t1 > t2:
        return None, None, ("Start time must be before end time", 400)
    
    return t1, t2, None

def get_billdb_data(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # SQL query to get provider name and count trucks
        name_and_count_query = """
        SELECT 
            p.name AS provider_name,
            COUNT(t.id) AS truck_count
        FROM 
            Provider p
        LEFT JOIN 
            Trucks t ON p.id = t.provider_id
        WHERE 
            p.id = %s
        GROUP BY 
            p.id, p.name
        """

        trucks_query = """
        SELECT
            t.id, t.model, t.year, t.license_plate  # or whatever truck fields you need
        FROM
            Trucks t
        WHERE
            t.provider_id = %s
        """

        cursor.execute(name_and_count_query, (id,))
        name_and_truckcount = cursor.fetchone()

        cursor.execute(trucks_query, (id,))
        trucks_list = cursor.fetchall()
        
        cursor.close()
        conn.close()
            
        if name_and_truckcount is not None and trucks_list is not None:
            return True, True, name_and_truckcount["name"], name_and_truckcount["truckCount"], trucks_list
        else:
            # Provider not found
            return False, "Provider not found", None, None, None
        
    except Exception as e:
        # Database or other error
        return False, f"Error retrieving data from database: {str(e)}", None, None, None
    
def create_product(product_name, session_count, amount_kg, rate_agorot):
    pay = amount_kg * rate_agorot
    return {
        "product": product_name,
        "count": str(session_count),  # Must be a string per the spec
        "amount": amount_kg,          # Total kg (integer)
        "rate": rate_agorot,          # Price in agorot (integer)
        "pay": pay                    # Total payment in agorot (integer)
}


if __name__ == '__main__':
    # TODO: Check if host 0.0.0.0 is the correct way to do this
    app.run(host='0.0.0.0', debug=True, port=5000)
