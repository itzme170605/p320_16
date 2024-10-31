import psycopg2
from sshtunnel import SSHTunnelForwarder

username = ""
password = ""
dbName = "p320_16"

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

# Example usage
rate_game_for_user(123, 456, 9.5)
