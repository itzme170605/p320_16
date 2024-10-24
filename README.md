# p320_16
Repo for PDM project 

# setup for python
python
What follows is a sample of python3 code that can be used to establish a connection to starbug.cs.rit.edu and then perform other operations. Be sure to replace "YOUR_CS_USERNAME" with your CS username and "YOUR_CS_PASSWORD" with your CS password and "YOUR_DB_NAME" with the database name you are connecting to.

Notice the SSH tunnel is in a with clause. Once you leave that with block the SSH tunnel will close.

import psycopg2
from sshtunnel import SSHTunnelForwarder

username = "YOUR_CS_USERNAME"
password = "YOUR_CS_PASSWORD"
dbName = "YOUR_DB_NAME"


try:
    with SSHTunnelForwarder(('starbug.cs.rit.edu', 22),
                            ssh_username=username,
                            ssh_password=password,
                            remote_bind_address=('127.0.0.1', 5432)) as server:
        server.start()
        print("SSH tunnel established")
        params = {
            'database': dbName,
            'user': username,
            'password': password,
            'host': 'localhost',
            'port': server.local_bind_port
        }


        conn = psycopg2.connect(**params)
        curs = conn.cursor()
        print("Database connection established")

        //DB work here....

        conn.close()
except:
    print("Connection failed")
