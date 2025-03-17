from flask import g
import mysql.connector


def connect_db():
    mydb = mysql.connector.connect(
        host='db_gs',
        user='root',
        password='root',
        database='transactions'
    )
    return mydb



def process_weight(direction, truck, containers, weight, unit, force, produce, session_id):
    db = connect_db()  # Get DB connection
    cursor = db.cursor(dictionary=True)

    # Generate a unique ID for session

    # Direction: "in"
    if direction == "in":
        # Check if there's an "in" session for the same truck
        cursor.execute("SELECT * FROM sessions WHERE truck_license = %s AND direction = 'in' ORDER BY datetime DESC LIMIT 1", (truck,))
        existing_in = cursor.fetchone()

        if existing_in and not force:
            return {"error": "An active 'in' session already exists. Use force=true to overwrite."}

        # Insert a new "in" session
        cursor.execute("INSERT INTO sessions (session_id, truck_license, direction) VALUES (%s, %s, %s)", (session_id, truck, direction))
        db.commit()
        return {"id": session_id, "truck": truck, "bruto": weight}

    # Direction: "out"
    elif direction == "out":
        # Get the latest "in" session for this truck
        cursor.execute("SELECT * FROM sessions WHERE truck_license = %s AND direction = 'in' ORDER BY datetime DESC LIMIT 1", (truck,))
        last_in = cursor.fetchone()

        if not last_in:
            return {"error": "No 'in' session found for this truck. Cannot proceed with 'out'."}

        # Calculate net weight if container weights are known (logic may vary)
        net_weight = weight - last_in.get("weight", 0)
        truck_tara = last_in.get("weight", 0)

        # Insert a new "out" session
        cursor.execute("INSERT INTO sessions (session_id, truck_license, direction) VALUES (%s, %s, %s)", (last_in["session_id"], truck, direction))
        db.commit()
        return {
            "id": last_in["session_id"],
            "truck": truck,
            "bruto": weight,
            "truckTara": truck_tara,
            "neto": net_weight
        }

    # Direction: "none"
    elif direction == "none":
        # Create a standalone session
        cursor.execute("INSERT INTO sessions (session_id, truck_license, direction) VALUES (%s, %s, %s)", (session_id, truck, direction))
        db.commit()
        return {"id": session_id, "truck": "na", "bruto": weight}

    # If invalid direction
    return {"error": "Invalid direction specified"}


