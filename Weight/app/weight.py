# from flask import Flask, redirect, url_for, render_template, Response, request, jsonify
# import os
# import uuid
# import db


# app = Flask(__name__)

# @app.route('/health', methods=['GET'])
# def healthcheck():
#     ## add test to db
#     return ('OK', 200)

# @app.route('/weight', methods=['POST'])
# def info_insert():
#     data = request.json
#     direction= data.get('direction')
#     truck = data.get('truck', 'na')   # License plate, or "na" if not provided
#     containers = data.get('containers', '')
#     weight = data.get('weight')
#     unit = data.get('unit', 'kg')     # Default to kg
#     force = data.get('force', False)  # Default is false
#     produce = data.get('produce', 'na')
#     # session_id = str(uuid.uuid4())
#     result = db.process_weight(direction, truck, containers, weight, unit, force, produce)

#     if not direction or weight is None:
#         return jsonify({"error":"Missing required fileds"}), 400
#     if direction == 'out':
#     # Ensure necessary fields for "out" response
#         return jsonify({
#         "id": result.get("id"),
#         "truck": result.get("truck", "na"),
#         "bruto": result.get("bruto"),
#         "truckTara": result.get("truckTara"),
#         "neto": result.get("neto", "na")
#         })
#     else:
#         # Default response for "in" and "none"
#         return jsonify({
#             "id": result.get("id"),
#             "truck": result.get("truck", "na"),
#             "bruto": result.get("bruto")
#         })
#     # if direction == 'in':
#     #     return ({ "truck": f"{truck}"})
#     # result = db.process_weight(direction, truck, containers, weight, unit, force, produce)
#     # return ({"truck": f"{truck}", "directon": f"{direction}"})
#     # Validate and process `data`, interact with the database.
#     # Example:
#     # direction = data.get('direction')
#     # if direction == 'in':
#     #     # Generate a new session ID, record data.
#     # result = process_weight(direction, truck, containers, weight, unit, force, produce, session_id)
#     # return jsonify(result)

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", debug=True)



from flask import Flask, request, jsonify
import uuid
import db

app = Flask(__name__)

# Close DB connection after each request
# @app.teardown_appcontext
# def close_connection(exception):
#     db.close_db()

@app.route('/health', methods=['GET'])
def healthcheck():
    return ('OK', 200)

@app.route('/weight', methods=['POST'])
def info_insert():
    # Ensure correct Content-Type
    if request.content_type != 'application/json':
        return jsonify({"error": "Content-Type must be application/json"}), 415

    # Parse JSON payload
    data = request.json
    direction = data.get('direction')  # "in", "out", or "none"
    truck = data.get('truck', 'na')  # Default to "na" if no truck is provided
    containers = data.get('containers', '')  # Comma-separated container IDs
    weight = data.get('weight')
    unit = data.get('unit', 'kg')  # Default to "kg"
    force = data.get('force', False)  # Default is False
    produce = data.get('produce', 'na')  # Default to "na"

    # Validate required fields
    if not direction or weight is None:
        return jsonify({"error": "Missing required fields"}), 400

    # Process request using the `process_weight` function from db.py
    result = ({'direction': f"{direction}", 'truck': f"{truck}", "container": f"{containers}", "weight": f"{weight}", "unit": f"{unit}", "force": f"{force}", "produce":f"{produce}"})
    return (result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
