CREATE_USER_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    user_id   INTEGER PRIMARY KEY NOT NULL,
    username  TEXT    UNIQUE NOT NULL
)
"""

CREATE_MAPS_TABLE = """
CREATE TABLE IF NOT EXISTS maps (
    map_id   INTEGER PRIMARY KEY NOT NULL,
    map_name TEXT    UNIQUE NOT NULL
)
"""

CREATE_DATA_TABLE = """
CREATE TABLE IF NOT EXISTS ow2 (
    rating_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    author_id INTEGER NOT NULL,
    map_id    INTEGER NOT NULL,
    result    STRING NOT NULL,
    -- role      CHAR(1) NOT NULL,
    -- sentiment INTEGER NOT NULL,
    datetime  INTEGER NOT NULL,

    FOREIGN KEY (author_id)
        REFERENCES users (user_id)
            ON DELETE CASCADE
            ON UPDATE NO ACTION,
    FOREIGN KEY (map_id)
        REFERENCES maps (map_id)
            ON DELETE CASCADE
            ON UPDATE NO ACTION
)
"""

# CREATE_UPDATE_TABLE = """
# CREATE TABLE IF NOT EXISTS rank_updates (
#     user_id INTEGER NOT NULL,
#     role    CHAR(1) NOT NULL,
#     rating_id INTEGER NOT NULL,
#     PRIMARY KEY (user_id, role)
# )
# """

SELECT_COUNT = "SELECT COUNT(rating_id) FROM ow2"
SELECT_ALL_PANDAS = """
SELECT users.username as author, maps.map_name as map, ow2.result as winloss, datetime(ow2.datetime, 'unixepoch') as time
    FROM ow2
        INNER JOIN users ON ow2.author_id = users.user_id
        INNER JOIN maps ON ow2.map_id = maps.map_id 
"""
def SELECT_LAST_N(n: int):
    """Method to select `n` entries from the dataset"""
    return f"""
        SELECT ow2.rating_id, users.username, maps.map_name, ow2.result, ow2.datetime
            FROM ow2
                INNER JOIN users ON ow2.author_id = users.user_id
                INNER JOIN maps ON ow2.map_id = maps.map_id 
            ORDER BY rating_id DESC
            LIMIT {min(100, max(1, int(n))):0d}
    """
def SELECT_LAST_N_USERNAME(n: int):
    """Method to select `n` entries from the dataset, filtering by username"""
    return f"""
        SELECT ow2.rating_id, users.username, maps.map_name, ow2.result, ow2.datetime
            FROM ow2
                INNER JOIN users ON ow2.author_id = users.user_id
                INNER JOIN maps ON ow2.map_id = maps.map_id
            WHERE users.username = ?
            ORDER BY rating_id DESC
            LIMIT {min(100, max(1, int(n))):0d}
    """

SELECT_USERID_FROM_USERNAME = "SELECT user_id FROM users WHERE username = ?"
SELECT_MAPID_FROM_MAPNAME = "SELECT map_id FROM maps WHERE map_name = ?"

def DELETE_N_IDS(n: int):
    """Method to delete `n` ids from the dataset"""
    return f"""
        DELETE FROM ow2
            WHERE rating_id IN
                ({', '.join(['?']*n)})
    """

INSERT_INTO_DATA = """
INSERT INTO ow2
    (author_id, map_id, result, datetime)
    VALUES (?, ?, ?, ?)
"""
INSERT_INTO_USERS = "INSERT INTO users (username) values (?)"
INSERT_INTO_MAPS = "INSERT INTO maps (map_name) values (?)"
# INSERT_RANK_UPDATES = """
# INSERT INTO rank_updates
#     (user_id, role, rating_id)
#     VALUES(?, ?, ?)
#     ON CONFLICT(user_id, role)
#     DO UPDATE SET rating_id=?;
# """
