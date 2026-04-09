# Database Connection Setup

This directory contains a Python script to connect to your remote MySQL server.

## Prerequisites

1.  **Python 3**: Ensure Python 3 is installed.
2.  **Dependencies**: Install the required packages.
    ```bash
    pip install -r requirements.txt
    ```

## Connecting

Run the script:
```bash
python3 connect_db.py
```

## Creating a Reservoir (Practice)

I've added a script to practice DDL (Data Definition Language) and DML (Data Manipulation Language).

Run the creation script:
```bash
python3 create_reservoir.py
```

This script will:
1. Create a `reservoirs` table if it doesn't exist.
2. Insert a sample record for "新安江水库".
3. Commit the transaction and display the data.

## Exploring the Database


I've added a script to explore the `usersystem` database specifically.

Run the exploration script:
```bash
python3 explore_db.py
```

This script will:
1. List all tables in the `usersystem` database.
2. Show the schema (columns, types) for each table.
3. Display the first 5 rows of data from each table.


If you see an error like `Host 'x.x.x.x' is not allowed to connect to this MySQL server`, you need to allow remote connections on your server.

1.  **SSH into your server**:
    ```bash
    ssh root@115.191.33.218
    ```
    (Password: `12345678aA`)

2.  **Login to MySQL**:
    ```bash
    mysql -u root -p
    ```
    (Enter the same password)

3.  **Grant Permissions**:
    Run the following SQL commands in the MySQL shell:
    ```sql
    USE mysql;
    -- Check existing users
    SELECT User, Host FROM user;
    
    -- Allow root to connect from anywhere (Be careful in production!)
    UPDATE user SET Host='%' WHERE User='root' AND Host='localhost';
    -- OR create a new user if root doesn't exist or you want a dedicated user
    -- CREATE USER 'root'@'%' IDENTIFIED BY '12345678aA';
    -- GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;
    
    FLUSH PRIVILEGES;
    EXIT;
    ```

4.  **Try connecting again** from your local machine.
