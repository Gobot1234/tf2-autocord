import asyncio

from autocord import AutoCord


async def main():
    print("Starting...")
    bot = AutoCord()
    try:
        await bot.start()
    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
