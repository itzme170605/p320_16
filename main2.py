import psycopg2
from sshtunnel import SSHTunnelForwarder
import random
from datetime import datetime, timedelta
import os

USER_STATE = 0

username = "jj7485"
passwd = "itzme@170605Kr"
dbname = "p320_16"

def get_db_connection():
    try:
        server = SSHTunnelForwarder(
            ('starbug.cs.rit.edu', 22),
            ssh_username=username,
            ssh_password=passwd,
            remote_bind_address=('127.0.0.1', 5432)
        )
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
        print("Database connection established")
        return conn, server
    except Exception as e:
        print(f"Error establishing connection: {e}")
        return None, None

def close_connection(server, conn):
    """
    Closes the database and SSH connections.
    """
    if conn:
        conn.close()
    if server:
        server.stop()
    print("Database and SSH tunnel closed.")


def search_video_games(search_params, sort_by='name', order='ASC'):
    sort_columns = {
        'name': 'vg.name', 'price': 'min_price',
        'genre': 'genres', 'release_date': 'vg.releasedate'
    }
    sort_column = sort_columns.get(sort_by, 'vg.name')
    query_base = """
        SELECT DISTINCT 
            vg.name AS game_name,
            STRING_AGG(DISTINCT p.name, ', ') AS platforms,
            STRING_AGG(DISTINCT c.name, ', ') AS developers,
            STRING_AGG(DISTINCT pub_con.name, ', ') AS publishers,
            COALESCE(ROUND(AVG(EXTRACT(EPOCH FROM (upvg.end_time - upvg.start_time)) / 3600)::numeric, 2), 0) AS playtime_hours,
            vg.esrb AS age_rating,
            COALESCE(ROUND(AVG(uov.rating)::numeric, 2), 0) AS user_rating,
            STRING_AGG(DISTINCT g.name, ', ') AS genres,
            vg.releasedate, MIN(p.price) AS min_price
        FROM video_games vg
        LEFT JOIN Games_on_platform gop ON gop.gameID = vg.gameID
        LEFT JOIN Platform p ON p.platformID = gop.platformID
        LEFT JOIN Developers d ON d.gameID = vg.gameID
        LEFT JOIN Contributors c ON c.conID = d.conID
        LEFT JOIN Publishers pub ON pub.gameID = vg.gameID
        LEFT JOIN Contributors pub_con ON pub_con.conID = pub.conID
        LEFT JOIN User_plays_video_games upvg ON upvg.gameID = vg.gameID
        LEFT JOIN User_owns_video_games uov ON uov.gameID = vg.gameID
        LEFT JOIN Genre_of_games gog ON gog.gameID = vg.gameID
        LEFT JOIN Genre g ON g.genreID = gog.genreID
        WHERE 1=1
    """
    filters = []
    params = []

    for field, value in search_params.items():
        if value:
            if field == 'name':
                filters.append("AND vg.name ILIKE %s")
            elif field == 'platform':
                filters.append("AND p.name ILIKE %s")
            elif field == 'release_date':
                filters.append("AND vg.releaseDate = %s")
            elif field == 'developer':
                filters.append("AND c.name ILIKE %s")
            elif field == 'genre':
                filters.append("AND g.name ILIKE %s")
            elif field == 'price':
                filters.append("AND p.price <= %s")
            params.append(f"%{value}%" if field != 'release_date' else value)

    query_final = f"{query_base} {' '.join(filters)} GROUP BY vg.gameID ORDER BY {sort_column} {order}, vg.name ASC, vg.releasedate ASC"

    conn, server = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as curs:
            curs.execute(query_final, params)
            results = curs.fetchall()
            conn.close()
            server.stop()
            return results
    except Exception as e:
        print(f"Error executing search query: {e}")
        return None

def mark_as_played(user_id, game_id=None, collection_id=None):
    conn, server = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as curs:
            if not game_id and collection_id:
                curs.execute("SELECT gameid FROM games_in_collection WHERE collectionid = %s", (collection_id,))
                games = curs.fetchall()
                game_id = random.choice(games)[0] if games else None

            if not game_id:
                print("No valid game_id or collection found.")
                return

            start_time = random_datetime(datetime(2018, 1, 1), datetime.now())
            end_time = random_datetime(start_time, datetime.now())

            curs.execute(
                "SELECT 1 FROM user_plays_video_games WHERE userid = %s AND gameid = %s", (user_id, game_id)
            )
            if curs.fetchone():
                curs.execute(
                    "UPDATE user_plays_video_games SET start_time = %s, end_time = %s WHERE userid = %s AND gameid = %s",
                    (start_time, end_time, user_id, game_id)
                )
            else:
                curs.execute(
                    "INSERT INTO user_plays_video_games (userid, gameid, start_time, end_time) VALUES (%s, %s, %s, %s)",
                    (user_id, game_id, start_time, end_time)
                )
            conn.commit()
    except Exception as e:
        print(f"Error marking game as played: {e}")
    finally:
        conn.close()
        server.stop()



def rate_game_for_user(user_id, game_id, star_rating):
    if not (0.5 <= star_rating <= 10.0) or (star_rating * 10) % 1 != 0:
        print("Invalid rating")
        return
    conn, server = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as curs:
            curs.execute(
                "UPDATE user_owns_video_games SET rating = %s WHERE userid = %s AND gameid = %s",
                (star_rating, user_id, game_id)
            )
            conn.commit()
            if curs.rowcount == 0:
                print(f"No record found for user {user_id} with game ID {game_id}.")
    except Exception as e:
        print(f"Error updating rating: {e}")
    finally:
        conn.close()
        server.stop()



def random_datetime(start, end):
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)

def search_users_by_email(search_email, user_id):
    """
    Search for new users to follow by email.

    @param search_email: Search for a user by this email
    @param user_id: User ID of the user
    """
    conn, server = get_db_connection()
    if(not conn):
        return conn
    try:
        with conn.cursor() as curs:
            
            sql_query = """
                SELECT u.userid, u.username, e.email
                FROM users u
                JOIN email e ON u.userid = e.uid  -- Adjusted to use 'uid' as foreign key
                WHERE e.email ILIKE %s
                    AND u.userid != %s
                    AND u.userid NOT IN (
                        SELECT followee_uid FROM followers WHERE follower_uid = %s
                    )
                ORDER BY u.username ASC;
            """

            curs.execute(sql_query, (f"%{search_email}%", user_id, user_id))
            results = curs.fetchall()

            print("\nSearch Results:")
            print("-" * 40)
            for row in results:
                print(f"User ID: {row[0]}, Username: {row[1]}, Email: {row[2]}")
            print("-" * 40)
            return results
        
    except Exception as e:
        print(f"Error updating rating: {e}")
    finally:
        conn.close()
        server.stop()

def follow_user(follower_uid, followee_uid):
    """
    Follow a new user by inserting a record in the followers table.

    @param follower_uid: Follower UID
    @param followee_uid: Followee UID
    """
    conn, server = get_db_connection()
    try:
        with conn.cursor() as curs:

            sql_query = """
                INSERT INTO followers (follower_uid, followee_uid)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;  -- Avoid duplicate follows
            """

            curs.execute(sql_query, (follower_uid, followee_uid))
            conn.commit()
            print(f"User {follower_uid} now follows User {followee_uid}")

            

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
        server.stop()

def unfollow_user(follower_uid, followee_uid):
    """
    Unfollow a user by deleting a record from the followers table.

    @param follower_uid: Follower UID
    @param followee_uid: Followee UID
    """
    conn,server = get_db_connection()
    try:
        with conn.cursor() as curs:
            sql_query = """
                DELETE FROM followers
                WHERE follower_uid = %s AND followee_uid = %s
            """

            curs.execute(sql_query, (follower_uid, followee_uid))
            conn.commit()
            print(f"User {follower_uid} unfollowed User {followee_uid}")

            conn.close()

    except Exception as e:
        print(f"Error: {e}")

def homepage(curs):
    global USER_STATE
    while True:
        print('''
        Signed in!
        Choose an option:
            1 - View Profile
            2 - View Collections
            3 - Make a New Collection
            4 - Log Game Play
            5 - Exit
        ''')
        
        choice = input("->|| ")
        if choice == '1':
            view_profile(curs)
        elif choice == '2':
            view_collections(curs)
        elif choice == '3':
            make_collection(curs)
        elif choice == '4':
            log_game_play(curs)
        elif choice == '5':
            print("Exiting...")
            USER_STATE = -1
            break
        else:
            print("Invalid choice. Please try again.")


def view_profile(curs):
    # Implement functionality to view user profile information
    print("Viewing profile... (implementation here)")

def view_collections(curs):
    # Implement functionality to view collections
    print("Viewing collections... (implementation here)")

def make_collection(curs):
    # Implement functionality to create a new collection
    print("Creating a new collection... (implementation here)")

def log_game_play(curs):
    # Implement functionality to log game play
    print("Logging game play... (implementation here)")

def login(curs):
    global USER_STATE
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
            
            if curs.fetchone():
                print("Login successful!")
                USER_STATE = 2
                return USER_STATE
            else:
                print("Invalid username or password. Try again!")
                
        elif x == 2:
            os.system('cls')
            print("Sign up:")
            fname = input("First name: ")
            lname = input("Last name: ")
            uname = input("Username: ")
            passwd = input("Password: ")
            dob = input("DOB (YYYY-MM-DD): ")
            creation_date =  datetime.now().strftime("%Y-%m-%d")
            query = "SELECT * FROM users WHERE username = %s;"
            curs.execute(query, (uname,))
            
            if curs.fetchone():
                print("Username already taken. Try again!")
            else:
                signup_query = """
                    INSERT INTO users (uid, first_name, last_name, dob, creation_date, password, username) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                """
                curs.execute(signup_query, (fname, lname, dob, creation_date, passwd, uname))
                print("Signed Up! You can go back and sign in.")
                USER_STATE = 0
                return USER_STATE

        elif x == 3:
            os.system('cls')
            print("Exiting...")
            USER_STATE = -1
            return USER_STATE
        
        else:
            os.system('cls')
            print("Invalid choice. Please try again.")

def main():
    global USER_STATE
    conn, server = get_db_connection()
    curs = conn.cursor()

    while USER_STATE < 2:
        if USER_STATE == -1:
            print("Quitting program...")
            close_connection(server, conn)
            break
        elif USER_STATE == 0:
            USER_STATE = login(curs)

    if USER_STATE == 2:
        homepage(curs)
        close_connection(server, conn)

if __name__ == "__main__":
    main()