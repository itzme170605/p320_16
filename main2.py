import psycopg2
from sshtunnel import SSHTunnelForwarder
import random
from datetime import datetime, timedelta
import os
from decimal import Decimal


USER_STATE = 0
USER_DETAILS = ()

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

def genereate_unique_user_id():
    
    conn, server = get_db_connection()
    try:
        with conn.cursor() as curs:
            while True:
                rand = random.randint(0,100000000)
                curs.execute(f"SELECT * from users where userid = {rand};")
                if(curs.fetchone()):
                    continue
                else:
                    break
        conn.close()
        server.stop()
        return rand
    except Exception as e:
        print(f"Error in id generation try again {e}")

def search_video_games(search_params, sort_by='name', order='ASC'):
    sort_columns = {
        'name': 'vg.name', 'price': 'min_price',
        'genre': 'genres', 'release_date': 'vg.releasedate'
    }
    sort_column = sort_columns.get(sort_by, 'vg.name')
    query_base = """
        SELECT DISTINCT
            vg.gameid as Game_id,
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

            sql_query =  """
                INSERT INTO followers (follower_uid, followee_uid)
                VALUES (%s, %s)
                ON CONFLICT (follower_uid, followee_uid) DO NOTHING
                RETURNING follower_uid;
            """

            curs.execute(sql_query, (follower_uid, followee_uid))
            result = curs.fetchone()
            conn.commit()
            if result:
                print(f"User {follower_uid} now follows User {followee_uid}")
            else:
                print(f"User {follower_uid} is already following User {followee_uid}")
            # print(f"User {follower_uid} now follows User {followee_uid}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
        server.stop()
        # return result

def unfollow_user(follower_uid, followee_uid):
    """
    Unfollow a user by deleting a record from the followers table.

    @param follower_uid: Follower UID
    @param followee_uid: Followee UID
    """
    conn,server = get_db_connection()
    try:
        with conn.cursor() as curs:
            sql_query ="""
                DELETE FROM followers
                WHERE follower_uid = %s AND followee_uid = %s
                RETURNING follower_uid;
            """

            curs.execute(sql_query, (follower_uid, followee_uid))
            result = curs.fetchone()
            conn.commit()
            if result:
                print(f"User {follower_uid} unfollowed User {followee_uid}")
            else:
                print(f"No follow relationship found between User {follower_uid} and User {followee_uid}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
        server.stop()

def search_for_users():
    conn, server = get_db_connection()
    try:
        with conn.cursor() as curs:
            search_email = input("Enter email to search: ")
            curs.execute("""
                SELECT u.userid, u.username, e.email
                FROM users u
                JOIN email e ON u.userid = e.uid
                WHERE e.email ILIKE %s
                    AND u.userid != %s
            """, (f"%{search_email}%", USER_DETAILS[0]))
            users = curs.fetchall()
            print("Search Results:")
            for index, user in enumerate(users, start=1):
                print(f"{index}. User ID: {user[0]}, Username: {user[1]}, Email: {user[2]}")
                
    except Exception as e:
        print(f"Error searching users: {e}")
    finally:
        close_connection(server, conn)

def log_game_play():
    global USER_DETAILS
    conn, server = get_db_connection()
    try:
        with conn.cursor() as curs:
            curs.execute("SELECT gameid, name FROM video_games")
            games = curs.fetchall()
            for game in games:
                print(f"ID: {game[0]}, Name: {game[1]}")
            game_id = input("Enter game ID to log play: ")
            start_time = random_datetime(datetime(2018, 1, 1), datetime.now())
            end_time = random_datetime(start_time, datetime.now())
            curs.execute("""
                INSERT INTO user_plays_video_games (userid, gameid, start_time, end_time)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (userid, gameid) DO UPDATE SET start_time = EXCLUDED.start_time, end_time = EXCLUDED.end_time
            """, (USER_DETAILS[0], game_id, start_time, end_time))
            conn.commit()
            print(f"Playtime logged for game ID {game_id}")
    except Exception as e:
        print(f"Error logging playtime: {e}")
    finally:
        close_connection(server, conn)

def homepage(conn, curs):
    global USER_STATE, USER_DETAILS
    while True:
        print(f'''
        Welcome, {USER_DETAILS[1]}!
        
        Choose an option:
            1 - View Profile
            2 - View Collections
            3 - Make a New Collection
            4 - Log Game Play
            5 - Search for users
            6 - Follow/Unfollow users by id
            7 - rate a video game
            8 - Exit
        ''')
        
        choice = input("->||")
        if choice == '1':
            view_profile(curs,conn)
        elif choice == '2':
            view_collections()
        elif choice == '3':
            make_collection()
        elif choice == '4':
            log_game_play()
        elif choice == '5':
            search_for_users()
        elif choice == '6':
            uid = int(input("Enter user id:"))

            print("""
Choose an action:
    1 - follow 
    2 - unfollow """)
            x = int(input("-->||"))
            if(x == 1):
                x = input("Are you sure?(y/n)")
                if(x in'Yy'):

                    follow_user(USER_DETAILS[0],uid)
            if(x == 2):
                x = input("Are you sure ?(Y/N)")
                if(x in "Yy"):
                    unfollow_user(USER_DETAILS[0], uid)
                else:
                    print("exiting")
        
        elif choice == '7':
            os.system("cls")
            print("Rate video Games:")

        elif choice == '8':
            print("Exiting...")
            USER_STATE = -1
            break
        else:
            print("Invalid choice. Please try again.")



def view_profile(curs,conn):
    global USER_STATE, USER_DETAILS
    # Implement functionality to view user profile information
    for i in USER_DETAILS:
        print(i)
    print("Viewing profile... (implementation here)")
    USER_STATE = 2
from datetime import timedelta

def format_playtime(total_play_time):
    """Convert timedelta to formatted string."""
    days, seconds = total_play_time.days, total_play_time.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    years, days = divmod(days, 365)
    months, days = divmod(days, 30)

    return f"{years} years {months} months {days} days {hours} hours {minutes} minutes {seconds} seconds"

def view_collections():
    """Display collections and allow user to select and modify a collection."""
    global USER_STATE, USER_DETAILS
    conn, server = get_db_connection()
    try:
        with conn.cursor() as curs:
            sql_query = """
                SELECT
                    c.collectionid as id,
                    c.name AS collection_name,
                    COUNT(g.gameid) AS number_of_games,
                    SUM(gl.end_time - gl.start_time) AS total_play_time
                FROM
                    collection c
                LEFT JOIN
                    games_in_collection g ON c.collectionid = g.collectionid
                LEFT JOIN
                    user_plays_video_games gl ON g.gameid = gl.gameid
                WHERE
                    c.userid = %s
                GROUP BY
                    c.collectionid, c.name
                ORDER BY
                    c.name ASC;
            """
            curs.execute(sql_query, (USER_DETAILS[0],))
            collections = curs.fetchall()

        if not collections:
            print("No collections found for the user.")
            return

        # Display each collection with formatted total playtime
        for idx, (id,name, num_games, total_play_time) in enumerate(collections, start=1):
            if(total_play_time == None):
                formatted_time = total_play_time
            else:
                formatted_time = format_playtime(total_play_time)
            print(f"{idx}. collection id: {id}\n   Collection Name: {name}\n   Number of Games: {num_games}\n   Total Play Time: {formatted_time}\n")
        # User selects a collection to modify
        while True:
            try:
                print('''
    Options:
        1 - Select a collection number to modify its name/games
        0 - exit
''')
                choice = int(input("-->||"))
                if choice == 0:
                    break
                if 1 <= choice <= len(collections):
                    os.system("cls")
                    x = int(input("""Choice:
                    1 - Modify name
                    2 - Remove game
                    3 - add Game
                    4 - exit"""))
                    selected_collection = collections[choice - 1][0]
                    if(x == 1):
                        modify_collection(selected_collection)
                        conn.commit()
                    elif(x == 2):
                        remove_games_menu(curs,conn,selected_collection)
                        conn.commit()
                    elif(x==3):
                        add_games_menu(curs,conn, selected_collection)
                        conn.commit()
                    else:
                        break
                else:
                    print("Invalid selection. Please choose a valid collection number.")
            except ValueError:
                print("Invalid input. Please enter a number.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
        server.stop()


def modify_collection(collection_name):
    conn, server = get_db_connection()
    """Allow user to modify the selected collection."""
    print(f"\nModifying collection: {collection_name}")
    # Example: prompt the user to change the collection's name
    new_name = input("Enter new collection name (leave blank to keep current): ")
    try:
        with conn.cursor() as curs:
            if new_name:
                try:
                    update_query = "UPDATE collection SET name = %s WHERE collectionid = %s;"
                    curs.execute(update_query, (new_name, collection_name))
                    conn.commit()
                    print(f"Collection name updated to '{new_name}'.")
                except Exception as e:
                    print(f"Error updating collection: {e}")
            else:
                print("No changes made to the collection name.")
    except Exception as e:
        print(f"Error {e}")
    finally:
        conn.close()
        server.stop()

def genereate_unique_collectio_id():
    
    conn, server = get_db_connection()
    try:
        
        with conn.cursor() as curs:
            
            while True:
                rand = random.randint(0,1000000000)
                curs.execute(f"SELECT * from collection where collectionid = {rand};")
                if(curs.fetchone()):
                    continue
                else:
                    break
        conn.close()
        server.stop()
        return rand
    except Exception as e:
        print(f"Error in id generation try again {e}")



def make_collection():
    conn, server = get_db_connection()
    """Create a new collection and allow user to add games to it."""
    print("Creating a new collection...")
    
    # Prompt user for collection name
    collection_name = input("Enter the name of the new collection: ")
    
    # Generate a unique collection ID
    collection_id = genereate_unique_collectio_id()
    #user id 
    user_id = USER_DETAILS[0]
    try:
        with conn.cursor() as curs:
            # Insert the new collection into the 'collection' table
            insert_collection_query = """
                INSERT INTO collection (collectionid, userid, name) 
                VALUES (%s, %s, %s);
            """
            curs.execute(insert_collection_query, (collection_id, user_id, collection_name))
            conn.commit()
            print(f"Collection '{collection_name}' created successfully with ID {collection_id}.\n")
            add_games_menu(curs, conn, collection_id)
    except Exception as e:
        print(f"Error creating collection: {e}")
        conn.rollback()
        return
    finally:
        conn.close()
        server.stop()
    
    # Prompt the user to add games to the collection

def print_search_results(results):

    print(f"{'Game Id':<10} {'Game Title':<30} {'Platform':<20} {'Developer':<20} {'Collaborators':<40} {'Sales':<10} {'Rating':<5} {'Score':<10} {'Genre':<15} {'Release Date':<15} {'Price':<10}")
    print("="*175)
    if(results == None):
        print("No Results for the given search try using better arguments. and try again")
    for result in results:
        game_id, game_title, platform, developer, collaborators, sales, rating, score, genre, release_date, price = result
        print(f"{game_id:<10} {game_title:<30} {platform:<20} {developer:<20} {collaborators or 'N/A':<40} {sales:<10.2f} {rating:<5} {score:<10.2f} {genre:<15} {release_date:<15} {price:<10.2f}")

def add_games_menu(curs, conn, collection_id):
    """Menu to add games to the created collection."""
    conn,server = get_db_connection()
    curs = conn.cursor()
    while True:
        print("\nChoose an option:")
        print("1. Add a game to the collection by id")
        print("2. Add games by name")
        print("3. exit")

        try:
            choice = int(input("Enter your choice: "))
        except ValueError:
            print("Invalid input. Please enter a number.")
            continue

        if choice == 1:
            try:
                game_id = input("Enter the game ID to add: ")
                
                # Insert game into 'games_in_collection' table
                insert_game_query = """
                    INSERT INTO games_in_collection (gameid, collectionid)
                    VALUES (%s, %s);
                """
                curs.execute(insert_game_query, (game_id, collection_id))
                conn.commit()
                conn.close()
                server.stop()
                print(f"Game with ID {game_id} added to collection {collection_id}.")
            except Exception as e:
                print(f"Error adding game: {e}")
                conn.rollback()

        elif choice == 2:
            print("Search By Search params:(leave empty if dont know)")
            keys = ['name', 'price','genre ','release_date']
            params = {}
            for i in range(4):
                x = input(keys[i]+":")
                if(x):
                    params[keys[i]] = x
                else:
                    print("invalid entry set to ''")
                    params[keys[i]] = ''
            result = search_video_games(params) #sorted by nae and Ascending order
            print_search_results(result)
            
        elif choice == 3:
            print("Finished adding games. Exiting to main menu.")
            break
        else:
            print("Invalid choice. Please select 1 or 2 or 3")

def remove_games_menu(curs, conn, collection_id):
    """Menu to add games to the created collection."""
    conn, server = get_db_connection()
    curs = conn.cursor()
    while True:
        print("\nChoose an option:")
        print("1. remove a game to the collection by id")
        print("2. remove games by name")
        print("3. exit")

        try:
            choice = int(input("Enter your choice: "))
        except ValueError:
            print("Invalid input. Please enter a number.")
            continue

        if choice == 1:
            try:
                game_id = input("Enter the game ID to remove: ")
                
                # Insert game into 'games_in_collection' table
                insert_game_query = """
                DELETE FROM games_in_collection
                WHERE gameid = %s AND collectionid = %s;
                """

                curs.execute(insert_game_query, (game_id, collection_id))
                conn.commit()
                conn.close()
                server.stop()
                print(f"Game with ID {game_id} removed to collection {collection_id}.")
            except Exception as e:
                print(f"Error adding game: {e}")
                conn.rollback()

        elif choice == 2:
            print("Search By Search params:(leave empty if dont know)")
            keys = ['name', 'price','genre ','release_date']
            params = {}
            for i in range(4):
                x = input(keys[i]+":")
                if(x):
                    params[keys[i]] = x
                else:
                    print("invalid entry set to ''")
                    params[keys[i]] = ''
            result = search_video_games(params) #sorted by nae and Ascending order
            print_search_results(result)
            
        elif choice == 3:
            print("Finished adding games. Exiting to main menu.")
            break
        else:
            print("Invalid choice. Please select 1 or 2 or 3")


# def view_collections(curs,conn):
#     # Implement functionality to view collections
#     global USER_STATE, USER_DETAILS
#     print("Viewing collections... (implementation here)")
#     conn,server = get_db_connection()
#     try:
#         with conn.cursor() as curs:
#             sql_query = """
#                 SELECT
#                     c.name AS collection_name,
#                     COUNT(g.gameid) AS number_of_games,
#                     SUM(gl.end_time - gl.start_time) AS total_play_time
#                 FROM
#                     collection c
#                 LEFT JOIN
#                     games_in_collection g ON c.collectionid = g.collectionid
#                 LEFT JOIN
#                     user_plays_video_games gl ON g.gameid = gl.gameid
#                 WHERE
#                     c.userid = 2  -- Replace %s with the actual user ID
#                 GROUP BY
#                     c.collectionid, c.name
#                 ORDER BY
#                     c.name ASC;"""
#             curs.execute(sql_query,(USER_DETAILS[0],))
#             data = curs.fetchall()
#     except Exception as e:
#         print(f"Error: {e}")
#     finally:
#         conn.close()
#         server.stop()





def search_users(curs,conn):
    print("")

def login(conn, curs):
    global USER_STATE, USER_DETAILS
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
            data = curs.fetchone()
            if data:
                print("Login successful!")
                USER_DETAILS = data
                curs.execute("INSERT INTO user_log(userid, lasttimelogged) VALUES(%s,%s);",(USER_DETAILS[0],datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")))
                USER_STATE = 2
                conn.commit()
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
            uid = 2000
            creation_date =  datetime.now().strftime("%Y-%m-%d")
            query = "SELECT * FROM users WHERE username = %s;"
            curs.execute(query, (uname,))
            
            if curs.fetchone():
                print("Username already taken. Try again!")
            else:
                signup_query = """
                    INSERT INTO users (userid, fname, lname, dob, creationdate, password, username) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                """
                curs.execute(signup_query, (uid,fname, lname, dob, creation_date, passwd, uname))
                print("Signed Up! You can go back and sign in.")
                conn.commit()
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

    while True:
        if USER_STATE == -1:
            print("Quitting program...")
            close_connection(server, conn)
            break
        elif USER_STATE == 0:
            USER_STATE = login(conn, curs)

        if USER_STATE == 2:
        # os.system('cls')
            homepage(conn, curs)
            close_connection(server, conn)
            continue
        elif USER_STATE == 3:
            view_profile()


if __name__ == "__main__":
    main()