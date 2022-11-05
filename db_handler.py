"""Database connectivity functions"""

import logging
from typing import Optional

import sqlite3
import aiosqlite
import pandas as pd

from queries import *

class DatabaseHandler:
    """A class to manage SQLite databases per-server"""
    def __init__(self, root_dir: str = "") -> None:
        self.root_dir = root_dir
        self.tables = set()

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
        if server_id in self.tables:
            return True

        async with aiosqlite.connect(f"{self.root_dir}{server_id}.db") as conn:
            cursor = await conn.cursor()

            await cursor.execute(CREATE_USER_TABLE)
            await cursor.execute(CREATE_MAPS_TABLE)
            await cursor.execute(CREATE_DATA_TABLE)
            await cursor.execute(CREATE_UPDATE_TABLE)

            await cursor.close()
            await conn.commit()

        self.tables.add(server_id)

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

    async def get_last(self, server_id: int, count: int = 1,
                       username: Optional[str] = None) -> tuple[list, list]:
        """
        gets the last line of data from the file, if present
        """
        if not isinstance(count, int):
            return [], []

        if count not in list(range(21)):
            return [], []

        await self._ensure_tables_exist(server_id)
        async with aiosqlite.connect(f"{self.root_dir}{server_id}.db") as conn:
            cursor = await conn.cursor()

            # WARN: This does risk SQL injection! However, given the value is a
            #       bounded int, this should not pose much concern
            if username is None:
                await cursor.execute(SELECT_LAST_N(count))
            else:
                await cursor.execute(SELECT_LAST_N_USERNAME(count), (username,))

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

        await self._ensure_tables_exist(server_id)
        async with aiosqlite.connect(f"{self.root_dir}{server_id}.db") as conn:
            cursor = await conn.cursor()

            await cursor.execute(DELETE_N_IDS(len(ids)), ids)
            await cursor.close()
            await conn.commit()

    async def get_line_count(self, server_id: int):
        """gets the number of (data) lines in the file"""
        await self._ensure_tables_exist(server_id)
        async with aiosqlite.connect(f"{self.root_dir}{server_id}.db") as conn:
            cursor = await conn.cursor()

            await cursor.execute("select count(rating_id) from ow2")
            count = await cursor.fetchone()
            count = count[0]

            await cursor.close()

        return count

    async def _test_rank_update(self, server_id: int, username: str, role: str):
        """Tests if a rank update is expected"""
        needs_update = False
        await self._ensure_tables_exist(server_id)
        async with aiosqlite.connect(f"{self.root_dir}{server_id}.db") as conn:
            cursor = await conn.cursor()

            print(f"\n\n\n{role=}, {username=}\n\n\n")
            await cursor.execute(CHECK_RANK_UPDATE, (role, username))
            result = await cursor.fetchall()
            result_dict = dict(result)
            loss_count = result_dict.get("l", 0)
            win_count = result_dict.get("w", 0)
            if loss_count >= 20:
                needs_update = True
            elif win_count >= 7:
                needs_update = True

            logging.info("%s / %s", loss_count, win_count)

            await cursor.close()

        return needs_update

    async def do_rank_update(self, server_id: int, username: str, role: str,
                             force: bool = False):
        """Checks if a rank update is expected, performing one if needed"""
        needs_update = await self._test_rank_update(server_id, username, role)
        if needs_update or force:
            user_id = await self._get_user_id(server_id, username)
            last_id, _ = await self.get_last(server_id, 1, username)
            if len(last_id) == 1:
                last_id = last_id[0]

            else:
                last_id = -1

            logging.info("last id is %s", last_id)

            result_str = None
            async with aiosqlite.connect(f"{self.root_dir}{server_id}.db") as conn:
                cursor = await conn.cursor()
                await cursor.execute(GET_GAMES_SINCE_UPDATE, (role, user_id))
                result = "".join(map(lambda x: x[0], await cursor.fetchall()))
                if result != "":
                    result_str = result

                await cursor.execute(INSERT_RANK_UPDATES, (user_id, role, last_id, last_id))
                await cursor.close()
                await conn.commit()

            return True, result_str

        return False, None

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
