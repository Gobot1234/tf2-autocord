# -*- coding: utf-8 -*-
from typing import List

import discord
import steam
from discord.ext import menus, commands


class Sourcer(menus.PageSource):
    def __init__(self, entries: List[str]):
        self._entries = entries

    async def get_page(self, page_number: int) -> str:
        return self._entries[page_number]

    async def format_page(self, menu: "ScrollingPaginator", page: str):
        embed = discord.Embed(title=menu.title, description=menu.joiner.join(page), colour=menu.colour)
        if menu.author and menu.author_icon_url:
            embed.set_author(name=menu.author, icon_url=menu.author_icon_url)
        elif menu.author:
            embed.set_author(name=menu.author)
        if menu.footer and menu.footer_icon_url:
            embed.set_footer(text=menu.footer, icon_url=menu.footer_icon_url)
        elif menu.footer:
            embed.set_footer(text=menu.footer)
        if menu.thumbnail:
            embed.set_thumbnail(url=menu.thumbnail)
        if menu.file:
            embed.set_image(url=f'attachment://{menu.file.filename}')
        return embed


class ScrollingPaginatorBase(menus.MenuPages):
    """The base for all "scrolling" paginators"""
    def __init__(self, *, entries: List[str], timeout=90):
        source = Sourcer(entries)
        super().__init__(source, timeout=timeout)
        self.entries = entries

    @menus.button('ℹ')
    async def show_info(self, payload):
        """Shows this message"""
        embed = discord.Embed(title='Help with this message')
        docs = [(button.emoji, button.action.__doc__) for button in self.buttons.values()]
        docs = '\n'.join(f'{button} - {doc}' for (button, doc) in docs)
        embed.description = f'What do the buttons do?:\n{docs}'
        return await self.message.edit(embed=embed)


class ScrollingPaginator(ScrollingPaginatorBase):
    """For paginating text"""
    def __init__(self, *, title: str, entries: list, per_page: int = 10,
                 author: str = None, author_icon_url: str = None,
                 footer: str = None, footer_icon_url: str = None,
                 joiner: str = '\n', timeout: int = 90,
                 thumbnail: str = None, colour: discord.Colour = discord.Colour.blurple(),
                 file: discord.File = None):

        super().__init__(entries=entries, timeout=timeout)
        self.title = title
        self.entries = entries
        self.per_page = per_page
        self.joiner = joiner
        self.author = author
        self.author_icon_url = author_icon_url
        self.footer = footer
        self.footer_icon_url = footer_icon_url
        self.thumbnail = thumbnail
        self.colour = colour
        self.file = file

        self.entries = steam.utils.chunk(entries, per_page)
        self.page = 0

    async def send_initial_message(self, ctx, channel):
        page = await self._source.get_page(0)
        if self.file is not None:
            return await ctx.send(embed=page, file=self.file)
        else:
            return await ctx.send(embed=page)


class TextSourcer(Sourcer):
    async def format_page(self, menu: "TextPaginator", page: str):
        embed = discord.Embed(title=menu.title, description=menu.pages[page], colour=menu.colour)
        if menu.author and menu.author_icon_url:
            embed.set_author(name=menu.author, icon_url=menu.author_icon_url)
        elif menu.author:
            embed.set_author(name=menu.author)
        if menu.footer and menu.footer_icon_url:
            embed.set_footer(text=menu.footer, icon_url=menu.footer_icon_url)
        elif menu.footer:
            embed.set_footer(text=menu.footer)
        if menu.thumbnail:
            embed.set_thumbnail(url=menu.thumbnail)
        return embed


class TextPaginator(ScrollingPaginator):
    """For paginating code blocks in an embed"""
    def __init__(self, *, text: str, title: str, python: bool = True, **kwargs):
        paginator = commands.Paginator(
            prefix=f'{kwargs.get("prefix", "```")}py' if python else kwargs.get("prefix", "```"),
            suffix=kwargs.get('suffix', '```'))
        for line in text.splitlines():
            paginator.add_line(line)
        entries = [page for page in paginator.pages]
        super().__init__(title=title, entries=entries, per_page=1985, **kwargs)

    @menus.button('⏹')
    async def stop_pages(self, payload):
        """Deletes this message"""
        return await self.message.delete()
