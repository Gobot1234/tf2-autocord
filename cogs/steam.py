# -*- coding: utf-8 -*-

import asyncio
import json

import discord
from discord.ext import commands

from .utils.formats import human_join
from .utils.choice import wait_for_bool, wait_for_options, wait_for_any, wait_for_digit


class Steam(commands.Cog):
    """Commands that are mainly owner restricted and only work if you are logged in to your Steam account"""

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def update_classifieds(ctx, items):
        is_list = isinstance(items, list)
        this = 'these' if is_list else 'this'
        command = 'commands' if is_list else 'command'
        pretty_name = human_join(items, delimiter='`, `', final='` and `')
        await ctx.send(f'Do you want to send {this} `{pretty_name}` {command} to the bot?')
        if await wait_for_bool(ctx):
            async with ctx.typing():
                if is_list:
                    for item in items:
                        await ctx.steam_bot.send(item)
                        await asyncio.sleep(3)
                else:
                    await ctx.steam_bot.send(items)
            await ctx.send(f'Sent{f" {len(items)}" if is_list else ""} {command} to the bot')
        else:
            await ctx.send("The command hasn't been sent")

    @commands.group(invoke_without_command=True)
    @commands.is_owner()
    async def add(self, ctx):
        """Add is used to add items to your bot's classifieds.
        NOTE: do NOT use an "=" between name and the item.

        **Examples**
        - One item.
        `{prefix}add name The Team Captain`
        - It also allows the chaining of commands.
        `{prefix}add names This&intent=sell, That, The other&quality=Strange`"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @add.command(name='name')
    async def a_name(self, ctx, *, item):
        """Handles singular classified additions"""
        await self.update_classifieds(ctx, f'!add name={item}')

    @add.command(name='names')
    async def a_names(self, ctx, *, items):
        """Handles multiple classified additions"""
        items = [f'!add name={item.strip()}' for item in items.split(',')]
        await self.update_classifieds(ctx, items)

    @commands.group(invoke_without_command=True)
    @commands.is_owner()
    async def update(self, ctx):
        """Update is used to update items on your bot's classifieds.
        NOTE: do NOT use an "=" between name and the item.

        **Examples**
        - One item.
        `{prefix}update name The Team Captain`
        - It also allows the chaining of commands.
        `{prefix}update names This&intent=sell, That, The other&quality=Strange`"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @update.command(name='name')
    async def u_name(self, ctx, *, item):
        """Handles singular updates"""
        await self.update_classifieds(ctx, f'!update name={item}')

    @update.command(name='names')
    async def u_names(self, ctx, *, items):
        """Handles multiple updates"""
        items = [f'!update name={item.strip()}' for item in items.split(',')]
        await self.update_classifieds(ctx, items)

    @commands.group(invoke_without_command=True)
    @commands.is_owner()
    async def remove(self, ctx):
        """Remove is used to remove items from your bot's classifieds.
        NOTE: do NOT use an "=" between name and the item.

        **Examples**
        - One item.
        `{prefix}remove name The Team Captain`
        - It also allows the chaining of commands.
        `{prefix}remove names This&intent=sell, That, The other&quality=Strange`"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @remove.command(name='item')
    async def r_item(self, ctx, *, item):
        """Handles singular removals"""
        await self.update_classifieds(ctx, f'!remove name={item}')

    @remove.command(name='items')
    async def r_items(self, ctx, *, items):
        """Handles multiple removals"""
        items = [f'!add name={item.strip()}' for item in items.split(',')]
        await self.update_classifieds(ctx, items)

    @commands.command()
    @commands.is_owner()
    async def acknowledged(self, ctx):
        """Used to acknowledge a user message
        This is so user messages don't get lost in the channel history"""
        self.bot.client.user_message.stop()
        self.bot.client.first = True
        for message in self.bot.messages:
            try:
                await message.unpin()
            except discord.HTTPException:
                pass
        await ctx.send("Acknowledged the user's message")

    @commands.command()
    @commands.is_owner()
    async def send(self, ctx, *, message):
        """Send is used to send a message to the bot
        eg. `{prefix}send {prefix}message 76561198248053954 Get on steam`"""
        await ctx.trigger_typing()
        await ctx.steam_bot.send(message)
        await ctx.send(f'Sent `{message}` to the bot')

    @commands.command(aliases=['bp'])
    async def backpack(self, ctx):
        """Get a link to your inventory and your bot's"""
        bptf = 'https://backpack.tf'
        embed = discord.Embed(
            title='Backpack.tf', url=bptf,
            description=f"[Your backpack]({bptf}/profiles/{self.bot.client.user.id64})\n"
                        f"[Your bot's backpack]({bptf}/profiles/{ctx.steam_bot.id64})",
            color=0x58788F)
        embed.set_thumbnail(url=f'{bptf}/images/tf-icon.png')
        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def cashout(self, ctx):
        """Want to cash-out all your listings?
        Be warned this command is quite difficult to fix once you run it"""
        listings_json = json.load(open(f'{self.bot.templocation}/listings.json'))
        await ctx.send(f'Cashing out {len(listings_json)} items, this may take a while')
        for value in listings_json:
            command = f'!update sku={value["sku"]}&intent=sell'  # TODO needs to use sku
            await ctx.steam_bot.send_message(command)
            await ctx.send(command)
            await asyncio.sleep(3)
        await ctx.send('Completed the intent update')

    @commands.command(aliases=['raw_add', 'add-raw', 'raw-add'])
    @commands.is_owner()
    async def add_raw(self, ctx, *, ending=None):
        """Add lots of items, from both a .txt file or a discord message"""
        await ctx.send('Paste all the items you want to add on a new line, or attach a text file')
        message = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author)
        items = []
        if message.content:
            items.extend(message.content.splitlines())
        if message.attachments:
            file = await message.attachments[0].read()
            items.extend(file.decode().splitlines())
        else:
            return await ctx.send('Please send either a file or a message')
        for item in items:
            await self.bot.client.steam_bot.send(f'!add name={item}{ending if ending else ""}')
        await ctx.send(f'Done adding {len(items)} items')

    @commands.command()
    @commands.is_owner()
    async def scc(self, ctx):
        """SCC - Steam Command Creator is a ~~worse~~ better version of Hackerino's command generator tool"""
        ngt1, ngt2, ngt3, ngt4, ngt5, ngt6, ngt7, ngt8, ngt9 = [True for _ in range(9)]
        scclist = ['__You can change the:__\n',
                   'Price', 'Limit', 'Quality',
                   'Intent', 'Craftable', 'Australium',
                   'Killstreak', 'Effect', 'Autopricing', "\nIf you don't type want to change any type escape"]
        intents = ['Bank', 'Buy', 'Sell']
        qualities = ['Unique', 'Strange', 'Vintage', 'Genuine', 'Haunted', "Collector's"]

        await ctx.send('What do you want to do?\nUpdate, Remove or Add?')
        choice = await wait_for_options(ctx, ('update', 'u', 'add', 'a', 'remove', 'r'))
        if choice in ('update', 'u'):
            do = 'update'
        elif choice in ('add', 'a'):
            do = 'add'
        else:
            do = 'remove'
        await ctx.send(f'What item do you want to {do}?')
        item = await wait_for_any(ctx)
        command = item

        if do == 'remove':
            f'!remove name={command}'
        else:
            await ctx.send('Do you want to add prefixes to the command?')
            if await wait_for_bool(ctx):
                await ctx.send('\n'.join(scclist))
                while 1:
                    if True not in (ngt1, ngt2, ngt3, ngt4, ngt5, ngt6, ngt7, ngt8, ngt9):
                        break

                    prefix = await wait_for_any(ctx)

                    if prefix in ('price', 'p') and ngt1:
                        await ctx.send('Buy price in refined metal')
                        buy_price_ref = await wait_for_digit(ctx)
                        await ctx.send('Buy price in keys')
                        buy_price_keys = await wait_for_digit(ctx)

                        await ctx.send('Sell price in refined metal')
                        sell_price_ref = await wait_for_digit(ctx)
                        await ctx.send('Sell price in keys')
                        sell_price_keys = await wait_for_digit(ctx)

                        command = f'{command}&buy.metal={buy_price_ref}&buy.keys={buy_price_keys}' \
                                  f'&sell.metal={sell_price_ref}&sell.keys={sell_price_keys}'
                        scclist.remove('Price')
                        formatted = '\n'.join(scclist)
                        ngt1 = False
                        await ctx.send(f'Do you want to add more options to your command from the list:\n{formatted}')

                    elif prefix in ('limit', 'l') and ngt2:
                        await ctx.send('Max stock is')
                        limit = await wait_for_digit(ctx)
                        command = f'{command}&limit={limit}'
                        scclist.remove('Limit')
                        formatted = '\n'.join(scclist)
                        ngt2 = False
                        await ctx.send(f'Do you want to add more options to your command from the list:\n{formatted}')

                    elif prefix in ('quality', 'q') and ngt3:
                        await ctx.send(f'Quality (enter {human_join(qualities, delimiter="/", final="or")})')
                        quality = wait_for_options(ctx, [quality.lower() for quality in qualities])
                        if do == 'update':
                            command = f'{quality} {command}'
                        else:
                            command = f'{command}&quality={quality}'

                        scclist.remove('Quality')
                        formatted = '\n'.join(scclist)
                        ngt3 = False
                        await ctx.send(f'Do you want to add more options to your command from the list:\n{formatted}')

                    elif prefix in ('intent', 'i') and ngt4:
                        await ctx.send(f'Intent is to ({human_join(intents, final="or")}')
                        intent = await wait_for_options(ctx, [intent.lower() for intent in intents])
                        command = f'{command}&intent={intent}'

                        scclist.remove('Intent')
                        formatted = '\n'.join(scclist)
                        ngt4 = False
                        await ctx.send(f'Do you want to add more options to your command from the list:\n{formatted}')

                    elif prefix in ('craftable', 'c') and ngt5:
                        await ctx.send('Is the item craftable?')
                        if await wait_for_bool(ctx):
                            if do == 'update':
                                command = f'Craftable {command}'
                            else:
                                command = f'{command}&craftable=true'
                        else:
                            if do == 'update':
                                command = f'Non-Craftable {command}'
                            else:
                                command = f'{command}&quality=false'

                        scclist.remove('Craftable')
                        formatted = '\n'.join(scclist)
                        ngt5 = False
                        await ctx.send(f'Do you want to add more options to your command from the list:\n{formatted}')

                    elif prefix in ('australium', 'au') and ngt6:
                        await ctx.send('Is the item australium?')
                        if await wait_for_bool(ctx):
                            if do == 'update':
                                command = f'Strange Australium {command}'
                            else:
                                command = f'{command}&strange=true&australium=true'

                        scclist.remove('Australium')
                        formatted = '\n'.join(scclist)
                        ngt6 = False
                        await ctx.send(f'Do you want to add more options to your command from the list:\n{formatted}')

                    elif prefix in ('killstreak', 'k') and ngt7:
                        await ctx.send('Is the item killstreak (Killstreak (1), Specialized (2) or Professional (3))')
                        options = ('1', 'k', 'killstreak', 'basic', '2', 's', 'specialized', '3', 'p', 'professional')
                        killstreak = await wait_for_options(ctx, options)

                        if killstreak in ('1', 'k', 'killstreak', 'basic'):
                            if do == 'update':
                                command = f'Killstreak {command}'
                            else:
                                command = f'{command}&quality=1'
                        elif killstreak in ('2', 's', 'specialized'):
                            if do == 'update':
                                command = f'Specialized {command}'
                            else:
                                command = f'{command}&quality=2'
                        elif killstreak in ('3', 'p', 'professional'):
                            if do == 'update':
                                command = f'Professional {command}'
                            else:
                                command = f'{command}&quality=3'

                        scclist.remove('Killstreak')
                        formatted = '\n'.join(scclist)
                        ngt7 = False
                        await ctx.send(f'Do you want to add more options to your command from the list:\n{formatted}')

                    elif prefix in ('effect', 'e') and ngt8:  # effect suffix
                        await ctx.send('What is the unusual effect? E.g Burning Flames')
                        effect = await wait_for_any(ctx, lower=False)
                        if do == 'update':
                            command = f'{effect} {command}'
                        else:
                            command = f'{command}&effect={effect}'
                        scclist.remove('Effect')
                        formatted = '\n'.join(scclist)
                        ngt8 = False
                        await ctx.send(f'Do you want to add more options to your command from the list:\n{formatted}')

                    elif prefix in ('autoprice', 'ap') and ngt9:
                        await ctx.send('Is auto-pricing enabled?')
                        choice = await wait_for_bool(ctx)
                        command = f'{command}&autoprice={choice}'
                        scclist.remove('Autopricing')
                        formatted = '\n'.join(scclist)
                        ngt9 = False
                        await ctx.send(f'Do you want to add more options to your command from the list:\n{formatted}')

                    elif prefix in ('escape', 'esc'):
                        break

            if do == 'update':
                command = f'!update name={command}'
            elif do == 'add':
                command = f'!add name={command}'

        await ctx.send(f'Command to {do} {item} is `{command}`\n'
                       f'Do you want to send the command to the bot?\nType yes or no')

        if await wait_for_bool(ctx):
            await ctx.trigger_typing()
            await ctx.steam_bot.send(command)
            await ctx.send(':ok_hand: sent')
        else:
            await ctx.send(":thumbsdown: you didn't send the command")


def setup(bot):
    bot.add_cog(Steam(bot))
