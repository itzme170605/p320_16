import psycopg2
from sshtunnel import SSHTunnelForwarder


username = ""
password = ""
dbName = "p320_16"

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

# Example usage
if __name__ == "__main__":
    search_params = {
        'name': 'Mario',          # Search by name (optional)
        # 'platform': 'Switch',     # Search by platform (optional)
        # 'developer': 'Nintendo',  # Search by developer (optional)
        # 'price': 60.00,          # Maximum price (optional)
        # 'genre': 'Platform'      # Search by genre (optional)
    }
    
    # Perform search with sorting by name in ascending order
    search_video_games(search_params, sort_by='name', order='ASC')