import os
import aiofiles

async def write_line(*args):
    if os.path.exists("data.csv"):
        size = os.path.getsize("data.csv")
        if size:
            async with aiofiles.open("data.csv", mode="a") as file:
                await file.write(",".join(map(str, args)) + "\n")
            return

    async with aiofiles.open("data.csv", mode="w") as file:
        await file.write("author,map,win/loss,role,sentiment,time\n")
        await file.write(",".join(map(str, args)) + "\n")

async def get_last(n: int = 1):
    if os.path.exists("data.csv"):
        async with aiofiles.open("data.csv", mode="r") as file:
            lines = await file.readlines()
            return lines[-n:]

async def delete_last(n: int = 1):
    if os.path.exists("data.csv"):
        async with aiofiles.open("data.csv", mode="r") as file:
            lines = await file.readlines()
        async with aiofiles.open("data.csv", mode="w") as file:
            await file.writelines(lines[:-n])
            return lines[-n:]

async def get_line_count():
    if os.path.exists("data.csv"):
        async with aiofiles.open("data.csv", mode="r") as file:
            lines = await file.readlines()
            return len(lines)
    return -1