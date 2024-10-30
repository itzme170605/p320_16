import psycopg2
from sshtunnel import SSHTunnelForwarder
import config

username = config.username
password = config.password
dbName = config.dbName

def add_collection(collection_id, uid, name):
    try:
        with SSHTunnelForwarder(('starbug.cs.rit.edu', 22),
                                ssh_username=username,
                                ssh_password=password,
                                remote_bind_address=('127.0.0.1', 5432)) as server:
            server.start()
            params = {
                'database': dbName,
                'user': username,
                'password': password,
                'host': 'localhost',
                'port': server.local_bind_port
            }
            print("SSH tunnel established")
            conn = psycopg2.connect(**params)
            curs = conn.cursor()
            print("Database Connection Established")
            curs.execute("insert into collection(collectionid, userid, name) values(%s, %s, %s)",
                         (collection_id, uid, name))
            conn.commit()
            print("collection added")
            conn.close()
    except Exception as e:
        print("Failed to add to collection:", e)


def delete_collection(collection_id):
    try:
        with SSHTunnelForwarder(('starbug.cs.rit.edu', 22),
                                ssh_username=username,
                                ssh_password=password,
                                remote_bind_address=('127.0.0.1', 5432)) as server:
            server.start()
            params = {
                'database': dbName,
                'user': username,
                'password': password,
                'host': 'localhost',
                'port': server.local_bind_port
            }
            print("SSH tunnel established")
            conn = psycopg2.connect(**params)
            curs = conn.cursor()
            print("Database Connection Established")
            curs.execute("DELETE from collection WHERE collectionid = %s", (collection_id,))
            conn.commit()
            print("collection deleted")
            conn.close()
    except Exception as e:
        print("Failed to delete collection:", e)


def add_to_collection(gameid, collectionid):
    try:
        with SSHTunnelForwarder(('starbug.cs.rit.edu', 22),
                                ssh_username=username,
                                ssh_password=password,
                                remote_bind_address=('127.0.0.1', 5432)) as server:
            server.start()
            params = {
                'database': dbName,
                'user': username,
                'password': password,
                'host': 'localhost',
                'port': server.local_bind_port
            }
            print("SSH tunnel established")
            conn = psycopg2.connect(**params)
            curs = conn.cursor()
            print("Database Connection Established")
            curs.execute("select userid from collection where collectionid = %s", (collectionid,))
            userid = curs.fetchone()
            curs.execute("select platformid from user_owns_platforms where userid = %s", (userid,))
            userplatids = curs.fetchall()
            curs.execute("select platformid from games_on_platform where gameid = %s", (gameid,))
            gameplatid = curs.fetchone()
            if gameplatid not in userplatids:
                perm = input("Warning game is not in a platform you own, would you like to proceed y/n? ")
                if perm == "y":
                    curs.execute("insert into games_in_collection(gameid, collectionid) values (%s, %s)",
                                 (gameid, collectionid))
                    conn.commit()
                    print("game added to collection")
                else:
                    print("game was not added to your collection")
            else:
                curs.execute("insert into games_in_collection(gameid, collectionid) values (%s, %s)",
                             (gameid, collectionid))
                conn.commit()
                print("game added to collection")
                conn.close()
    except Exception as e:
        print("Failed to add to collection:", e)


def delete_from_collection(gameid):
    try:
        with SSHTunnelForwarder(('starbug.cs.rit.edu', 22),
                                ssh_username=username,
                                ssh_password=password,
                                remote_bind_address=('127.0.0.1', 5432)) as server:
            server.start()
            params = {
                'database': dbName,
                'user': username,
                'password': password,
                'host': 'localhost',
                'port': server.local_bind_port
            }
            print("SSH tunnel established")
            conn = psycopg2.connect(**params)
            curs = conn.cursor()
            print("Database Connection Established")
            curs.execute("DELETE from games_in_collection WHERE gameid = %s", (gameid,))
            conn.commit()
            print("game deleted from collection")
            conn.close()
    except Exception as e:
        print("Failed to delete from collection:", e)


if __name__ == "__main__":
    add_to_collection(13, 10)
