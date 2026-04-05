import mysql.connector
from mysql.connector import Error
from .config import Config

def get_db_connection():
    """Připojí se k školní MySQL databázi"""
    try:
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        print("Připojeno k školní databázi OK!")
        return conn
    except Error as err:
        print(f"Chyba připojení k DB: {err}")
        return None

def init_db():
    """Vytvoří tabulky v školní DB, pokud neexistují"""
    conn = get_db_connection()
    if not conn:
        print("Nepodařilo se připojit – tabulky nevytvořeny")
        return

    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            price DECIMAL(10,2) NOT NULL,
            image_url VARCHAR(255),
            stock INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    cursor.close()
    conn.close()
    print("Tabulky v školní DB zkontrolovány / vytvořeny")
