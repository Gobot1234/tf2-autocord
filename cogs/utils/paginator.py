# -*- coding: utf-8 -*-

import discord
from discord.ext import menus, commands


class ScrollingPaginatorBase(menus.Menu):
    """The base for all scrolling paginators"""
    def __init__(self, *, entries, timeout=90):
        super().__init__(timeout=timeout)
        self.entries = entries

    def check(self):
        return len(self.entries) == 1

    async def send_initial_message(self, ctx, channel):
        return await ctx.send(embed=await self.invoke())

    @menus.button('⏮', skip_if=check)
    async def do_first(self, payload):
        """Goes to the first page"""
        return await self.first_page()

    @menus.button('◀', skip_if=check)
    async def do_previous(self, payload):
        """Goes to the previous page"""
        return await self.previous_page()

    @menus.button('▶', skip_if=check)
    async def do_next(self, payload):
        """Goes to the next page"""
        return await self.next_page()

    @menus.button('⏭', skip_if=check)
    async def do_final(self, payload):
        """Goes to the last page"""
        return await self.final_page()

    @menus.button('⏹')
    async def _stop(self, payload):
        """Stops processing of reactions"""
        await self.stop()
        await self.message.delete

    @menus.button('ℹ', skip_if=check)
    async def show_info(self, payload):
        """Shows this message"""
        embed = discord.Embed(title='Help with this message')
        docs = [(button.emoji, button.action.__doc__) for button in self.buttons.values()]
        docs = '\n'.join([f'{button} - {doc}' for (button, doc) in docs])
        embed.description = f'What do the buttons do?:\n{docs}'
        return await self.message.edit(embed=embed)

    async def next_page(self):
        raise NotImplemented

    async def previous_page(self):
        raise NotImplemented

    async def first_page(self):
        raise NotImplemented

    async def final_page(self):
        raise NotImplemented

    async def invoke(self, *args, **kwargs):
        raise NotImplemented


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

        self.entries = list(self.chunk(entries))
        self.page = 0

    def check(self):
        return len(self.entries) == 1

    def chunk(self, entries):
        for i in range(0, len(entries), self.per_page):
            yield self.entries[i:i + self.per_page]

    async def send_initial_message(self, ctx, channel):
        page = self.entries[0]
        if self.file is not None:
            return await ctx.send(embed=await self.invoke(page), file=self.file)
        else:
            return await ctx.send(embed=await self.invoke(page))

    async def next_page(self):
        self.page += 1
        try:
            page = self.entries[self.page]
        except IndexError:
            return
        else:
            embed = await self.invoke(page)
            await self.message.edit(embed=embed)

    async def previous_page(self):
        self.page -= 1
        try:
            page = self.entries[self.page]
        except IndexError:
            return
        else:
            embed = await self.invoke(page)
            await self.message.edit(embed=embed)

    async def first_page(self):
        self.page = 0
        page = self.entries[self.page]
        embed = await self.invoke(page)
        await self.message.edit(embed=embed)

    async def final_page(self):
        self.page = len(self.entries) - 1
        page = self.entries[self.page]
        embed = await self.invoke(page)
        await self.message.edit(embed=embed)

    async def invoke(self, page):
        embed = discord.Embed(title=self.title, description=self.joiner.join(page), colour=self.colour)
        if self.author and self.author_icon_url:
            embed.set_author(name=self.author, icon_url=self.author_icon_url)
        elif self.author:
            embed.set_author(name=self.author)
        if self.footer and self.footer_icon_url:
            embed.set_footer(text=self.footer, icon_url=self.footer_icon_url)
        elif self.footer:
            embed.set_footer(text=self.footer)
        if self.thumbnail:
            embed.set_thumbnail(url=self.thumbnail)
        if self.file:
            embed.set_image(url=f'attachment://{self.file.filename}')
        return embed


class TextPaginator(ScrollingPaginator):
    """For paginating code blocks in an embed"""
    def __init__(self, *, text, title, python=True, **kwargs):
        super().__init__(title=title, entries=[text], per_page=1985, **kwargs)
        self.paginator = commands.Paginator(
            prefix=f'{kwargs.get("prefix", "```")}py' if python else kwargs.get("prefix", "```"),
            suffix=kwargs.get('suffix', '```'))
        for line in text.splitlines():
            self.paginator.add_line(line)
        self.pages = [page for page in self.paginator.pages]

    async def send_initial_message(self, ctx, channel):
        return await ctx.send(embed=await self.invoke(0))

    @menus.button('⏹')
    async def _stop(self, payload):
        """Deletes this message"""
        return await self.message.delete()

    async def invoke(self, page):
        embed = discord.Embed(title=self.title, description=self.pages[page], colour=self.colour)
        if self.author and self.author_icon_url:
            embed.set_author(name=self.author, icon_url=self.author_icon_url)
        elif self.author:
            embed.set_author(name=self.author)
        if self.footer and self.footer_icon_url:
            embed.set_footer(text=self.footer, icon_url=self.footer_icon_url)
        elif self.footer:
            embed.set_footer(text=self.footer)
        if self.thumbnail:
            embed.set_thumbnail(url=self.thumbnail)
        return embed
