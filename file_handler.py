import os

import aiofiles
import pandas as pd

class FileHandler:
    def __init__(self, filename) -> None:        
        self.filename = filename

    async def ensure_file_exists(self):
        """
        makes sure the file exists and contains a header line.
        returns true if file already existed
        """
        if os.path.exists(self.filename):
            size = os.path.getsize(self.filename)
            if size == 0:
                async with aiofiles.open(self.filename, mode="w") as file:
                    await file.write("author,map,win/loss,role,sentiment,time\n")
                    return False

        else:
            async with aiofiles.open(self.filename, mode="w") as file:
                await file.write("author,map,win/loss,role,sentiment,time\n")
                return False

        return True

    async def write_line(self, *args):
        """writes a line of args to file"""
        await self.ensure_file_exists()
        async with aiofiles.open(self.filename, mode="a") as file:
            await file.write(",".join(map(str, args)) + "\n")

    async def get_last(self, n: int = 1):
        """
        gets the last line of data from the file, if present
        note that this requires reading all lines from file, which may
        cause issues in future
        """
        file_existed = await self.ensure_file_exists()
        if file_existed:
            async with aiofiles.open(self.filename, mode="r") as file:
                lines = await file.readlines()
                return lines[-n:]

        return ""

    async def delete_last(self, n: int = 1):
        """
        deletes the last line of data from the file, if present
        note that this requires reading all lines from file, which may
        cause issues in future
        """
        file_existed = await self.ensure_file_exists()
        if file_existed:
            async with aiofiles.open(self.filename, mode="r") as file:
                lines = await file.readlines()
            async with aiofiles.open(self.filename, mode="w") as file:
                await file.writelines(lines[:-n])
                return lines[-n:]

        return ""

    async def get_line_count(self):
        """gets the number of (data) lines in the file"""
        file_existed = await self.ensure_file_exists()
        if file_existed:
            async with aiofiles.open(self.filename, mode="r") as file:
                lines = await file.readlines()
                return len(lines) - 1

        return 0

    def get_pandas_data(self):
        """reads the csv file into a Pandas df"""
        data = pd.read_csv(self.filename)
        data["time"] = pd.to_datetime(data["time"])
        data.rename(columns={"win/loss": "winloss"}, inplace=True)
        return data
