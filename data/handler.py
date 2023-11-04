"""Database connectivity functions"""

import logging
from typing import Optional

import aiosqlite

from definitions import Results, Roles
from data.queries import *


class DatabaseHandler:
    """A class to manage SQLite databases per-server"""
    def __init__(self, root_dir: str = "") -> None:
        self.root_dir = root_dir
        self.tables = set()
        self._username_map = {}

    def file(self, server_id: int):
        return f"{self.root_dir}{server_id}-sr.db"

    def set_identity(self, server_id: int, username: str, profile: Optional[str]):
        if profile is None:
            try:
                self._username_map.pop(f"{server_id}--{username}")
            except KeyError:
                pass
        else:
            self._username_map[f"{server_id}--{username}"] = f"{username}--{profile}"

    async def _get_user_id(self, server_id: int, username: str):
        """Gets a user ID from a map name, inserting if not present"""
        profile_username = self._username_map.get(f"{server_id}--{username}", username)

        await self._ensure_tables_exist(server_id)
        async with aiosqlite.connect(self.file(server_id)) as conn:
            cursor = await conn.cursor()

            await cursor.execute(SELECT_USERID_FROM_USERNAME, (profile_username, ))
            user_id = await cursor.fetchone()

            if user_id is None:
                await cursor.execute(INSERT_INTO_USERS, (profile_username, ))
                await cursor.execute(SELECT_USERID_FROM_USERNAME, (profile_username, ))
                user_id = await cursor.fetchone()
                for role in Roles:
                    await cursor.execute(
                        DO_RANK_UPDATE,
                        parameters={"userid": user_id[0], "role": role.name[0], "ratingid": -1}
                    )
                await conn.commit()

        return user_id[0]

    async def _ensure_tables_exist(self, server_id: int):
        """
        makes sure the required tables exist.
        """
        if server_id in self.tables:
            return True

        async with aiosqlite.connect(self.file(server_id)) as conn:
            cursor = await conn.cursor()

            await cursor.execute(CREATE_USER_TABLE)
            await cursor.execute(CREATE_DATA_TABLE)
            await cursor.execute(CREATE_UPDATE_TABLE)

            await cursor.close()
            await conn.commit()

        self.tables.add(server_id)

    async def do_update(self, server_id: int, username: str, result: Results,
                        role: Roles, datetime: float):
        """writes a map review to the database"""
        await self._ensure_tables_exist(server_id)
        user_id = await self._get_user_id(server_id, username)

        async with aiosqlite.connect(self.file(server_id)) as conn:
            cursor = await conn.cursor()

            await cursor.execute(
                sql=INSERT_INTO_DATA,
                parameters=(user_id, result.name[0], role.name[0], int(datetime))
            )

            await cursor.close()
            await conn.commit()

    async def get_last(self, server_id: int, count: int = 1,
                       username: Optional[str] = None,
                       role: Optional[Roles] = None) -> tuple[list, list]:
        """
        gets the last line of data from the file, if present
        """
        if not isinstance(count, int):
            return [], []

        if count not in list(range(101)):
            return [], []

        role_char = None if role is None else role.name[0]

        await self._ensure_tables_exist(server_id)
        async with aiosqlite.connect(self.file(server_id)) as conn:
            cursor = await conn.cursor()

            # WARN: This does risk SQL injection! However, given the value is a
            #       bounded int, this should not pose much concern
            if username is not None:
                if role_char is not None:
                    query = SELECT_LAST_N_USERNAME_ROLE(count)
                    await cursor.execute(query, {"username": username, "role": role_char})
                else:
                    query = SELECT_LAST_N_USERNAME(count)
                    await cursor.execute(query, {"username": username})

            elif role_char is not None:
                query = SELECT_LAST_N_ROLE(count)
                await cursor.execute(query, {"role": role_char})

            else:
                query = SELECT_LAST_N(count)
                await cursor.execute(query)

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
        async with aiosqlite.connect(self.file(server_id)) as conn:
            cursor = await conn.cursor()

            await cursor.execute(DELETE_N_IDS(len(ids)), ids)
            await cursor.close()
            await conn.commit()

    async def get_line_count(self, server_id: int):
        """gets the number of (data) lines in the file"""
        await self._ensure_tables_exist(server_id)
        async with aiosqlite.connect(self.file(server_id)) as conn:
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
        async with aiosqlite.connect(self.file(server_id)) as conn:
            cursor = await conn.cursor()

            await cursor.execute(CHECK_RANK_UPDATE, (role, username))
            result = await cursor.fetchall()
            result_dict = dict(result)  # noqa
            loss_count = result_dict.get(Results.LOSS.name[0], 0) + result_dict.get(Results.DRAW.name[0], 0)
            win_count = result_dict.get(Results.WIN.name[0], 0)
            if loss_count >= 15:
                needs_update = True
            elif win_count >= 5:
                needs_update = True

            logging.info("%s / %s", loss_count, win_count)

            await cursor.close()

        return needs_update

    async def do_rank_update(self, server_id: int, username: str, role: Roles,
                             force: bool = False):
        """Checks if a rank update is expected, performing one if needed"""
        needs_update = await self._test_rank_update(server_id, username, role.name[0])
        user_id = await self._get_user_id(server_id, username)
        last_id, _ = await self.get_last(server_id, 1, username)
        if len(last_id) == 1:
            last_id = last_id[0]
        else:
            last_id = -1

        logging.info("last id is %s", last_id)

        async with aiosqlite.connect(self.file(server_id)) as conn:
            cursor = await conn.cursor()
            await cursor.execute(GET_GAMES_SINCE_UPDATE, (role.name[0], user_id))

            result_mapping = {"W": Results.WIN, "D": Results.DRAW, "L": Results.LOSS}

            result = [result_mapping[x] for x, in await cursor.fetchall()]

            if needs_update or force:
                await cursor.execute(
                    DO_RANK_UPDATE,
                    parameters={"userid": user_id, "role": role.name[0], "ratingid": last_id}
                )

            await cursor.close()

            if needs_update or force:
                await conn.commit()

        return needs_update or force, result

    async def get_sr(self, server_id: int, username: str, role: Roles):
        """Gets the current SR of a player"""
        user_id = await self._get_user_id(server_id, username)
        async with aiosqlite.connect(self.file(server_id)) as conn:
            cursor = await conn.cursor()
            await cursor.execute(GET_SR, (role.name[0], user_id))
            result = await cursor.fetchone()
            await cursor.close()

        return result[0]

    async def set_sr(self, server_id: int, username: str, role: Roles, sr: int):
        """Gets the current SR of a player"""
        user_id = await self._get_user_id(server_id, username)
        async with aiosqlite.connect(self.file(server_id)) as conn:
            cursor = await conn.cursor()
            await cursor.execute(SET_SR, (sr, role.name[0], user_id))
            await conn.commit()
            await cursor.close()
