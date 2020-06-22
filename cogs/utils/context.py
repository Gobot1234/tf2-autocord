# -*- coding: utf-8 -*-

import asyncio
from typing import Callable, Awaitable

import aiohttp
from subprocess import getoutput

from discord import PartialEmoji, HTTPException, Message
from discord.ext import commands


async def json_or_text(response):
    try:
        return await response.json()
    except aiohttp.ContentTypeError:
        return await response.text(encoding='utf-8')


class Contexter(commands.Context):
    def __init__(self, **attrs):
        super().__init__(**attrs)
        self.steam_bots = self.bot.client.steam_bots

    async def get_output(self, command: str):
        return await self.bot.loop.run_in_executor(None, getoutput, command)

    async def run_async(self, func: Callable[..., Awaitable], *args):
        return await self.bot.loop.run_in_executor(None, func, *args)

    async def bool(self, value: bool):
        try:
            await self.message.add_reaction(self.emoji.tick if value else self.emoji.cross)
        except HTTPException:
            pass

    async def bin(self, message: Message, *, timeout: float = 90):
        def check(reaction, user):
            return user == self.author and str(reaction.emoji) == '🗑️'
        await message.add_reaction('🗑️')
        try:
            _, _ = await self.bot.wait_for('reaction_add', timeout=timeout, check=check)
        except asyncio.TimeoutError:
            try:
                await message.clear_reactions()
            except HTTPException:
                pass
        else:
            await message.delete()

    async def request(self, method, url, **kwargs):
        for tries in range(5):
            async with self.bot.session.request(method, url, **kwargs) as r:
                data = await json_or_text(r)

                if 300 > r.status >= 200:
                    return data

                if r.status == 429:
                    try:
                        await asyncio.sleep(r.headers('X-Retry-After'))
                    except KeyError:
                        await asyncio.sleep(2 ** tries)
                    continue

                if r.status in {500, 502}:
                    await asyncio.sleep(1 + tries * 3)
                    continue

            return None

    class emoji:  # this is so we can go ctx.emoji.tick
        tick = PartialEmoji(name='tick', id=688829439659737095)
        cross = PartialEmoji(name='cross', id=688829441123942416)

        discord = PartialEmoji(name='discord', id=626486432793493540)
        dpy = PartialEmoji(name='dpy', id=622794044547792926)
        steam = PartialEmoji(name='steam', id=622621553800249364)
        automatic = PartialEmoji(name='tf2automatic', id=624658370447671297)
        autocord = PartialEmoji(name='tf2autocord', id=624658299224326148)
        python = PartialEmoji(name='python', id=622621989474926622)

        loading = PartialEmoji(name='loading', id=661210169870516225, animated=True)

        cpu = PartialEmoji(name='cpu', id=622621524418887680)
        ram = PartialEmoji(name='ram', id=689212498544820301)