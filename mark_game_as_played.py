import psycopg2
from sshtunnel import SSHTunnelForwarder
from datetime import datetime
import random

# Retrieve credentials from environment variables
username = ""
password = ""
dbName = "p320_16"

def mark_as_played(user_id, game_id=None, collection_id=None, start_time=None, end_time=None):
    """
    Mark a video game as played by a user, recording the start and end times.
    If game_id is not provided, a random game from the specified collection will be chosen.
    :param user_id: The ID of the user.
    :param game_id: Optional ID of the game.
    :param collection_id: Optional ID of the collection to choose a random game from.
    :param start_time: Optional start time for the play session. Defaults to current time.
    :param end_time: Optional end time for the play session.
    """
    start_time = start_time or datetime.now()
    
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

            # If game_id is not provided but collection_id is, choose a random game from the collection
            if game_id is None and collection_id is not None:
                random_game_query = """
                    SELECT gameid
                    FROM games_in_collection
                    WHERE collectionid = %s;
                """
                curs.execute(random_game_query, (collection_id,))
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

            # Insert the play session record
            insert_query = """
                INSERT INTO user_plays_video_games (userid, gameid, start_time, end_time)
                VALUES (%s, %s, %s, %s);
            """
            curs.execute(insert_query, (user_id, game_id, start_time, end_time))
            conn.commit()
            print(f"Play session recorded for user {user_id} with game {game_id}.")

    except psycopg2.OperationalError as oe:
        print(f"Database connection error: {oe}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("Database connection closed.")

# Example usage for an individual game
mark_as_played(user_id=123, game_id=456)

# Example usage for a random game from a collection
mark_as_played(user_id=123, collection_id=789)
