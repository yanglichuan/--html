import pymysql
import sys

# Connection details
HOST = '115.191.33.218'
USER = 'root'
PASSWORD = '12345678aA'
DB_NAME = 'usersystem'  # Target database

def explore():
    print(f"Connecting to database '{DB_NAME}'...")
    try:
        connection = pymysql.connect(
            host=HOST,
            user=USER,
            password=PASSWORD,
            database=DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print("Connected successfully!\n")
        
        try:
            with connection.cursor() as cursor:
                # 1. List Tables
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                
                if not tables:
                    print(f"No tables found in database '{DB_NAME}'.")
                    return

                print(f"Tables in '{DB_NAME}':")
                table_names = []
                for table in tables:
                    name = list(table.values())[0]
                    table_names.append(name)
                    print(f"- {name}")
                
                # 2. Describe each table
                for table_name in table_names:
                    print(f"\n--- Schema for table: {table_name} ---")
                    cursor.execute(f"DESCRIBE {table_name}")
                    columns = cursor.fetchall()
                    print(f"{'Field':<20} | {'Type':<20} | {'Null':<5} | {'Key':<5}")
                    print("-" * 60)
                    for col in columns:
                        print(f"{col['Field']:<20} | {col['Type']:<20} | {col['Null']:<5} | {col['Key']:<5}")
                    
                    # 3. Show first 5 rows
                    print(f"\nFirst 5 rows of {table_name}:")
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                    rows = cursor.fetchall()
                    if rows:
                        for row in rows:
                            print(row)
                    else:
                        print("(Table is empty)")
                    
        finally:
            connection.close()
            print("\nConnection closed.")
            
    except pymysql.MySQLError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    explore()
