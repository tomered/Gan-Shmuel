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
    result = 0

    for container in containers:
        # Fetch container weight from the database
        cursor.execute("""SELECT SUM(weight) FROM containers_registered WHERE container_id = %s""", (container,))
        result = cursor.fetchone()

        if result and 'weight' in result:
            return result


    cursor.close()
    mysql.close()

    return result


