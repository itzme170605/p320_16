import psycopg2
from sshtunnel import SSHTunnelForwarder



class Connection:
    def __init__(self, username, passwd, dbName) :
        self.username = username
        self.password = passwd
        self.dbName = dbName

        try:
            with SSHTunnelForwarder(('starbug.cs.rit.edu', 22),ssh_username=self.username,ssh_password=self.password,remote_bind_address=('127.0.0.1', 5432)) as server:
                server.start()
                print("SSH tunnel established")
                params = {
                    'database': self.dbName,
                    'user': self.username,
                    'password': self.password,
                    'host': 'localhost',
                    'port': server.local_bind_port
                }


                self.conn = psycopg2.connect(**params)
                self.curs = self.conn.cursor()
                print("Database connection established")

                self.curs.execute("SELECT * from users;")
                print("The number of parts: ", curs.rowcount)
                row = self.curs.fetchone()
                while row is not None:
                    print(row)
                    row = self.curs.fetchone()
            return self.curs
        except:
            print("Connection failed")
