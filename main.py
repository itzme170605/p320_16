import datetime
import psycopg2
from sshtunnel import SSHTunnelForwarder
import os
import random
from datetime import datetime, timedelta
import random


username = "jj7485"
passwd = "itzme@170605Kr"
dbname = "p320_16"
user_state = 0
user_username = ''


def search_video_games(search_params, sort_by='name', order='ASC'):
    """
    Search video games by different criteria and sort the result.

    :param search_params: Dictionary containing filters (name, platform, release_date, developer, genre, price)
    :param sort_by: Field to sort by (name, price, genre, release_date)
    :param order: Sorting order ('ASC' or 'DESC')
    """
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

            # Base query 
            sql_query = """
                SELECT DISTINCT 
                    vg.name AS game_name,
                    STRING_AGG(DISTINCT p.name, ', ') AS platforms,
                    STRING_AGG(DISTINCT c.name, ', ') AS developers,
                    STRING_AGG(DISTINCT pub_con.name, ', ') AS publishers,
                    COALESCE(ROUND(AVG(
                        EXTRACT(EPOCH FROM (upvg.end_time - upvg.start_time)) / 3600
                    )::numeric, 2), 0) AS playtime_hours,
                    vg.esrb AS age_rating,
                    COALESCE(ROUND(AVG(uov.rating)::numeric, 2), 0) AS user_rating,
                    STRING_AGG(DISTINCT g.name, ', ') AS genres,
                    vg.releasedate,
                    MIN(p.price) AS min_price
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

            # Search filters
            params = []
            if 'name' in search_params and search_params['name']:
                sql_query += " AND vg.name ILIKE %s"
                params.append(f"%{search_params['name']}%")
            
            if 'platform' in search_params and search_params['platform']:
                sql_query += " AND p.name ILIKE %s"
                params.append(f"%{search_params['platform']}%")
            
            if 'release_date' in search_params and search_params['release_date']:
                sql_query += " AND vg.releaseDate = %s"
                params.append(search_params['release_date'])
            
            if 'developer' in search_params and search_params['developer']:
                sql_query += " AND c.name ILIKE %s"
                params.append(f"%{search_params['developer']}%")
            
            if 'genre' in search_params and search_params['genre']:
                sql_query += " AND g.name ILIKE %s"
                params.append(f"%{search_params['genre']}%")
            
            if 'price' in search_params and search_params['price']:
                sql_query += " AND p.price <= %s"
                params.append(search_params['price'])

            sql_query += """ 
                GROUP BY vg.gameID, vg.name, vg.esrb, vg.releasedate
            """

            sort_columns = {
                'name': 'vg.name',
                'price': 'min_price',
                'genre': 'genres',
                'release_date': 'vg.releasedate'
            }
            
            # Apply the requested sort first, then name and release date
            if sort_by in sort_columns:
                sort_column = sort_columns[sort_by]
                if sort_by == sort_by:
                    # If sorting by name, just append release date
                    sql_query += f" ORDER BY {sort_column} {order}, vg.releasedate ASC"
                else:
                    # For other sorts, maintain alphabetical ordering as secondary sort
                    sql_query += f" ORDER BY {sort_column} {order}, vg.name ASC, vg.releasedate ASC"
            else:
                # Default sorting if no valid sort_by parameter is provided
                sql_query += " ORDER BY vg.name ASC, vg.releasedate ASC"

            curs.execute(sql_query, params)
            results = curs.fetchall()

            print("\nSearch Results:")
            print("-" * 100)
            for row in results:
                print(f"Game: {row[0]}")
                print(f"Platforms: {row[1]}")
                print(f"Developers: {row[2]}")
                print(f"Publishers: {row[3]}")
                print(f"Average Playtime: {row[4]} hours")
                print(f"Age Rating: {row[5]}")
                print(f"User Rating: {row[6]}/10")
                print(f"Genres: {row[7]}")
                print(f"Release Date: {row[8]}")
                print(f"Starting Price: ${row[9]:.2f}")
                print("-" * 100)

            conn.close()
            return results

    except Exception as e:
        print(f"Error: {e}")
        return None

'''
Miko's code 
'''
def mark_as_played(user_id, game_id=None, collection_id=None):
    """
    Mark a video game as played by a user, recording the start and end times.
    If game_id is not provided, a random game from the specified collection will be chosen.
    :param user_id: The ID of the user.
    :param game_id: Optional ID of the game.
    :param collection_id: Optional ID of the collection to choose a random game from.
    :param start_time: Optional start time for the play session. Defaults to current time.
    :param end_time: Optional end time for the play session.
    """
    
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

            # If game_id is not provided but collection_id is, choose a random game from the collection
            
            start_date = datetime(2018, 1, 1, 0, 0, 0)  # Earliest play session start
            end_date = datetime.now()  # Latest possible end time
            start_time = random_datetime(start_date, end_date)
            end_time = random_datetime(start_time, end_date)
                
            if game_id is None and collection_id is not None:
                random_game_query = """
                    SELECT gameid
                    FROM games_in_collection
                    WHERE collectionid = %s;
                """
                curs.execute(random_game_query, (collection_id))
                games = curs.fetchall()

                if not games:
                    print(f"No games found in collection {collection_id}.")
                    return
                
                game_id = random.choice(games)[0]
                print(f"Random game selected from collection {collection_id}: Game ID {game_id}")
            
            # Check if game_id is still None (no game or collection provided)
            if game_id is None:
                print("No game_id or valid collection_id provided.")
                return

            # Check if the user has played the game previously
            query = f"""
                select * from user_plays_video_games upvg where upvg.userid = {user_id} and upvg.gameid = {game_id}
            """
            curs.execute(query)
            results = curs.fetchall()

            if len(results) > 0:
                # Update existing play session
                print("Updating existing play session")
                update_query = """
                    UPDATE user_plays_video_games 
                    SET start_time = %s, end_time = %s 
                    WHERE userid = %s AND gameid = %s;
                """
                curs.execute(update_query, (start_time, end_time, user_id, game_id))
                print(f"Play session updated for user {user_id} with game {game_id}.")
            else:
                # insert
                print("reached insert")
                insert_query = """
                INSERT INTO user_plays_video_games (userid, gameid, start_time, end_time)
                VALUES (%s, %s, %s, %s);
            """
                curs.execute(insert_query, (user_id, game_id, start_time, end_time))

                print(f"Play session recorded for user {user_id} with game {game_id}.")
            
            conn.commit()            

    except psycopg2.OperationalError as oe:
        print(f"Database connection error: {oe}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("Database connection closed.")

'''Alvin'''

def rate_game_for_user(user_id, game_id, star_rating):
    """
    Update the rating for a specific user's game in 'user_owns_video_games' using game_id.
    :param user_id: The ID of the user.
    :param game_id: The ID of the game to rate.
    :param star_rating: The star rating given by the user (0.5 to 10.0, 1 decimal).
    """
    try:
        # Ensure the rating is between 0.5 and 10.0 with one decimal
        if not (0.5 <= star_rating <= 10.0) or round(star_rating * 10) % 1 != 0:
            print("Rating must be between 0.5 and 10.0 with one decimal place.")
            return

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

            # Update the rating for the specific user and game
            update_rating_query = """
                UPDATE user_owns_video_games
                SET rating = %s
                WHERE userid = %s AND gameid = %s;
            """
            curs.execute(update_rating_query, (star_rating, user_id, game_id))
            conn.commit()

            if curs.rowcount == 0:
                print(f"No record found for user {user_id} with game ID {game_id}.")
            else:
                print(f"Rating updated to {star_rating} for user {user_id} on game ID {game_id}.")

    except psycopg2.OperationalError as oe:
        print(f"Database connection error: {oe}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("Database connection closed.")


def random_datetime(start, end):
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)

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
