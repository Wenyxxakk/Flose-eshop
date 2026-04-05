import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'tvoje_tajne_heslo_2025_tady_nebezpecne'

    # ŠKOLNÍ MySQL databáze 
    DB_HOST = 'dbs.spskladno.cz'
    DB_PORT = 3306
    DB_USER = 'student19'      
    DB_PASSWORD = 'spsnet'               
    DB_NAME = 'vyuka19'           
