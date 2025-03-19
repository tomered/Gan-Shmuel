import random
from flask import g
import mysql.connector

def connect_db():
    mydb = mysql.connector.connect(
        host='db_gs',
        user='root',
        password='root',
        database='weight'
    )
    return mydb

def container_data(containers):
    mysql = connect_db()
    cursor = mysql.cursor(dictionary=True)

    # Initialize total weight
    sum = 0
    converted_list = containers.split(",")
    for container in converted_list:
        # Fetch container weight from the database
        try:
            cursor.execute("SELECT weight FROM containers_registered WHERE container_id = %s", (container, ))
            result = cursor.fetchone()
            sum+=result["weight"]
        except:
            return (f"No data available for Container: {container} "), 500

    cursor.close()
    mysql.close()

    return sum


