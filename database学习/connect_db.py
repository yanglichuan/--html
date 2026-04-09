import pymysql
import sys

# Connection details
HOST = '115.191.33.218'
USER = 'root'
PASSWORD = 'root'
PORT = 3306

def connect():
    print(f"Attempting to connect to MySQL server at {HOST}...")
    try:
        connection = pymysql.connect(
            host=HOST,
            user=USER,
            password=PASSWORD,
            port=PORT,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print("Successfully connected!")
        
        try:
            with connection.cursor() as cursor:
                # Execute a simple query
                cursor.execute("SELECT VERSION()")
                result = cursor.fetchone()
                print(f"Database Version: {result['VERSION()']}")
                
                # Show databases
                cursor.execute("SHOW DATABASES")
                databases = cursor.fetchall()
                print("\nAvailable Databases:")
                for db in databases:
                    print(f"- {db['Database']}")
                    
        finally:
            connection.close()
            print("\nConnection closed.")
            
    except pymysql.MySQLError as e:
        print(f"Error connecting to MySQL: {e}")
        sys.exit(1)

if __name__ == "__main__":
    connect()
