import mysql.connector
from mysql.connector import Error

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host='dbs.spskladno.cz',
            user='student19',
            password='spsnet',
            database='vyuka19',
            use_pure=True
        )
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Chyba připojení k MySQL: {e}")
        return None
