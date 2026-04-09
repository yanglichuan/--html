import pymysql
import sys

# Connection details
HOST = '115.191.33.218'
USER = 'root'
PASSWORD = '12345678aA'
DB_NAME = 'usersystem'

def create_reservoir():
    print(f"Connecting to database '{DB_NAME}' to create a reservoir...")
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
                # 1. SQL to create the table
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS reservoirs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL COMMENT '水库名称',
                    location VARCHAR(255) COMMENT '地理位置',
                    capacity DECIMAL(15, 2) COMMENT '总库容(万立方米)',
                    current_level DECIMAL(15, 2) COMMENT '当前水位/库容',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
                print("Executing: CREATE TABLE reservoirs...")
                cursor.execute(create_table_sql)
                
                # 2. SQL to insert a sample reservoir
                insert_sql = """
                INSERT INTO reservoirs (name, location, capacity, current_level)
                VALUES (%s, %s, %s, %s)
                """
                sample_data = ("新安江水库", "浙江省杭州市淳安县", 178.4, 150.2)
                
                print(f"Executing: INSERT INTO reservoirs ({sample_data[0]})...")
                cursor.execute(insert_sql, sample_data)
                
                # IMPORTANT: Commit the transaction
                connection.commit()
                print("Transaction committed successfully!")
                
                # 3. Query the results
                print("\nFetching data from 'reservoirs' table:")
                cursor.execute("SELECT * FROM reservoirs")
                results = cursor.fetchall()
                for row in results:
                    print(row)
                    
        except Exception as e:
            # Rollback in case of error
            connection.rollback()
            print(f"An error occurred, transaction rolled back: {e}")
        finally:
            connection.close()
            print("\nConnection closed.")
            
    except pymysql.MySQLError as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    create_reservoir()
