import psycopg2
from sshtunnel import SSHTunnelForwarder
import random

username = ""
password = ""
dbName = "p320_16"

def get_random_game_from_collection(collection_name):
    """
    Fetch a random game from a collection based on the collection name.
    :param collection_name: The name of the collection to search within.
    :return: A random game from the specified collection.
    """
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

            # Query to get all games from the specified collection
            query = """
                SELECT vg.name
                FROM collection c
                JOIN games_in_collection gc ON c.collectionid = gc.collectionid
                JOIN video_games vg ON gc.gameid = vg.gameid
                WHERE c.name = %s;
            """
            curs.execute(query, (collection_name,))
            games = curs.fetchall()

            if not games:
                print(f"No games found for collection: {collection_name}")
                return

            random_game = random.choice(games)[0]
            print(f"Random Game from '{collection_name}': {random_game}")

            conn.close()
    except Exception as e:
        print(f"Error: {e}")

# Example usage
get_random_game_from_collection('Alices RPG Collection')