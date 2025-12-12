"""Database connectivity functions"""

import logging
from pathlib import Path
from typing import Optional

import sqlite3
import aiosqlite
import pandas as pd
from datetime import datetime, timezone

from maprater.data.constants import SEASONS, Ranks, FullRank
from maprater.data.queries import *


class DatabaseHandler:
    """A class to manage SQLite databases per-server"""

    def __init__(self, root_dir: str | Path = "") -> None:
        self.root_dir = root_dir
        self.tables = set()

    def get_db_name(self, server_id: int) -> Path:
        assert self.root_dir.is_dir()
        db_path = Path(self.root_dir) / f"{server_id}-v2.db"
        return db_path

    async def _get_user_id(self, server_id: int, username: str):
        """Gets a user ID from a map name, inserting if not present"""
        async with aiosqlite.connect(self.get_db_name(server_id)) as conn:
            cursor = await conn.cursor()

            await cursor.execute(SELECT_USERID_FROM_USERNAME, (username,))
            user_id = await cursor.fetchone()

            if user_id is None:
                await cursor.execute(INSERT_INTO_USERS, (username,))
                await cursor.execute(SELECT_USERID_FROM_USERNAME, (username,))
                user_id = await cursor.fetchone()
                await conn.commit()

        return user_id[0]

    async def _get_map_id(self, server_id: int, mapname: str):
        """Gets a map ID from a map name, inserting if not present"""
        async with aiosqlite.connect(self.get_db_name(server_id)) as conn:
            cursor = await conn.cursor()

            await cursor.execute(SELECT_MAPID_FROM_MAPNAME, (mapname,))
            map_id = await cursor.fetchone()

            if map_id is None:
                await cursor.execute(INSERT_INTO_MAPS, (mapname,))
                await cursor.execute(SELECT_MAPID_FROM_MAPNAME, (mapname,))
                map_id = await cursor.fetchone()
                await conn.commit()

        return map_id[0]

    async def _ensure_tables_exist(self, server_id: int):
        """
        makes sure the required tables exist.
        """
        if server_id in self.tables:
            return True

        async with aiosqlite.connect(self.get_db_name(server_id)) as conn:
            cursor = await conn.cursor()

            await cursor.execute(CREATE_USER_TABLE)
            await cursor.execute(CREATE_MAPS_TABLE)
            await cursor.execute(CREATE_DATA_TABLE)
            await cursor.execute(CREATE_RANK_TABLE)

            await cursor.close()
            await conn.commit()

        self.tables.add(server_id)

    async def write_line(
        self,
        server_id: int,
        username: str,
        mapname: str,
        result: str | int,
        timestamp: float,
    ):
        """writes a map review to the database"""
        await self._ensure_tables_exist(server_id)
        map_id = await self._get_map_id(server_id, mapname)
        user_id = await self._get_user_id(server_id, username)

        if isinstance(result, str):
            rank_change = None
            result_str = result
        elif isinstance(result, int):
            rank_change = result
            if result > 12:
                result_str = "win"
            elif result > 0:
                result_str = "wide-win"
            elif result == 0:
                result_str = "draw"
            elif result <= -12:
                result_str = "wide-loss"
            else:
                result_str = "loss"
        else:
            raise TypeError("invalid result type")

        async with aiosqlite.connect(self.get_db_name(server_id)) as conn:
            cursor = await conn.cursor()

            await cursor.execute(
                INSERT_INTO_DATA,
                (user_id, map_id, result_str, rank_change, int(timestamp)),
            )

            await cursor.close()
            await conn.commit()

    async def get_last(
        self,
        server_id: int,
        count: int = 1,
        username: Optional[str] = None,
        map_name: Optional[str] = None,
    ) -> tuple[list, list]:
        """
        gets the last line of data from the file, if present
        """
        if not isinstance(count, int):
            return [], []

        if count not in list(range(101)):
            return [], []

        await self._ensure_tables_exist(server_id)
        async with aiosqlite.connect(self.get_db_name(server_id)) as conn:
            cursor = await conn.cursor()

            # WARN: This does risk SQL injection! However, given the value is a
            #       bounded int, this should not pose much concern
            if username is not None:
                if map_name is not None:
                    query = SELECT_LAST_N_USERNAME_MAP(count)
                    await cursor.execute(
                        query,
                        (
                            username,
                            map_name,
                        ),
                    )
                else:
                    query = SELECT_LAST_N_USERNAME(count)
                    await cursor.execute(query, (username,))
            elif map_name is not None:
                raise NotImplementedError()
            else:
                query = SELECT_LAST_N(count)
                await cursor.execute(query)

            result = await cursor.fetchall()

            await cursor.close()

        # split into rating id and other information
        return [line[0] for line in result], [line[1:] for line in result]

    async def get_rank(self, server_id: int, username: str) -> FullRank | None:
        logging.info("Getting rank for %s on %d", username, server_id)
        await self._ensure_tables_exist(server_id)
        async with aiosqlite.connect(self.get_db_name(server_id)) as conn:
            cursor = await conn.cursor()
            await cursor.execute(GET_RANK, {"username": username})

            # todo: split into rank, division, percentage
            rank_int = await cursor.fetchone()
            if rank_int is not None and rank_int[0] >= 1000:
                rank = max(0, rank_int[0] - 1000) // 500
                tier = 5 - (rank_int[0] % 500 // 100)
                percentage = rank_int[0] % 100
                return FullRank(Ranks(rank), tier, percentage)
            return None

    async def set_rank(
        self, server_id: int, username: str, rank: Ranks, division: int, percentage: int
    ) -> None:
        logging.info(
            "Setting rank for %s on %d to %s %d %d",
            username,
            server_id,
            rank.name,
            division,
            percentage,
        )

        await self._ensure_tables_exist(server_id)

        assert rank in Ranks
        assert 1 <= division <= 5
        assert 0 <= percentage <= 99

        user_id = await self._get_user_id(server_id, username)

        async with aiosqlite.connect(self.get_db_name(server_id)) as conn:
            cursor = await conn.cursor()
            rank_int = 1000
            rank_int += 500 * rank.value
            rank_int += 100 * (5 - division)
            rank_int += percentage

            timestamp = datetime.now(tz=timezone.utc).timestamp()
            await cursor.execute(
                SET_RANK,
                {"user_id": user_id, "rank": rank_int, "set_time": int(timestamp)},
            )
            await conn.commit()

    async def update_rank(
        self, server_id: int, username: str, percentage: int
    ) -> FullRank | None:
        logging.info(
            "Updating rank for %s on %d by %d", username, server_id, percentage
        )
        await self._ensure_tables_exist(server_id)
        user_id = await self._get_user_id(server_id, username)
        async with aiosqlite.connect(self.get_db_name(server_id)) as conn:
            cursor = await conn.cursor()
            await cursor.execute(GET_RANK, {"username": username})
            rank_int = await cursor.fetchone()
            if rank_int is None or rank_int[0] < 1000:
                raise RuntimeError("cannot update: not set")

            rank_int = min(4999, max(1000, rank_int[0] + percentage))
            await cursor.execute(UPDATE_RANK, {"user_id": user_id, "rank": rank_int})
            await conn.commit()

        rank_tuple = await self.get_rank(server_id, username)
        if rank_tuple is None:
            raise RuntimeError("failed to fetch tuple after setting")
        return rank_tuple

    async def _undo_rank_updates(self, server_id: int, ids: list[int]):
        await self._ensure_tables_exist(server_id)
        async with aiosqlite.connect(self.get_db_name(server_id)) as conn:
            cursor = await conn.cursor()

            for result_id in ids:
                await cursor.execute(SELECT_BY_ID, {"id": result_id})
                result = await cursor.fetchone()

                if result is not None:
                    user_id, username, rank_change, timestamp = result
                    if rank_change is None:
                        continue

                    await cursor.execute(
                        GET_RANK, {"id": user_id, "username": username}
                    )
                    user_rank = await cursor.fetchone()

                    if user_rank is None:
                        continue

                    rank, set_timestamp = user_rank
                    if timestamp < set_timestamp:
                        continue

                    old_rank = max(1000, min(4999, rank - rank_change))

                    await cursor.execute(
                        UPDATE_RANK, {"user_id": user_id, "rank": old_rank}
                    )
                    await conn.commit()

    async def delete_ids(self, server_id: int, ids: list[int]):
        """
        deletes specific ids from the file, if present
        """
        logging.info("Deleting ids %s", ids)

        if len(ids) > 20:
            raise ValueError("Too many ids to delete at once")

        await self._ensure_tables_exist(server_id)
        await self._undo_rank_updates(server_id, ids)
        async with aiosqlite.connect(self.get_db_name(server_id)) as conn:
            cursor = await conn.cursor()

            await cursor.execute(DELETE_N_IDS(len(ids)), ids)
            await cursor.close()
            await conn.commit()

    async def get_line_count(self, server_id: int):
        """gets the number of (data) lines in the file"""
        await self._ensure_tables_exist(server_id)
        async with aiosqlite.connect(self.get_db_name(server_id)) as conn:
            cursor = await conn.cursor()

            await cursor.execute("select count(rating_id) from ow2")
            count = await cursor.fetchone()
            count = count[0]

            await cursor.close()

        return count

    def get_pandas_data(self, server_id: int, season: int | None = None):
        """
        reads the csv file into a Pandas df
        note that this function is *not* async
        """
        logging.info("Getting data as Pandas")

        with sqlite3.connect(self.get_db_name(server_id)) as conn:
            if season and (season + 1 in SEASONS):
                data = pd.read_sql_query(
                    SELECT_ALL_PANDAS_SEASON,
                    conn,
                    params=[SEASONS[season], SEASONS[season + 1]],
                )
            else:
                data = pd.read_sql_query(SELECT_ALL_PANDAS, conn)

        data["time"] = pd.to_datetime(data["time"])
        return data
