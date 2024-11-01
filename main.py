import datetime
import psycopg2
from sshtunnel import SSHTunnelForwarder
import os
import random
import time

username = "jj7485"
passwd = "itzme@170605Kr"
dbname = "p320_16"
user_state = 0
user_username = ''


# returns cursor object
def connection(username, passwd):
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
            print("Starting program.......................................")
            return conn, curs
    except Exception as e:
        print("An error occurred:", e)


def close(conn):
    conn.close()
    print("Database connection closed.")

def homepage(curs):
    global user_state
    while(True):
        print('''Signed in! 
''')



def login(curs):
    global user_state
    while True:
        print('''Welcome! To proceed choose one of the following:
                1 - Login (for existing users)
                2 - Sign up
                3 - Quit
            ''')
        try:
            x = int(input("->|| "))
        except ValueError:
            print("Invalid input. Please enter a number.")
            continue
        
        if x == 1:
            os.system('cls')
            print("Login")
            uname = input("Username: ")
            password = input("Password: ")
            print("Logging you in..............")
            
            # Parameterized query to prevent SQL injection
            query = "SELECT * FROM users WHERE username = %s AND password = %s;"
            curs.execute(query, (uname, password))
            
            # Check if any rows are returned
            if curs.fetchone():
                print("Login successful!")
                user_state = 2
                user_passwd = passwd
                user_username = user_username
                return user_state
            else:
                print("Invalid username or password. Try again!")
                
        elif x == 2:
            os.system('cls')
            print("Sign up:")
            print("Please carefully enter information:")
            fname = input("First name: ")
            lname = input("Last name: ")
            uname = input("Username: ")
            passwd = input("Password: ")
            dob = input("DOB (YYYY-MM-DD): ")
            creation_date =  datetime.now().strftime("%Y-%m-%d")
            # Check if the username already exists
            query = "SELECT * FROM users WHERE username = %s;"
            curs.execute(query, (uname,))
            
            if curs.fetchone():
                print("Username already taken. Try again!")
            else:
                # Insert new user into the database
                signup_query = """
                    INSERT INTO users (uid, first_name, last_name, dob, creation_date, password, username) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                """
                curs.execute(signup_query, (fname, lname,dob,creation_date, passwd, uname))
                print("Signed Up! You can go back and sign in.")
                user_state = 0
                return user_state

        elif x == 3:
            os.system('cls')
            print("Exiting...")
            user_state = -1
            return user_state
        
        else:
            os.system('cls')
            print("Invalid choice. Please try again.")

def main():
    global user_state
    # Establish connection
    conn, curs = connection(username, passwd)

    while user_state < 2:
        if user_state == -1:
            print("Quitting program ...................")
            break
        elif user_state == 0:
            user_state = login(curs)


    close(conn)

if __name__ == "__main__":
    main()
