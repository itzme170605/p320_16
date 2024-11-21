import psycopg2
from sshtunnel import SSHTunnelForwarder
import random
from datetime import datetime, timedelta
import os
from decimal import Decimal


USER_STATE = 0
USER_DETAILS = ()

username = ""
passwd = ""
dbname = "p320_16"

def recommendation_system(user_id):
    # Establish the database connection
    conn, server = get_db_connection()
    
    try:
        cursor = conn.cursor()

        # Top 20 most popular video games in the last 90 days
        def top_20_last_90_days():
            query = """
                SELECT vg.name, COUNT(*) as play_count 
                FROM user_plays_video_games upvg
                JOIN video_games vg ON vg.gameid = upvg.gameid
                WHERE start_time >= %s
                GROUP BY vg.name
                ORDER BY play_count DESC
                LIMIT 20;
            """
            ninety_days_ago = datetime.now() - timedelta(days=90)
            cursor.execute(query, (ninety_days_ago,))
            return [row[0] for row in cursor.fetchall()]  # Return only the names

        # Top 20 most popular video games among user's followers
        def top_20_among_followers():
            query = """
                SELECT vg.name, COUNT(*) as play_count
                FROM user_plays_video_games upvg
                JOIN followers f ON f.followee_uid = upvg.userid
                JOIN video_games vg ON vg.gameid = upvg.gameid
                WHERE f.follower_uid = %s
                GROUP BY vg.name
                ORDER BY play_count DESC
                LIMIT 20;
            """
            cursor.execute(query, (user_id,))
            return [row[0] for row in cursor.fetchall()]  # Return only the names

        # Top 5 new releases of the current month
        def top_5_new_releases():
            first_day_of_month = datetime.now().replace(day=1)
            last_day_of_month = datetime.now().replace(day=1) + timedelta(days=32)
            last_day_of_month = last_day_of_month.replace(day=1) - timedelta(days=1)

            query = """
                SELECT name 
                FROM video_games
                WHERE releasedate BETWEEN %s AND %s
                ORDER BY releasedate DESC
                LIMIT 5;
            """
            cursor.execute(query, (first_day_of_month, last_day_of_month))
            return [row[0] for row in cursor.fetchall()]  # Return only the names

        # "For you" - Recommendations based on user's play history
        def personalized_recommendations():
            query = """
                SELECT DISTINCT vg.name, vg.releasedate
                FROM user_plays_video_games upvg_other
                JOIN genre_of_games gog ON upvg_other.gameid = gog.gameid
                JOIN video_games vg ON vg.gameid = upvg_other.gameid
                LEFT JOIN user_plays_video_games upvg_user
                ON upvg_user.gameid = vg.gameid AND upvg_user.userid = %s
                WHERE upvg_other.userid != %s
                AND gog.genreid IN (
                    SELECT DISTINCT gog.genreid
                    FROM user_plays_video_games upvg
                    JOIN genre_of_games gog ON upvg.gameid = gog.gameid
                    WHERE upvg.userid = %s
                )
                AND upvg_user.gameid IS NULL
                ORDER BY vg.releaseDate DESC
                LIMIT 10;
            """
            cursor.execute(query, (user_id, user_id, user_id))
            return [row[0] for row in cursor.fetchall()]  # Return only the names

        # Fetch recommendations and print each separately
        print("Top 20 most popular video games in the last 90 days:")
        for game in top_20_last_90_days():
            print(f" - {game}")

        print("\nTop 20 most popular video games among your followers:")
        for game in top_20_among_followers():
            print(f" - {game}")

        print("\nTop 5 new releases of the current month:")
        for game in top_5_new_releases():
            print(f" - {game}")

        print("\nFor you - Personalized recommendations based on your play history:")
        for game in personalized_recommendations():
            print(f" - {game}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        close_connection(server, conn)
        
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

def random_datetime(start, end):
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)

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
    conn, server = get_db_connection()
    try:
        with conn.cursor() as curs:
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

def user_log_game_play():
    global USER_DETAILS
    conn, server = get_db_connection()
    try:
        with conn.cursor() as curs:
            print_games_owned()
            gameid = int(input("Game id:"))
            start_time = input("Enter a date and time (YYYY-MM-DD HH:MM:SS): ")
            end_time = input("Enter a date and time (YYYY-MM-DD HH:MM:SS): ")
            try:
                # Parse the input string into a datetime object

                print(f"You entered: {start_time} - {end_time}")
                if(start_time != '' and end_time != ''):
                    start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                    end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
                    query = '''
                    INSERT INTO user_plays_video_games (userid, gameid, start_time, end_time) VALUES (%s, %s, %s, %s);
                    '''
                    curs.execute(query, (USER_DETAILS[0],gameid, start_time,end_time))
                    conn.commit()
                    print("Sucess!!")
                else:
                    log_game_play()
            except ValueError:
                print("Invalid format. Please enter the date and time in 'YYYY-MM-DD HH:MM:SS' format.")
    except Exception as e:
        print(f"Error : {e}")
    finally:
        conn.close()
        server.close()

def print_games_owned():
    print("Games owned by user:")
    query = '''
SELECT 
    vg.gameid,
    vg.name,
    uvg.rating,
    uvg.purchasedate
FROM 
    user_owns_video_games uvg
JOIN 
    video_games vg ON uvg.gameid = vg.gameid
WHERE 
    uvg.userid = %s;

            '''
    conn,server = get_db_connection()
    try:
        with conn.cursor() as curs:
            curs.execute(query, (USER_DETAILS[0],))
            data = curs.fetchall()
            if(data == None):
                print("No games owened!")
            else:
                print(data)
            conn.close()
            server.stop()
    except Exception as e:
        print(f"Error: {e}")

def print_games_in_colection(collectionid):
    print("Games in Collection:")
    query = '''
SELECT v.gameid, v.name
FROM games_in_collection c
JOIN video_games v ON c.gameid = v.gameid
WHERE c.collectionid = %s;
'''
    conn,server = get_db_connection()
    try:
        with conn.cursor() as curs:
            curs.execute(query, (collectionid,))
            data = curs.fetchall()
            if(data == None):
                print("No games in Collection!")
            else:
                print(data)
            conn.close()
            server.stop()
    except Exception as e:
        print(f"Error: {e}")

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
            8 - Play game
            9 - Get game recommendations
            10 - Exit
        ''')
        
        choice = input("->||")
        if choice == '1':
            view_profile(curs,conn)
        elif choice == '2':
            view_collections()
        elif choice == '3':
            make_collection()
        elif choice == '4':
            user_log_game_play()
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
            
            print_games_owned()
            print("Rate video Games:")
            game_name = input("Enter game name:")
            result = search_video_games({'name': game_name})
            print_search_results(result)
            game_id = int(input("input the gameid to confirm:"))
            conn,server = get_db_connection()
            try:
                with conn.cursor() as curs:
                    query = '''
SELECT * from user_owns_video_games 
WHERE userid = %s AND gameid = %s;
'''
                    curs.execute(query,(USER_DETAILS[0],game_id))
                    if(curs.fetchone()):
                        rating = float(input("Rate the game:(0.5-10)"))
                        rate_game_for_user(USER_DETAILS[0],game_id,rating)
                    else:
                        print("you donot own this game!")
                    conn.close()
                    server.stop()
            except Exception as e:
                print(f"Errror: {e}")
            
        elif choice == '8':
            mark_as_played(USER_DETAILS[0])
        elif choice == '9':
            recommended_games = recommendation_system(USER_DETAILS[0])
            print(recommended_games)
        elif choice == '10':
            print("Exiting...")
            USER_STATE = -1
            break
        else:
            print("Invalid choice. Please try again.")



def view_profile(curs, conn):
    global USER_DETAILS
    try:
        curs.execute("SELECT userid, fname, lname, dob, creationdate, password, username FROM users WHERE userid = %s", (USER_DETAILS[0],))
        user_details = curs.fetchone()
        
        if user_details:
            # Print formatted output
            print(f"User ID: {user_details[0]}")
            print(f"First Name: {user_details[1]}")
            print(f"Last Name: {user_details[2]}")
            print(f"Date of Birth: {user_details[3]}")
            print(f"Creation Date: {user_details[4]}")
            print(f"Username: {user_details[6]}")
            # Note: Password should not be printed for security reasons
        else:
            print("No user found with the specified ID.")
    except Exception as e:
        print(f"Error fetching profile: {e}")



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
                    selected_collection = collections[choice - 1][0]
                    print_games_in_colection(selected_collection)
                    x = int(input("""Choice:
                    1 - Modify name
                    2 - Remove game
                    3 - add Game
                    4 - exit
                    """))
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

                query = '''
                    SELECT platformid from games_on_platform where gameid = %s;
'''
                curs.execute(query,(game_id,))
                platformid = curs.fetchone()[0]
                query = '''
                    SELECT * from user_owns_platforms where platformid = %s and userid = %s
'''
                curs.execute(query,(platformid,USER_DETAILS[0]))
                data = curs.fetchone()
                if(data == None):
                    x = input("WARNING! YOu donot own the platform for this game Do you want to continue?(y/n):" )
                    if(x in 'Nn'):
                        print("Aborting action")
                    else:
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
            uid = genereate_unique_user_id()
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
