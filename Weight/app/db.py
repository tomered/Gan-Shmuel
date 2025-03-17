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


