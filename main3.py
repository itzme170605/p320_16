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
    if conn:
        conn.close()
    if server:
        server.stop()
    print("Database and SSH tunnel closed.")

def view_profile(curs, conn):
    global USER_DETAILS
    try:
        curs.execute("SELECT username, email, join_date FROM users WHERE userid = %s", (USER_DETAILS[0],))
        profile_data = curs.fetchone()
        if profile_data:
            print(f"Username: {profile_data[0]}, Email: {profile_data[1]}, Joined: {profile_data[2]}")
        else:
            print("Profile data not found.")
    except Exception as e:
        print(f"Error fetching profile: {e}")

def view_collections():
    global USER_DETAILS
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
            for col in collections:
                print(f"Collection ID: {col[0]}, Name: {col[1]}, Games: {col[2]}, Playtime: {format_playtime(col[3])}")
    except Exception as e:
        print(f"Error fetching collections: {e}")
    finally:
        close_connection(server, conn)

def make_collection():
    global USER_DETAILS
    conn, server = get_db_connection()
    try:
        with conn.cursor() as curs:
            collection_name = input("Enter the collection name: ")
            curs.execute("INSERT INTO collection (userid, name) VALUES (%s, %s) RETURNING collectionid", (USER_DETAILS[0], collection_name))
            conn.commit()
            print(f"Collection '{collection_name}' created with ID {curs.fetchone()[0]}")
    except Exception as e:
        print(f"Error creating collection: {e}")
    finally:
        close_connection(server, conn)

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
            for user in users:
                print(f"User ID: {user[0]}, Username: {user[1]}, Email: {user[2]}")
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

# Helper function to generate random datetime
def random_datetime(start, end):
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)

# Helper function to format playtime
def format_playtime(total_play_time):
    days, seconds = total_play_time.days, total_play_time.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    years, days = divmod(days, 365)
    months, days = divmod(days, 30)
    return f"{years} years {months} months {days} days {hours} hours {minutes} minutes {seconds} seconds"

