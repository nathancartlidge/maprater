import os
from typing import Optional

import aiofiles
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
    map_id    TEXT    NOT NULL,
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

SELECT_LAST_N = lambda n: f"""
SELECT (users.username, maps.map_name, ow2.result, ow2.role, ow2.sentiment,
        datetime(ow2.datetime, 'unixepoch'))
    FROM ow2
        INNER JOIN users ON ow2.author_id = users.user_id
        INNER JOIN maps ON ow2.map_id = maps.map_id 
    ORDER BY rating_id DESC
    LIMIT {min(20, max(1, int(n))):0d};
"""  # FIXME - join to other things
SELECT_USERID_FROM_USERNAME = "SELECT user_id FROM users WHERE username = ?"
SELECT_MAPID_FROM_MAPNAME = "SELECT map_id FROM maps WHERE map_name = ?"

INSERT_INTO_DATA = """
INSERT INTO ow2
    (author_id, map_id, result, role, sentiment, datetime)
    VALUES (?, ?, ?, ?, ?, ?)
"""
INSERT_INTO_USERS = "INSERT INTO users (username) values (?)"
INSERT_INTO_MAPS = "INSERT INTO maps (map_name) values (?)"

class DatabaseHandler:
    def __init__(self, filename) -> None:        
        self.filename = filename
        self.connection: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Connects to the database"""
        self.connection = await aiosqlite.connect(self.filename)

    async def get_user_id(self, cursor: aiosqlite.Cursor, username: str):
        """Gets a user ID from a map name, inserting if not present"""
        user_id = await cursor.execute(
            SELECT_USERID_FROM_USERNAME, (username, )
        ).fetchone()

        if user_id is None:
            await cursor.execute(INSERT_INTO_USERS, (username))
            user_id = await cursor.execute(
                SELECT_USERID_FROM_USERNAME, (username, )
            ).fetchone()

        return user_id[0]

    async def get_map_id(self, cursor: aiosqlite.Cursor, mapname: str):
        """Gets a map ID from a map name, inserting if not present"""
        map_id = await cursor.execute(
            SELECT_MAPID_FROM_MAPNAME, (mapname, )
        ).fetchone()

        if map_id is None:
            await cursor.execute(INSERT_INTO_MAPS, (mapname))
            map_id = await cursor.execute(
                SELECT_USERID_FROM_USERNAME, (mapname, )
            ).fetchone()

        return map_id[0]

    async def ensure_tables_exist(self):
        """
        makes sure the required tables exist.
        """
        if self.connection is None:
            await self.connect()
        
        cursor = await self.connection.cursor()

        await cursor.execute(CREATE_USER_TABLE)
        await cursor.execute(CREATE_MAPS_TABLE)
        await cursor.execute(CREATE_DATA_TABLE)

        await cursor.close()

    async def write_line(self, username, mapname, result, role, sentiment,
                         datetime):
        """writes a map review to a file"""
        if self.connection is None:
            await self.connect()
        
        cursor = await self.connection.cursor()

        map_id = self.get_map_id(cursor, mapname)
        user_id = self.get_user_id(cursor, username)
        
        cursor.execute(INSERT_INTO_DATA, (user_id, map_id, result[0], role[0],
                                          int(sentiment), int(datetime)))

        cursor.close()

    async def get_last(self, n: int = 1):
        """
        gets the last line of data from the file, if present
        note that this requires reading all lines from file, which may
        cause issues in future
        """
        if self.connection is None:
            await self.connect()
        
        cursor = await self.connection.cursor()

        if not isinstance(n, int):
            return None
        
        if n not in list(range(20)):
            return None

        # WARN: This does risk SQL injection! However, given the value is a
        #       bounded int, this should not pose much concern
        cursor.execute(SELECT_LAST_N(n))
        result = cursor.fetchall()

        cursor.close()
        return result

    async def delete_last(self, n: int = 1):
        """
        deletes the last line of data from the file, if present
        note that this requires reading all lines from file, which may
        cause issues in future
        """
        # TODO
        file_existed = await self.ensure_tables_exist()
        if file_existed:
            async with aiofiles.open(self.filename, mode="r") as file:
                lines = await file.readlines()
            async with aiofiles.open(self.filename, mode="w") as file:
                await file.writelines(lines[:-n])
                return lines[-n:]

        return ""

    async def get_line_count(self):
        # TODO
        """gets the number of (data) lines in the file"""
        file_existed = await self.ensure_tables_exist()
        if file_existed:
            async with aiofiles.open(self.filename, mode="r") as file:
                lines = await file.readlines()
                return len(lines) - 1

        return 0

    def get_pandas_data(self):
        # TODO
        """reads the csv file into a Pandas df"""
        data = pd.read_csv(self.filename)
        data["time"] = pd.to_datetime(data["time"])
        data.rename(columns={"win/loss": "winloss"}, inplace=True)
        return data
