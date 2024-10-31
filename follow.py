import psycopg2
from sshtunnel import SSHTunnelForwarder

username = ""
password = ""
dbName = "p320_16"

def search_users_by_email(search_email, user_id):
    """
    Search for new users to follow by email.
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

            # Use 'uid' in the join to match the foreign key column in the email table
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

            conn.close()
            return results

    except Exception as e:
        print(f"Error: {e}")
        return None

def follow_user(follower_uid, followee_uid):
    """
    Follow a new user by inserting a record in the followers table.
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

            sql_query = """
                INSERT INTO followers (follower_uid, followee_uid)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;  -- Avoid duplicate follows
            """

            curs.execute(sql_query, (follower_uid, followee_uid))
            conn.commit()
            print(f"User {follower_uid} now follows User {followee_uid}")

            conn.close()

    except Exception as e:
        print(f"Error: {e}")

def unfollow_user(follower_uid, followee_uid):
    """
    Unfollow a user by deleting a record from the followers table.
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

# Example usage
if __name__ == "__main__":
    # Search for users by email
    user_id = 1  # Current user ID
    search_email = 'example'
    search_users_by_email(search_email, user_id)

    # Follow a user
    follower_uid = 1
    followee_uid = 2
    follow_user(follower_uid, followee_uid)

    # Unfollow a user
    unfollow_user(follower_uid, followee_uid)
