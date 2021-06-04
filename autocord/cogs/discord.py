import os
import traceback
from time import perf_counter
from typing import TYPE_CHECKING

import discord
from jishaku.shell import ShellReader
from discord.ext import commands, tasks

from .utils.choice import wait_for_owners
from .utils.context import Context

if TYPE_CHECKING:
    from .. import AutoCord


class Discord(commands.Cog):
    """Commands that are mostly help commands but more useful"""

    def __init__(self, bot: "AutoCord"):
        self.bot = bot
        self.github_update.start()

    def cog_unload(self):
        self.github_update.cancel()

    @tasks.loop(hours=24)
    async def github_update(self):
        """A tasks loop to check if there has been an update to the GitHub repo"""
        with ShellReader(f"git checkout {os.getcwd()}") as reader:
            result = "\n".join([line async for line in reader])
        if "Your branch is up to date with" in result:
            return
        elif "not a git repository" in result:
            embed = discord.Embed(
                title="This version wasn't cloned from GitHub, which I advise as it allows for automatic updates",
                description=(
                    "Installation is simple type `git clone"
                    " https://github.com/Gobot1234/tf2-autocord.git` into your command"
                    " prompt of choice, although you need to have git"
                ),
                color=discord.Colour.blurple(),
            )
            for owner in self.bot.owners:
                await owner.send(embed=embed)
        else:
            for owner in self.bot.owners:
                message = await owner.send("Fetching info on the latest GitHub changes...")
                ctx: "Context" = await self.bot.get_context(message)
                await ctx.trigger_typing()
                resp = await ctx.request("GET", "https://api.github.com/repos/Gobot1234/tf2-autocord/commits")
                info = resp[0]["commit"]["message"].splitlines()
                version = info[0]
                commit_message = "\n".join(info[1:]).strip()
                embed = discord.Embed(
                    title=f"Version {version} has been pushed to the GitHub repo. Do you want to install it?",
                    description=f"__Update info is as follows:__\n```{commit_message}```",
                    color=discord.Colour.blurple(),
                )
                await message.edit(content=None, embed=embed)

            if await wait_for_owners(ctx):
                for owner in self.bot.owners:
                    await owner.send("Updating from the latest GitHub push")
                command = await ctx.get_output("git pull")
                for owner in self.bot.owners:
                    await owner.send(command)
            else:
                for owner in self.bot.owners:
                    await owner.send(f"I won't update yet")

    @github_update.before_loop
    async def before_github(self):
        await self.bot.wait_until_ready()

    @github_update.after_loop
    async def after_github(self):
        if self.github_update.failed():
            traceback.print_exc()

    @commands.command()
    async def uptime(self, ctx):
        """See how long the bot has been online for"""
        await ctx.send(f"{self.bot.user.mention} has been online for {self.bot.uptime}")

    @commands.command()
    @commands.is_owner()
    @commands.cooldown(rate=1, per=7200, type=commands.BucketType.user)
    async def suggest(self, ctx, *, suggestion):
        """Suggest a feature to <@340869611903909888>
        eg. `{prefix}suggest update the repo` your bot needs to be in the
        [tf2autocord server](discord.gg/S3eVmxD) for this to work"""
        embed = discord.Embed(color=0x2E3BAD, description=suggestion)
        embed.set_author(name=f"Message from {ctx.author}")
        try:
            await self.bot.get_user(340869611903909888).send(embed=embed)
        except discord.HTTPException:
            await ctx.send(
                "I could not deliver your message. ¯\\_(ツ)_/¯, probably as your bot"
                f" isn't in the server send {self.bot.user.id} to <@340869611903909888>"
            )
        else:
            await ctx.send(
                "I have delivered your message to <@340869611903909888> (I may be in"
                " contact), this command is limited to working every 2 hours so you"
                " can't spam me"
            )

    @commands.command()
    async def ping(self, ctx: Context):
        """Check if your bot is online on both Steam and Discord"""
        embed = discord.Embed(color=discord.Colour.blurple()).set_author(name="Pong!")
        start = perf_counter()
        m = await ctx.send(embed=embed)
        end = perf_counter()
        message_duration = (end - start) * 1000

        message = (
            f"{ctx.emoji.tick} You are logged into Steam in as: `{self.bot.client.user}`"
            if self.bot.client
            else f"{ctx.emoji.cross} You aren't logged into Steam"
        )

        embed = discord.Embed(
            description=f"{self.bot.user.mention} is online.\n{message}", colour=discord.Colour.blurple(),
        )
        embed.set_author(name="Pong!", icon_url=self.bot.user.avatar_url)
        embed.add_field(
            name=f":heartbeat: Discord Heartbeat latency is:", value=f"`{self.bot.latency * 1000:.2f}` ms.",
        )
        embed.add_field(
            name=f":heartbeat: Steam Heartbeat latency is:", value=f"`{self.bot.client.latency * 1000:.2f}` ms.",
        )
        embed.add_field(
            name=f"Message latency is:", value=f"`{message_duration:.2f}` ms.",
        )
        await m.edit(embed=embed)


def setup(bot):
    bot.add_cog(Discord(bot))
