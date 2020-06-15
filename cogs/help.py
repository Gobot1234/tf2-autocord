# -*- coding: utf-8 -*-

import difflib
import logging
import os
from re import split

import discord
from discord.ext import commands, menus

from . import __version__
from .utils.formats import format_exec
from .utils.paginator import ScrollingPaginatorBase

log = logging.getLogger(__name__)


class HelpCommandPaginator(ScrollingPaginatorBase):
    """The paginator for our HelpCommand"""
    def __init__(self, bot: commands.Bot, entries: list, help_command):
        super().__init__(entries=entries)
        self.bot = bot
        self.page = 0
        self.help_command = help_command

    async def send_initial_message(self, ctx, channel):
        cog = self.bot.get_cog(self.entries[0])
        return await ctx.send(embed=await self.invoke(cog))

    @menus.button('ℹ')
    async def show_info(self, payload):
        """Shows this message"""
        embed = discord.Embed(
            title=f"Help with {self.bot.user.name}'s commands",
            description=self.bot.description)
        embed.add_field(
            name=f'Currently there are {len(self.entries)} cogs loaded, which includes '
                 f'(`{"`, `".join(self.entries)}`) :gear:',
            value='`<...>` indicates a required argument\n'
                  '`[...]` indicates an optional argument.\n\n'
                  "**Don't however type these around your argument**")
        helper = [(button.emoji, button.action.__doc__) for button in self.buttons.values()]
        embed.add_field(name='What do the buttons do?:',
                        value='\n'.join([f'{button} - {doc}' for (button, doc) in helper if button and doc]))
        embed.set_author(name=f'You were on page {self.page + 1}/{len(self.entries)} before',
                         icon_url=self.ctx.author.avatar_url)
        embed.set_footer(text=f'Use "{self.help_command.clean_prefix}help <command>" for more info on a command.',
                         icon_url=self.bot.user.avatar_url)
        await self.message.edit(embed=embed)

    async def next_page(self):
        self.page += 1
        try:
            cog = self.bot.get_cog(self.entries[self.page])
        except IndexError:
            return
        else:
            embed = await self.invoke(cog)
            await self.message.edit(embed=embed)

    async def previous_page(self):
        self.page -= 1
        try:
            cog = self.bot.get_cog(self.entries[self.page])
        except IndexError:
            return
        else:
            embed = await self.invoke(cog)
            await self.message.edit(embed=embed)

    async def first_page(self):
        self.page = 0
        cog = self.bot.get_cog(self.entries[self.page])
        embed = await self.invoke(cog)
        await self.message.edit(embed=embed)

    async def final_page(self):
        self.page = len(self.entries) - 1
        cog = self.bot.get_cog(self.entries[self.page])
        embed = await self.invoke(cog)
        await self.message.edit(embed=embed)

    async def invoke(self, cog: commands.Cog):
        useable_commands = 0
        embed = discord.Embed(description=cog.description, color=discord.Colour.blurple())
        for command in await self.help_command.filter_commands(cog.walk_commands()):
            try:
                if await command.can_run(self.ctx) and not command.hidden:
                    signature = self.help_command.get_command_signature(command)
                    description = self.help_command.get_command_description(command)
                    if command.parent:
                        if command.parent.hidden:
                            continue
                        embed.add_field(name=signature, value=description)
                        useable_commands += 1
                    else:
                        embed.add_field(name=signature, value=description, inline=False)
                        useable_commands += 1
            except commands.CommandError:
                pass
        embed.set_footer(text=f'Page {self.page + 1}/{len(self.entries)}. '
                              f'Use "{self.help_command.clean_prefix}help <command>" for more info on a command.',
                         icon_url=self.bot.user.avatar_url)
        embed.title = f'Help with {cog.qualified_name} ({useable_commands} ' \
                      f'command{"s" if useable_commands != 1 else ""})'
        return embed


class HelpCommand(commands.HelpCommand):
    """The custom help command class for the bot"""

    def __init__(self):
        super().__init__(verify_checks=True, command_attrs={
            'help': 'Shows help about the bot, a command, or a cog'
        })

    def get_command_signature(self, command) -> str:
        if not command.signature and not command.parent:
            return f'`{self.clean_prefix}{command.name}`'
        if command.signature and not command.parent:
            sig = '` `'.join(split(r'\B ', command.signature))
            return f'`{self.clean_prefix}{command.name}` `{sig}`'
        if not command.signature and command.parent:
            return f'**╚╡** `{command.name}`'
        else:
            return '**╚╡** `{}` `{}`'.format(command.name, '`, `'.join(split(r'\B ', command.signature)))

    @staticmethod
    def get_command_aliases(command) -> str:
        if not command.aliases:
            return ''
        else:
            return f'command aliases are [`{"` | `".join(command.aliases)}`]'

    def get_command_description(self, command) -> str:
        if not command.short_doc:
            return 'There is no documentation for this command currently'
        else:
            return command.short_doc.format(prefix=self.clean_prefix)

    def get_command_help(self, command) -> str:
        if not command.help:
            return 'There is currently no documentation for this command'
        else:
            return command.help.format(prefix=self.clean_prefix)

    async def send_bot_help(self, mapping):
        cogs = [name for name, obj in self.context.bot.cogs.items()
                if await discord.utils.maybe_coroutine(obj.cog_check, self.context)]
        cogs.sort()
        paginator = HelpCommandPaginator(entries=cogs, bot=self.context.bot, help_command=self)
        await paginator.start(self.context)

    async def send_cog_help(self, cog):
        paginator = HelpCommandPaginator(entries=[cog.qualified_name], bot=self.context.bot, help_command=self)
        await paginator.start(self.context)

    async def send_command_help(self, command):
        ctx = self.context

        if await command.can_run(ctx):
            embed = discord.Embed(title=f'Help with `{command.name}`', color=0x2E3BAD)
            embed.set_author(
                name=f'We are currently looking at the {command.cog.qualified_name} cog and its command {command.name}',
                icon_url=ctx.author.avatar_url)
            signature = self.get_command_signature(command)
            description = self.get_command_help(command)
            aliases = self.get_command_aliases(command)

            if command.parent:
                embed.add_field(name=signature, value=description, inline=False)
            else:
                embed.add_field(name=f'{signature} {aliases}', value=description, inline=False)
            embed.set_footer(text=f'Use "{self.clean_prefix}help <command>" for more info on a command.')
            await ctx.send(embed=embed)

    async def send_group_help(self, group):
        ctx = self.context
        bot = ctx.bot

        embed = discord.Embed(title=f'Help with `{group.name}`', description=bot.get_command(group.name).help,
                              color=bot.colour)
        embed.set_author(
            name=f'We are currently looking at the {group.cog.qualified_name} cog and its command {group.name}',
            icon_url=ctx.author.avatar_url)
        for command in group.walk_commands():
            if await command.can_run(ctx):
                signature = self.get_command_signature(command)
                description = self.get_command_description(command)
                aliases = self.get_command_aliases(command)

                if command.parent:
                    embed.add_field(name=signature, value=description, inline=False)
                else:
                    embed.add_field(name=f'{signature} {aliases}', value=description, inline=False)
        embed.set_footer(text=f'Use "{self.clean_prefix}help <command>" for more info on a command.')
        await ctx.send(embed=embed)

    async def send_error_message(self, error):
        pass

    async def command_not_found(self, string):
        ctx = self.context
        command_names = [command.name for command in ctx.bot.commands]
        close_commands = difflib.get_close_matches(string, command_names, len(command_names), 0)
        joined = '\n'.join(f'- `{command}`' for command in close_commands[:2])

        embed = discord.Embed(
            title='**Error 404:**', color=discord.Colour.red(),
            description=f'Command or category "{string}" was not found ¯\\_(ツ)_/¯\nPerhaps you meant?:\n{joined}')
        embed.add_field(name='The current loaded cogs are:',
                        value=f'(`{"`, `".join(ctx.bot.cogs)}`) :gear:')
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
    async def on_ready(self):
        try:
            channel = self.bot.get_channel(int(open('channel.txt', 'r').read()))
            os.remove('channel.txt')
        except FileNotFoundError:
            pass
        else:
            if channel:
                deleted = 0
                async for m in channel.history(limit=50):
                    if m.author == self.bot.user and deleted < 2:
                        await m.delete()
                        deleted += 1
                    if m.author in self.bot.owners and m.content == '!restart':
                        try:
                            await m.delete()
                        except discord.Forbidden:
                            pass
                await channel.send('Finished restarting...', delete_after=60)
        print(f'Successfully logged in as {self.bot.user.name} and booted...!')
        log.info(f'Successfully logged in as {self.bot.user.name} and booted...!')

    @commands.Cog.listener()
    async def on_connect(self):
        print(f'Logging in as: {self.bot.user.name} V.{__version__} - {self.bot.user.id} -- '
              f'Version: {discord.__version__} of Discord.py')
        log.info(f'Logging in as: {self.bot.user.name} V.{__version__} - {self.bot.user.id}')
        log.info(f'Version: {discord.__version__} of Discord.py')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """The event triggered when an error is raised while invoking a command"""
        original = error
        error = getattr(error, 'original', error)

        ignored = (commands.CommandNotFound, commands.UserInputError)
        if isinstance(error, ignored):
            return

        if isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
            return await ctx.send_help(ctx.command)
        elif isinstance(error, commands.CommandOnCooldown):
            title = 'Command is on cooldown'
        elif isinstance(error, commands.NotOwner):
            title = "You aren't the owner of the bot"
        else:
            title = 'Unspecified error'
        embed = discord.Embed(title=f':warning: **{title}**',
                              description=f'```py\n{format_exec(original)}```',
                              color=discord.Colour.red())
        await ctx.send(embed=embed)
        raise original


def setup(bot):
    bot.add_cog(Help(bot))
