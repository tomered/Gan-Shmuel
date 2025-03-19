import json
from flask import Flask, request, jsonify
from datetime import datetime
import mysql.connector
import db
import os


app = Flask(__name__)

mydb = db.connect_db()

cursor = mydb.cursor(dictionary=True, buffered=True)


@app.route('/')
def home():
    return "Hello, Welcome to weight software!"


# http://localhost:5000/item/truck1?from=20230301000000&to=20230302235959
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
        if not force:
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
