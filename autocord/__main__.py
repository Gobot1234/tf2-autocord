# -*- coding: utf-8 -*-

import logging
import re
from pathlib import Path
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

import aiohttp
import discord
import humanize
import steam
from discord.ext import commands, tasks

from cogs.utils.context import Contexter
from cogs.utils.formats import human_join

try:
    import cogs.config.preferences as preferences
    import cogs.config.sensitives as sensitives
except ImportError:
    print(
        "Have you set up the preferences and sensitives,"
        'Make sure to remove the leading "_" from the files if you haven\'t'
    )
    raise SystemExit

if TYPE_CHECKING:
    import asyncio

log = logging.getLogger(__name__)


class SteamClient(steam.Client):
    def __init__(self, loop: "asyncio.AbstractEventLoop", bot: "AutoCord"):
        if preferences.play_tf2:
            super().__init__(loop, game=steam.TF2)
        else:
            super().__init__(loop)
        self.bot = bot
        self.steam_bots: Optional[List[steam.User]] = None
        self.first = True

    async def on_ready(self) -> None:
        log.debug("Steam Client is ready")
        print("------------")
        print("Logged in to Steam as")
        print("Username:", self.user.name)
        print("ID:", self.user.id64)
        print("------------")
        self.steam_bots = [
            self.get_user(steam_bot) for steam_bot in preferences.bots_steam_ids
        ]

    @tasks.loop(minutes=10)
    async def user_message(self, message):
        embed = discord.Embed(color=discord.Colour.dark_gold())
        embed.set_author(
            name=f"Message from {message.author}",
            url=message.author.community_url,
            icon_url=message.author.avatar_url,
        )
        embed.add_field(
            name="User Message:",
            value=(
                "You have a message from a user:\n>"
                f' {message.content.split(":", 1)[1]}\nType'
                f" {self.bot.command_prefix}acknowledged to stop receiving these"
                " messages."
            ),
        )
        if self.first:
            self.bot.pins = []
            for owner in self.bot.owners:
                message = await owner.send(embed=embed)
                try:
                    await message.pin()
                except discord.HTTPException:
                    pass
                else:
                    self.bot.messages.append(message)
        else:
            for channel in self.bot.channels:
                await channel.send(embed=embed)

    async def on_message(self, message: steam.Message):
        if message.author in self.steam_bots:
            log.info(f"Received a message from {message.author}")
            if message.content.startswith("Message from"):  # we have a user message
                log.debug("Starting a user message loop")
                self.user_message.cancel()
                self.user_message.start(message)
            else:
                if message.content.startswith("Trade "):
                    await self.send_trade_info(message)
                elif message.content.startswith("Offer "):
                    await self.send_review_info(message)
                else:
                    embed = discord.Embed(
                        color=self.bot.colour,
                        title="New Message:",
                        description=message.content,
                    )
                    embed.set_footer(
                        text=datetime.now().strftime("%c"),
                        icon_url=self.bot.user.avatar_url,
                    )
                    await self.send(embed=embed)

    async def send_trade_info(self, message: steam.Message):
        color = 0x5C7E10 if "accepted" in message.content else discord.Colour.red()
        embed = discord.Embed(color=color)

        trade_id, user_id = re.findall(r"\d+", message.content)
        steam_id = steam.SteamID(int(user_id))
        trader = (
            await self.fetch_user(steam_id.id64) or steam_id
        )  # api calls aren't that bad on steam
        message = message.content.replace(f" #{trade_id}", "")
        message = message.replace(
            f"Trade with {user_id} is", f"A trade with {trader} has been marked as",
        )
        message = message.replace("Summary:", "\n__Summary:__")
        message = message.replace("Asked:", "- **Asked:**")
        message = message.replace("Offered:", "- **Offered:**")
        embed.set_author(
            name=f"Received a trade from: {trader}",
            url=trader.community_url,
            icon_url=trader.avatar_url if isinstance(trader, steam.User) else "",
        )
        embed.description = message
        embed.set_footer(text=f"Trade #{trade_id}", icon_url=self.bot.user.avatar_url)
        embed.timestamp = datetime.now()
        await self.send(embed=embed)

    async def send_review_info(self, message: steam.Message):
        if "not active" in message.content:
            embed = discord.Embed(
                color=self.bot.colour,
                title="Offer review status:",
                description=message.content,
            )
            embed.set_footer(
                text=f'• {datetime.now().strftime("%c")}',
                icon_url=self.bot.user.avatar_url,
            )
        elif "not exist" in message.content:
            embed = discord.Embed(
                color=self.bot.colour,
                title="Offer review status:",
                description=message.content,
            )
            embed.set_footer(
                text=f'• {datetime.now().strftime("%c")}',
                icon_url=self.bot.user.avatar_url,
            )
        else:
            embed = discord.Embed(color=self.bot.colour)
            trade_id, user_id = re.findall(r"\d+", message.content)
            steam_id = steam.SteamID(int(user_id))
            trader = (
                await self.fetch_user(steam_id.id64) or steam_id
            )  # api calls aren't that bad on steam
            message = message.content.replace(f" #{trade_id}", "")
            if trader is not None:
                message = message.replace(
                    f"Offer from {trader} is waiting for review",
                    f"An offer (#{trade_id}) sent by {trader} ({trader.id64}) is"
                    " waiting for review",
                )
                message = message.replace("Summary:", "\n__Summary:__")
                message = message.replace("Asked:", "- **Asked:**")
                message = message.replace("Offered:", "- **Offered:**")
                embed.set_author(
                    name=f"Offer from: {trader.name}",
                    url=trader.community_url,
                    icon_url=trader.avatar_url,
                )
            embed.description = message
            embed.set_footer(
                text=f'Offer #{trade_id} • {datetime.now().strftime("%c")}',
                icon_url=self.bot.user.avatar_url,
            )
            await self.send(
                f"{human_join([o.mention for o in self.bot.owners])} check this!"
            )
        await self.send(embed=embed)

    async def send(
        self,
        content: str = None,
        *,
        embed: discord.Embed = None,
        file: discord.File = None,
    ):
        for channel in self.bot.channels:
            await channel.send(content, embed=embed, file=file)


class AutoCord(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            case_insensitive=True,
            owner_ids=preferences.owner_ids,
            intents=discord.Intents.all()
        )
        self.client = SteamClient(loop=self.loop, bot=self)
        self.first = True

        self.log: Optional[logging.Logger] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.initial_extensions = [
            f"cogs.{file.name[:-3]}"
            for file in (Path(__file__).parent / "cogs").iterdir()
            if file.name.endswith(".py") and file.name != "__init__.py"
        ]
        log.info(f"Extensions to be loaded are {human_join(self.initial_extensions)}")
        self.launch_time: datetime
        self.messages: List[discord.Message] = []
        self.colour = discord.Colour(preferences.embed_colour)

    @property
    def owners(self) -> List[discord.User]:
        return [self.get_user(owner_id) for owner_id in self.owner_ids]

    @property
    def channels(self) -> List[discord.abc.Messageable]:
        return [self.get_channel(preferences.channel_id)] or self.owners

    @property
    def uptime(self):
        return humanize.naturaldelta(datetime.utcnow() - self.launch_time)

    async def on_ready(self):
        print("------------")
        print("Logged in to Discord as")
        print("Username:", self.user.name)
        print("ID:", self.user.id)
        print("------------")
        owners = [f"{owner.name}'s" for owner in self.owners]
        activity = discord.Activity(
            type=discord.ActivityType.watching, name=f"{human_join(owners)} trades"
        )
        await self.change_presence(activity=activity)

    async def on_extension_load(self, extension: Exception):
        log.info(f"Loaded {extension} cog")

    async def on_extension_reload(self, extension: Exception):
        log.info(f"Reloaded {extension} cog")

    async def on_extension_fail(self, extension, error: Exception):
        log.error(f"Failed to load extension {extension}.")
        log.exception(error)
        raise error

    def setup_logging(self):
        log_level = logging.DEBUG
        format_string = "%(asctime)s : %(name)s - %(levelname)s | %(message)s"
        log_format = logging.Formatter(format_string)

        log_file = Path("logs")
        log_file.mkdir(exist_ok=True)
        filename = f'logs/out--{datetime.now().strftime("%d-%m-%Y")}.log'
        file_handler = logging.FileHandler(filename)
        file_handler.setFormatter(log_format)

        log.setLevel(log_level)
        log.addHandler(file_handler)

        logging.getLogger("discord").setLevel(logging.WARNING)
        logging.getLogger("steam").setLevel(logging.WARNING)
        log.info("Finished setting up logging")

    def load_extension(self, name: str):
        try:
            super().load_extension(name)
        except Exception as exc:
            bot.dispatch("extension_fail", name, exc)
        else:
            bot.dispatch("extension_load", name)

    async def start(self):
        self.setup_logging()

        self.session = aiohttp.ClientSession(loop=self.loop)
        for extension in self.initial_extensions:
            self.load_extension(extension)
        self.load_extension("jishaku")

        self.launch_time = datetime.utcnow()
        self.loop.create_task(
            self.client.start(
                username=sensitives.username,
                password=sensitives.password,
                shared_secret=sensitives.shared_secret,
            )
        )
        await super().start(sensitives.token)

    async def get_context(self, message, *, cls: Optional[commands.Context] = None):
        return await super().get_context(message, cls=cls or Contexter)

    async def close(self):
        log.debug("Shutting down")
        await self.session.close()
        await self.client.close()
        await super().close()


if __name__ == "__main__":
    print("Starting...")
    bot = AutoCord()
    bot.run()
