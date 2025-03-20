import json
from flask import Flask, request, jsonify
from datetime import datetime
from io import TextIOWrapper
import mysql.connector
import db
import os
import csv


app = Flask(__name__)

mydb = db.connect_db()

cursor = mydb.cursor(dictionary=True, buffered=True)

# Converts LBS to kg, Returns int per containers_registered table.
def convert_weight(weight):
    # LBS to Kg conversion
    new_weight = int(weight) * 0.45359237
    return int(new_weight)

@app.route('/')
def home():
    return "Hello, Welcome to weight software!"


# http://localhost:5000/item/truck1?from=20230301000000&to=20230302235959
@app.route("/item/<id>", methods=["GET"])
def get_item(id):
    
    try:
        from_time = datetime.strptime(request.args.get('from', datetime.now().replace(day=1).strftime("%Y%m%d") + "000000"), "%Y%m%d%H%M%S")
        to_time = datetime.strptime(request.args.get('to', datetime.now().strftime("%Y%m%d%H%M%S")), "%Y%m%d%H%M%S")
    except ValueError:
        return "Invalid date format. Use YYYYMMDDHHMMSS.", 400

    try:
        # Validate that 'from' time is earlier than 'to' time
        if from_time > to_time :
            return "The 'from' time must be earlier than the 'to' time.", 400


        cursor.execute("SELECT truck FROM transactions WHERE truck = %s", (id,))
        id_check = cursor.fetchone()  # Fetch one result 

        if not id_check:
            return jsonify({"error": "Item not found"}), 404 

        # Construct SQL query
        query = """
        SELECT 
            truck, 
            MAX(truckTara) AS truckTara, 
            GROUP_CONCAT(DISTINCT session ORDER BY session SEPARATOR ', ') AS sessions
        FROM transactions
        WHERE datetime BETWEEN %s AND %s
        AND truck = %s
        GROUP BY truck
        """
        params = (from_time, to_time, id) 

        cursor.execute(query, params)
        result = cursor.fetchone()


        return jsonify(result)
    
    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/batch-weight", methods=["POST"])
def containers_insert():
    
    def insert_into_db(container_id, weight, unit):
        try:
            cursor.execute(
                """
                INSERT INTO containers_registered (container_id, weight, unit)
                VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE weight = VALUES(weight) """,
                (container_id, weight, unit)
            )

            mysql.commit()
        except Exception as e:
            print(f"Error inserting into database: {str(e)}")   

    try:
        filename = request.get_json().get("file")
        if not filename:
            return {"error": "No file part in the request"}, 400

        file_path = os.path.join("./in/", filename)

        if not os.path.isfile(file_path):
            return {"error": "File not found"}, 404

        file_extension = os.path.splitext(file_path)[1].lower()

        # Process JSON files
        if file_extension == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for entry in data:
                container_id = entry.get("id")
                weight = entry.get("weight")
                unit = entry.get("unit")

                if isinstance(weight, str):
                    weight = weight.strip()  # Remove spaces if it's a string
                    weight =  None  # Convert to int if not empty
                else:
                    try : 
                        weight = int(weight)
                    except ValueError:
                        weight = None
                if unit == "lbs": 
                    weight=convert_weight(weight)
                    unit="kg"

                if container_id is not None:
                    insert_into_db(container_id, weight, unit)

        # Process CSV files
        elif file_extension == '.csv':
            with open(file_path, 'r', encoding='utf-8') as f:
                csv_reader = csv.DictReader(f)
                
                headers = next(csv_reader)  # Extract the first line as headers
                unit_type = "lbs" if "lbs" in headers else 'kg'

                for row in csv_reader:
                    
                    unit = "kg"
                    container_id = row.get("id")
                    weight = row.get("lbs") if unit_type == "lbs" else row.get("kg")

                    if weight.strip() == "":
                        weight = None  # Handle empty weight values
                    else:
                        try : 
                            weight = int(weight)
                        except ValueError:
                            weight = None

                    if unit_type == "lbs":
                        weight = convert_weight(weight)

                    if container_id is not None:
                        insert_into_db(container_id, weight, unit)

        else:
            return {"error": "Unsupported file type. Only CSV and JSON are allowed."}, 400

        return {"message": "File processed successfully"}, 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    




# http://localhost:5000/session/1619874477.123456
@app.route("/session/<id>", methods=["GET"])
def get_session(id):

    try:
        cursor.execute("SELECT truck FROM transactions WHERE session = %s", (id,))
        id_check = cursor.fetchone()  # Fetch one result 

        if not id_check:
            return jsonify({"error": "Item not found"}), 404 

        query = """
        SELECT session, truck,
        MAX(bruto) AS bruto,
        MAX(produce) AS produce,
        MAX(truckTara) AS truckTara,
        MAX(neto) AS neto 
            FROM transactions
            WHERE session = %s
            GROUP BY session, truck
            """

        cursor.execute(query, (id,))
        result = cursor.fetchone()


        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET']) ##DONE
def healthcheck():
      if mydb.is_connected():
        cursor.execute("SELECT 1;") 
        cursor.fetchall()  # Ensure all results are read
        return "OK", 200
      else:
          return "Failure", 500

@app.route('/weight', methods=['GET']) ##DONE
def get_weight():
    try:
        from_time = datetime.strptime(request.args.get('from', datetime.now().strftime("%Y%m%d") + "000000"), "%Y%m%d%H%M%S")
        to_time = datetime.strptime(request.args.get('to', datetime.now().strftime("%Y%m%d%H%M%S")), "%Y%m%d%H%M%S")
    except ValueError:
        return "Invalid date format. Use YYYYMMDDHHMMSS.", 400
    filter_by = request.args.get('filter', "in,out,none").split(',')

    # Validate that 'from' time is earlier than 'to' time
    if from_time > to_time :
        return "The 'from' time must be earlier than the 'to' time.", 400
    
    try:        
        # Construct SQL query
        query = """
        SELECT id, direction, bruto, neto, produce, containers 
        FROM transactions
        WHERE datetime BETWEEN %s AND %s
        AND direction IN ({})
        """.format(",".join(["%s"] * len(filter_by)))  # Creates placeholders dynamically
        
        params = [from_time, to_time] + filter_by
        
        cursor.execute(query, params)
        result = cursor.fetchall()

        
        return jsonify(result)
    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500

@app.route('/weight', methods=['POST']) ##DONE
def info_insert():
    # Ensure correct Content-Type
    if request.content_type != 'application/json':
        return ({"error": "Content-Type must be application/json"}), 415
    
    #set up the last session id to maintaine continues
    def fetch_session_id():
        mysql = db.connect_db()
        cursor = mysql.cursor(dictionary=True)
        cursor.execute(""" SELECT session FROM transactions ORDER BY session DESC""")
        result = cursor.fetchone()
        if result is None:
            return 0
        return result["session"]

    # Parse JSON payload
    data = request.json
    direction = data.get('direction')  # "in", "out", or "none"
    truck = data.get('truck', 'na')  # Default to "na" if no truck is provided
    containers = data.get('containers', '')  # Comma-separated container IDs
    weight = data.get('weight')
    unit = data.get('unit', 'kg')  # Default to "kg"
    force = data.get('force', False)  # Default is False
    produce = data.get('produce', 'na')  # Default to "na"
    current_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Converts weight from Pounds to Kilograms 
    if unit.lower() == "lbs" or unit.lower() == "lb":
        weight = convert_weight(weight)

    # Validate required fields
    if not direction or weight is None or not truck or not containers:
        return ({"error": "Missing required fields"}), 400

    mysql = db.connect_db()
    cursor = mysql.cursor(dictionary=True)

    # Direction: "in"
    if direction == "in":
        # Check if there's an "in" session for the same truck
        cursor.execute(""" SELECT * FROM transactions WHERE truck = %s AND direction = 'in' AND session NOT IN 
                    (SELECT session FROM transactions WHERE direction = 'out') LIMIT 1; """, (truck, ))
        existing_in = cursor.fetchone()

        if existing_in and not force:
            return {"error": "An active 'in' session already exists. Use force=true to overwrite."}, 500
        # Insert a new "in" session
        session_id= fetch_session_id()
        cursor.execute(""" SELECT truck FROM transactions WHERE truck = %s AND direction = 'in' LIMIT 1; """, (truck, ))
        truck_exist = cursor.fetchone()
        if force and truck_exist: ## add check for the same trackid
            cursor.execute("UPDATE transactions "
                "SET session = %s, truck = %s, direction = %s, bruto = %s, datetime = %s, containers = %s, produce = %s "
                "WHERE truck = %s",
                (session_id, truck, direction, weight, current_date, containers, produce, truck))
            mysql.commit()
            return {"session": session_id, "truck": truck, "bruto": weight}, 200
        session_id +=1
        cursor.execute("INSERT INTO transactions (session, truck, direction, bruto, datetime, containers, produce) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)", (session_id, truck, direction, weight, current_date, containers, produce))
        mysql.commit()
        return {"session": session_id, "truck": truck, "bruto": weight}, 200


    # Direction: "out"
    elif direction == "out":
        # Get the latest "in" session for this truck
        cursor.execute(""" SELECT * FROM transactions WHERE truck = %s AND direction = 'in' AND session NOT IN 
                    (SELECT session FROM transactions WHERE direction = 'out') LIMIT 1; """, (truck,))
        last_in = cursor.fetchone()

        if not last_in:
            return {"error": "No 'in' session found for this truck. Cannot proceed with 'out'."}

        # Calculate neto (Fruits)
        session_id=last_in.get("session")
        try:
            bruto_weight = last_in["bruto"] # Get bruto from last_in
            truck_tara = int(weight)  # Current truck weight
            container_weight = db.container_data(containers)  # Weight of containers
            net_weight = bruto_weight - truck_tara - container_weight
            
        except Exception as e:
            return {"error": f"Failed to calculate net weight: {e}"}, 500


        # Insert a new "out" session
        # Here we need to get tara weight, truck id, calculate neto as input
        cursor.execute("INSERT INTO transactions (session, truck, direction, truckTara, datetime, containers, neto) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)", (session_id, truck, direction, truck_tara, current_date, containers, net_weight))
        mysql.commit()
        return {
            "sesssion": last_in["session"],
            "truck": truck,
            "truckTara": truck_tara,
            "neto": net_weight
        }

    # Direction: "none"
    elif direction == "none":
        cursor.execute(""" SELECT direction FROM transactions ORDER BY datetime DESC LIMIT 1;""")
        result = cursor.fetchone()
        if 'in' in result['direction']:
            return ("Error, na after in detected"), 500
        session_id= fetch_session_id()
        session_id +=1
        cursor.execute("INSERT INTO transactions (session, direction, datetime) VALUES (%s, %s, %s)", (session_id, direction, current_date))
        mysql.commit()
        return {"id": session_id, "truck": "na", "bruto": weight, "result":result}, 200

    # If invalid direction
    return {"Error": "Page Not Found, try different route"}, 404
 


@app.route('/unknown', methods=['GET'])
def get_unknown():
    
    try:        
        # Intializing a list for empty containers
        contaniers_empty = []

        # SQL querry for empty_containers, where whight is null
        query = """
        SELECT container_id from containers_registered WHERE weight IS NULL
        """     

        cursor.execute(query)
        result = cursor.fetchall()

        # indexing the specifc ID's from the querry to the containers_empty list
        for id in result:
            contaniers_empty.append(id["container_id"])
        
        # Return the list of empty continare id's 
        return {"id": contaniers_empty}, 200


    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
