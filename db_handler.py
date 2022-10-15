import logging

import sqlite3
import aiosqlite
import pandas as pd

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
    result    CHAR(1) NOT NULL,
    role      CHAR(1) NOT NULL,
    sentiment INTEGER NOT NULL,
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

SELECT_COUNT = "SELECT COUNT(rating_id) FROM ow2"
SELECT_ALL_PANDAS = """
SELECT users.username as author, maps.map_name as map, ow2.result as winloss,
       ow2.role, ow2.sentiment, datetime(ow2.datetime, 'unixepoch') as time
    FROM ow2
        INNER JOIN users ON ow2.author_id = users.user_id
        INNER JOIN maps ON ow2.map_id = maps.map_id 
"""
SELECT_LAST_N = lambda n: f"""
SELECT ow2.rating_id, users.username, maps.map_name, ow2.result, ow2.role,
       ow2.sentiment, ow2.datetime
    FROM ow2
        INNER JOIN users ON ow2.author_id = users.user_id
        INNER JOIN maps ON ow2.map_id = maps.map_id 
    ORDER BY rating_id DESC
    LIMIT {min(20, max(1, int(n))):0d};
"""
SELECT_USERID_FROM_USERNAME = "SELECT user_id FROM users WHERE username = ?"
SELECT_MAPID_FROM_MAPNAME = "SELECT map_id FROM maps WHERE map_name = ?"

DELETE_N_IDS = lambda n: f"""
DELETE FROM ow2
    WHERE rating_id IN
        ({', '.join(['?']*n)})
"""

INSERT_INTO_DATA = """
INSERT INTO ow2
    (author_id, map_id, result, role, sentiment, datetime)
    VALUES (?, ?, ?, ?, ?, ?)
"""
INSERT_INTO_USERS = "INSERT INTO users (username) values (?)"
INSERT_INTO_MAPS = "INSERT INTO maps (map_name) values (?)"

class DatabaseHandler:
    """A class to manage SQLite databases per-server"""
    def __init__(self, root_dir: str = "") -> None:
        self.root_dir = root_dir

    async def _get_user_id(self, server_id: int, username: str):
        """Gets a user ID from a map name, inserting if not present"""
        async with aiosqlite.connect(f"{self.root_dir}{server_id}.db") as conn:
            cursor = await conn.cursor()

            await cursor.execute(SELECT_USERID_FROM_USERNAME, (username, ))
            user_id = await cursor.fetchone()

            if user_id is None:
                await cursor.execute(INSERT_INTO_USERS, (username, ))
                await cursor.execute(SELECT_USERID_FROM_USERNAME, (username, ))
                user_id = await cursor.fetchone()
                await conn.commit()

        return user_id[0]

    async def _get_map_id(self, server_id: int, mapname: str):
        """Gets a map ID from a map name, inserting if not present"""
        async with aiosqlite.connect(f"{self.root_dir}{server_id}.db") as conn:
            cursor = await conn.cursor()

            await cursor.execute(SELECT_MAPID_FROM_MAPNAME, (mapname, ))
            map_id = await cursor.fetchone()

            if map_id is None:
                await cursor.execute(INSERT_INTO_MAPS, (mapname, ))
                await cursor.execute(SELECT_MAPID_FROM_MAPNAME, (mapname, ))
                map_id = await cursor.fetchone()
                await conn.commit()

        return map_id[0]

    async def _ensure_tables_exist(self, server_id: int):
        """
        makes sure the required tables exist.
        """
        async with aiosqlite.connect(f"{self.root_dir}{server_id}.db") as conn:
            cursor = await conn.cursor()

            await cursor.execute(CREATE_USER_TABLE)
            await cursor.execute(CREATE_MAPS_TABLE)
            await cursor.execute(CREATE_DATA_TABLE)

            await cursor.close()
            await conn.commit()

    async def write_line(self, server_id: int, username: str, mapname: str,
                         result: str, role: str, sentiment: int,
                         datetime: float):
        """writes a map review to the database"""
        await self._ensure_tables_exist(server_id)
        map_id = await self._get_map_id(server_id, mapname)
        user_id = await self._get_user_id(server_id, username)

        async with aiosqlite.connect(f"{self.root_dir}{server_id}.db") as conn:
            cursor = await conn.cursor()

            await cursor.execute(INSERT_INTO_DATA, (user_id, map_id, result[0],
                                                    role[0], int(sentiment),
                                                    int(datetime)))

            await cursor.close()
            await conn.commit()

    async def get_last(self, server_id: int, n: int = 1):
        """
        gets the last line of data from the file, if present
        """
        if not isinstance(n, int):
            return [], []

        if n not in list(range(21)):
            return [], []

        async with aiosqlite.connect(f"{self.root_dir}{server_id}.db") as conn:
            cursor = await conn.cursor()
            await self._ensure_tables_exist(server_id)

            # WARN: This does risk SQL injection! However, given the value is a
            #       bounded int, this should not pose much concern
            await cursor.execute(SELECT_LAST_N(n))
            result = await cursor.fetchall()

            await cursor.close()

        # split into rating id and other information
        return [line[0] for line in result], [line[1:] for line in result]

    async def delete_ids(self, server_id: int, ids: list[int]):
        """
        deletes specific ids from the file, if present
        """
        logging.info("Deleting ids %s", ids)

        if len(ids) > 20:
            return

        async with aiosqlite.connect(f"{self.root_dir}{server_id}.db") as conn:
            cursor = await conn.cursor()
            await self._ensure_tables_exist(server_id)

            await cursor.execute(DELETE_N_IDS(len(ids)), ids)
            await cursor.close()
            await conn.commit()

    async def get_line_count(self, server_id: int):
        """gets the number of (data) lines in the file"""
        async with aiosqlite.connect(f"{self.root_dir}{server_id}.db") as conn:
            cursor = await conn.cursor()
            await self._ensure_tables_exist(server_id)

            await cursor.execute("select count(rating_id) from ow2")
            count = await cursor.fetchone()
            count = count[0]

            await cursor.close()

        return count

    def get_pandas_data(self, server_id: int):
        """
        reads the csv file into a Pandas df
        note that this function is *not* async
        """

        logging.info("Getting data as Pandas")

        with sqlite3.connect(f"{self.root_dir}{server_id}.db") as conn:
            data = pd.read_sql_query(SELECT_ALL_PANDAS, conn)

        data["time"] = pd.to_datetime(data["time"])
        return data
