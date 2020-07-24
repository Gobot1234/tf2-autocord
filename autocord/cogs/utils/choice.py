# -*- coding: utf-8 -*-

from typing import Union

import discord
from discord.ext import commands

from .formats import human_join


async def wait_for_bool(ctx: commands.Context) -> bool:
    def check(message: discord.Message):
        return message.author == ctx.author

    while 1:
        choice = await ctx.bot.wait_for('message', check=check)
        choice = choice.content.lower()

        if choice in ('yes', 'y', 'ye', 'yea', 'yeah', 'true', 't',  'on', 'enable', '1'):
            return True
        elif choice in ('no', 'n', 'nop', 'nope', 'false', 'f', 'off', 'disable', '0'):
            return False
        else:
            await ctx.send(f'"{choice}" is not a recognised boolean option. Please try again')


async def wait_for_any(ctx: commands.Context, lower=True) -> str:
    def check(message: discord.Message):
        return message.author == ctx.author

    choice = await ctx.bot.wait_for('message', check=check)
    return choice.content.lower() if lower else choice.content


async def wait_for_options(ctx: commands.Context, options: Union[tuple, list, str]) -> str:
    def check(message: discord.Message):
        return message.author == ctx.author

    while 1:
        choice = await ctx.bot.wait_for('message', check=check)
        choice = choice.content.lower()

        if choice in options:
            return choice
        else:
            await ctx.send(f'"{choice}" is not a recognised option. '
                           f'Please try again with any of {human_join(options, delimiter="/", final="or")}')


async def wait_for_digit(ctx: commands.Context) -> str:
    def check(message: discord.Message):
        return message.author == ctx.author

    while 1:
        digit = await ctx.bot.wait_for('message', check=check)
        digit = digit.content.lower()

        if digit.isdigit():
            return digit
        else:
            await ctx.send(f'"{digit}" is not a digit.')


async def wait_for_owners(ctx: commands.Context) -> bool:
    def check(message: discord.Message):
        return message.author.id in ctx.bot.owner_ids

    while 1:
        choice = await ctx.bot.wait_for('message', check=check)
        choice = choice.content.lower()

        if choice in ('yes', 'y', 'ye', 'yea', 'yeah', 'true', 't', 'on', 'enable', '1'):
            return True
        elif choice in ('no', 'n', 'nop', 'nope', 'false', 'f', 'off', 'disable', '0'):
            return False
        else:
            await ctx.send(f'"{choice}" is not a recognised boolean option. Please try again')
