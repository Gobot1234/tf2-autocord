import difflib
import logging
import traceback

import discord
from discord.ext import commands

from . import __version__
from .utils.formats import format_exec

log = logging.getLogger(__name__)


class HelpCommand(commands.HelpCommand):  # https://gist.github.com/Rapptz/31a346ed1eb545ddeb0d451d81a60b3b
    def get_ending_note(self):
        return "Use {0}{1} [command] for more info on a command.".format(self.clean_prefix, self.invoked_with)

    def get_command_signature(self, command):
        return "{0.qualified_name} {0.signature}".format(command)

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Bot Commands", colour=self.context.bot.colour)
        description = self.context.bot.description
        if description:
            embed.description = description

        for cog, commands in mapping.items():
            name = "No Category" if cog is None else cog.qualified_name
            filtered = await self.filter_commands(commands, sort=True)
            if filtered:
                value = "\u2002".join(c.name for c in commands)
                if cog and cog.description:
                    value = "{0}\n\n{1}".format(cog.description, value)

                embed.add_field(name=name, value=value)

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(title="{0.qualified_name} Commands".format(cog), colour=self.context.bot.colour)
        if cog.description:
            embed.description = cog.description

        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        for command in filtered:
            embed.add_field(name=self.get_command_signature(command), value=command.short_doc or "...", inline=False)

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        embed = discord.Embed(title=group.qualified_name, colour=self.context.bot.colour)
        if group.help:
            embed.description = group.help

        if isinstance(group, commands.Group):
            filtered = await self.filter_commands(group.commands, sort=True)
            for command in filtered:
                embed.add_field(
                    name=self.get_command_signature(command), value=command.short_doc or "...", inline=False
                )

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    # This makes it so it uses the function above
    # Less work for us to do since they're both similar.
    # If you want to make regular command help look different then override it
    send_command_help = send_group_help

    async def send_error_message(self, error):
        pass

    async def command_not_found(self, string):
        ctx = self.context
        command_names = [command.name for command in ctx.bot.commands]
        close_commands = difflib.get_close_matches(string, command_names, len(command_names), 0)
        joined = "\n".join(f"- `{command}`" for command in close_commands[:2])

        embed = discord.Embed(
            title="**Error 404:**",
            color=discord.Colour.red(),
            description=f'Command or category "{string}" was not found ¯\\_(ツ)_/¯\nPerhaps you meant?:\n{joined}',
        )
        embed.add_field(
            name="The current loaded cogs are:", value=f'(`{"`, `".join(ctx.bot.cogs)}`) :gear:',
        )
        await self.context.send(embed=embed)


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._original_help_command = bot.help_command
        bot.help_command = HelpCommand()
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self._original_help_command

    @commands.Cog.listener()
    async def on_connect(self):
        print(
            f"Logging in as: {self.bot.user.name} V.{__version__} - {self.bot.user.id}"
            f" -- Version: {discord.__version__} of Discord.py"
        )
        log.info(f"Logging in as: {self.bot.user.name} V.{__version__} - {self.bot.user.id}")
        log.info(f"Version: {discord.__version__} of Discord.py")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """The event triggered when an error is raised while invoking a command"""
        traceback.print_exc()
        error = getattr(error, "original", error)

        if isinstance(error, (commands.CommandNotFound, commands.UserInputError)):
            return

        if isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
            return await ctx.send_help(ctx.command)
        elif isinstance(error, commands.CommandOnCooldown):
            title = "Command is on cooldown"
        elif isinstance(error, commands.NotOwner):
            title = "You aren't the owner of the bot"
        else:
            title = "Unspecified error"
        embed = discord.Embed(
            title=f":warning: **{title}**", description=f"```py\n{format_exec(error)}```", color=discord.Colour.red(),
        )
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Help(bot))
