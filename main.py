import psycopg2
from sshtunnel import SSHTunnelForwarder

username = "jj7485"
passwd = "itzme@170605Kr"
dbname = "p320_16"



try:
    with SSHTunnelForwarder(('starbug.cs.rit.edu', 22),
                            ssh_username=username,
                            ssh_password=passwd,
                            remote_bind_address=('127.0.0.1', 5432)) as server:
        server.start()
        print("SSH tunnel established")

        params = {
            'database': dbname,
            'user': username,
            'password': passwd,
            'host': 'localhost',
            'port': server.local_bind_port
        }

        conn = psycopg2.connect(**params)
        curs = conn.cursor()
        print("Database connection established")
        # Query to get all games from the specified collection

        print("Starting program.......................................")
        while(True):
            print('''Welome! To proceed Choose one of te following
                    1 - Login (for exisgting users)
                    2 - Sign up
                    3 - Quit
                ''')
            x = int(input("->||"))
            if(x == 1):
                print("Login:")
                uname = input("Username:")
                password = input("Password:")
                print("Logging you in..............")
                query = '''
                        
                        '''
            



        conn.close()

except Exception as e:
    print(f"Error: {e}")