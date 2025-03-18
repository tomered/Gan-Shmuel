from flask import Flask, request, jsonify
from datetime import datetime
import mysql.connector
import db

app = Flask(__name__)

mydb = db.connect_db()

cursor = mydb.cursor(dictionary=True, buffered=True)


@app.route('/')
def home():
    return "Hello, From weight server!"

# Close DB connection after each request
# @app.teardown_appcontext
# def close_connection(exception):
#     db.close_db()

items_data = {
    "truck1": {
        "tara": 800,
        "sessions": ["1619874477.123456", "1619874487.234567"]
    },
    "container1": {
        "tara": "na",
        "sessions": ["1619874497.345678"]
    }
}


@app.route("/item/<id>", methods=["GET"])
def get_item(id):
    try:
        
        from_time = request.args.get('from', datetime.now().replace(day=1).strftime("%Y%m%d") + "000000")
        to_time = request.args.get('to', datetime.now().strftime("%Y%m%d%H%M%S"))


        cursor.execute("SELECT truck FROM transactions WHERE truck = %s", (id,))
        id_check = cursor.fetchone()  # Fetch one result 

        if not id_check:
            return jsonify({"error": "Item not found"}), 404 

        # Construct SQL query
        query = """
        SELECT 
            truck, 
            truckTara, 
            GROUP_CONCAT(DISTINCT session ORDER BY session SEPARATOR ', ') AS sessions
        FROM transactions
        WHERE datetime BETWEEN %s AND %s
        AND truck = %s
        GROUP BY truck, truckTara
        """
        params = (from_time, to_time, id) 

        cursor.execute(query, params)
        result = cursor.fetchone()


        return jsonify(result)
    
    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# http://localhost:5000/session/1619874477.123456
@app.route("/session/<id>", methods=["GET"])
def get_session(id):
    session = next((item for item in sessions_data if item['id'] == id), None)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    response = {
        "id": session["id"],
        "direction": session["direction"],
        "bruto": session["bruto"],
    }
    if session["direction"] == "out":
        response["truckTara"] = 1000
        response["neto"] = session["neto"] if session["neto"] != "na" else "na"
    return jsonify(response), 200


@app.route('/health', methods=['GET'])
def healthcheck():
      if mydb.is_connected():
        cursor.execute("SELECT 1;") 
        cursor.fetchall()  # Ensure all results are read
        return "OK", 200
      else:
          return "Failure", 500

@app.route('/weight', methods=['GET'])
def get_weight():

    from_time = request.args.get('from',datetime.now().strftime("%Y%m%d") + "000000")
    to_time = request.args.get('to', datetime.now().strftime("%Y%m%d%H%M%S"))
    filter_by = request.args.get('filter', "in,out,none").split(',')
    
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

# Generate a unique ID for session


@app.route('/weight', methods=['POST'])
def info_insert():
    # Ensure correct Content-Type
    if request.content_type != 'application/json':
        return ({"error": "Content-Type must be application/json"}), 415

    # Parse JSON payload
    data = request.json
    direction = data.get('direction')  # "in", "out", or "none"
    truck = data.get('truck', 'na')  # Default to "na" if no truck is provided
    containers = data.get('containers', '')  # Comma-separated container IDs
    weight = data.get('weight')
    # unit = data.get('unit', 'kg')  # Default to "kg"
    force = data.get('force', False)  # Default is False
    produce = data.get('produce', 'na')  # Default to "na"
    current_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')


    # Validate required fields
    if not direction or weight is None:
        return ({"error": "Missing required fields"}), 400
    
    mysql = db.connect_db()  # Get DB connection
    cursor = mysql.cursor(dictionary=True)
    #set up the last session id to maintaine continues
    # cursor.execute(""" SELECT session FROM transactions ORDER BY session DESC""")
    def fetch_session_id():
        mysql = db.connect_db()  # Get DB connection
        cursor = mysql.cursor(dictionary=True)
        # cursor.execute("SELECT MAX(session) FROM transactions LIMIT 1")  # Adjust table and column names as needed

        # set up the last session id to maintaine continues
        cursor.execute(""" SELECT session FROM transactions ORDER BY session DESC""")
        result = cursor.fetchone()
        if result is None:
            return 0
        return result


    # Direction: "in" DONE!!!!!!
    if direction == "in":
        # Check if there's an "in" session for the same truck
        cursor.execute(""" SELECT * FROM transactions WHERE truck = %s AND direction = 'in' AND session NOT IN 
                       (SELECT session FROM transactions WHERE direction = 'out') LIMIT 1; """, (truck, ))
        existing_in = cursor.fetchone()


        if existing_in and not force:
            return {"error": "An active 'in' session already exists. Use force=true to overwrite."}
        # Insert a new "in" session
        session_id= fetch_session_id()
        cursor.execute("INSERT INTO transactions (session, truck, direction, bruto, datetime, containers, produce) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)", (session_id, truck, direction, weight, current_date, containers, produce))
        mysql.commit()
        return {"session": session_id, "truck": truck, "bruto": weight}, 200

    # Direction: "out"
    elif direction == "out":
        # Get the latest "in" session for this truck
        cursor.execute(""" SELECT * FROM transactions WHERE truck = %s AND direction = 'in' AND session NOT IN 
                       (SELECT session FROM transactions WHERE direction = 'out') LIMIT 1; """, (truck, session_id))
        last_in = cursor.fetchall()

        if not last_in:
            return {"error": "No 'in' session found for this truck. Cannot proceed with 'out'."}

        # Calculate neto (Fruits)
    
        truck_tara = weight
        net_weight = (int(last_in.get("bruto", 0)) - int(truck_tara) - int(db.container_data(containers)))

        # Insert a new "out" session
        # Here we need to get tara weight, truck id, calculate neto as input
        cursor.execute("INSERT INTO transactions (session, truck, direction, truckTara, datetime, containers, neto) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)", (session_id, truck, direction, truck_tara, current_date, containers, net_weight))
        mysql.commit()
        return {
            "id": last_in["session"],
            "truck": truck,
            "truckTara": truck_tara,
            "neto": net_weight
        }

    # Direction: "none"
    elif direction == "none":
        # Create a standalone session
        cursor.execute("INSERT INTO transactions (session, direction) VALUES ('%s', '%s', '%s')", (session_id, truck, direction))
        mysql.commit()
        return {"id": session_id, "truck": "na", "bruto": weight}

    # If invalid direction
    return {"error": "Invalid direction specified"}
    

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
