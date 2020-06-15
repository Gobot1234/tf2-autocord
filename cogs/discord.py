# -*- coding: utf-8 -*-

import asyncio
import json
import math
import re
import os
import traceback
from datetime import datetime
from io import BytesIO
from pathlib import Path
from platform import python_version
from subprocess import getoutput
from time import perf_counter
from typing import Optional

import discord
import humanize
import psutil
import matplotlib.pyplot as plt
import steam
from discord.ext import commands, tasks

from config import preferences
from . import __version__
from .utils.choice import wait_for_owners
from .utils.paginator import ScrollingPaginator
from .utils.converters import SteamBot


class Discord(commands.Cog):
    """Commands that are mostly help commands but more useful"""

    def __init__(self, bot):
        self.bot = bot
        self.profit_graphing.start()
        self.github_update.start()

    def cog_unload(self):
        self.profit_graphing.cancel()
        self.github_update.cancel()

    @tasks.loop(seconds=20)
    async def profit_graphing(self):
        """A task that at 23:59 will get your profit
        It will convert all your values to keys"""
        self.bot.current_time = datetime.now().strftime("%d-%m-%Y %H:%M")
        if self.bot.current_time.split()[1] == '23:59':
            response = await self.bot.request('GET', 'https://api.prices.tf/items/5021;6?src=bptf')
            key_value = response["sell"]["metal"]

            tod_profit = re.search(r'(made (.*?) today)', self.bot.graphplots).group(1)[5:-6]
            tot_profit = re.search(r'(today, (.*?) in)', self.bot.graphplots).group(1)[7:-3]
            try:
                predicted_profit = re.search(r'(\((.*?) more)', self.bot.graphplots).group(1)[1:-5]
            except ValueError:
                predicted_profit = 0

            fixed = []
            for to_fix in [tod_profit, tot_profit, predicted_profit]:
                if to_fix == 0:
                    total = 0
                elif ', ' in to_fix:
                    to_fix = to_fix.split(', ')
                    keys = int(to_fix[0][:-5]) if 'keys' in to_fix[0] else int(to_fix[0][:-4])
                    multiplier = -1 if keys < 0 else 1
                    ref = multiplier * float(to_fix[1][:-4])
                    ref_keys = round(ref / key_value, 2)
                    total = keys + ref_keys
                else:
                    ref = float(tod_profit[:-4])
                    total = round(ref / key_value, 2)
                fixed.append(total)

            tod_profit, tot_profit, pred_profit = fixed
            graphdata = [tod_profit, tot_profit, pred_profit, self.bot.trades]
            tempprofit = {self.bot.current_time.split()[0]: graphdata}
            data = json.load(open('Login_details\\profit_graphing.json'))
            data.update(tempprofit)
            json.dump(data, open('Login_details\\profit_graphing.json'), indent=4)
            await asyncio.sleep(120)

    @tasks.loop(hours=24)
    async def github_update(self):
        """A tasks loop to check if there has been an update to the GitHub repo"""
        result = await self.bot.loop.run_in_executor(None, getoutput, f'git checkout {os.getcwd()}')
        if 'Your branch is up to date with' in result:
            return
        elif 'not a git repository' in result:
            embed = discord.Embed(
                title="This version wasn't cloned from GitHub, which I advise as it allows for automatic updates",
                description='Installation is simple type `git clone https://github.com/Gobot1234/tf2-autocord.git` '
                            'into your command prompt of choice, although you need to have git',
                color=discord.Colour.blurple())
            for owner in self.bot.owners:
                await owner.send(embed=embed)
        else:
            for owner in self.bot.owners:
                message = await owner.send('Fetching info on the latest GitHub changes...')
                ctx = self.bot.get_context(message)
                await ctx.trigger_typing()
                resp = await ctx.request('GET', 'https://api.github.com/repos/Gobot1234/tf2-autocord/commits')
                version = resp[0]['commit']['message']

                resp = await ctx.request('GET', resp[0]['comments_url'])
                comment = resp[0] or "I didn't provide any update info ¯\\_(ツ)_/¯"

                embed = discord.Embed(
                    title=f'Version {version} has been pushed to the GitHub repo. Do you want to install it?',
                    description=f'__Update info is as follows:__\n```{comment}```', color=discord.Colour.blurple())
                await message.edit(content=None, embed=embed)

            if await wait_for_owners(ctx):
                for owner in self.bot.owners:
                    await owner.send('Updating from the latest GitHub push')
                command = self.bot.get_command('git pull')
                await ctx.invoke(command, True)
            else:
                for owner in self.bot.owners:
                    await owner.send(f"I won't update yet")

    @profit_graphing.before_loop
    async def before_graphing(self):
        await self.bot.wait_until_ready()

    @github_update.before_loop
    async def before_github(self):
        await self.bot.wait_until_ready()

    @profit_graphing.after_loop
    async def after_graphing(self):
        if self.profit_graphing.failed():
            traceback.print_exc()

    @github_update.after_loop
    async def after_github(self):
        if self.github_update.failed():
            traceback.print_exc()

    @staticmethod
    def gen_graph(points: int = None):
        data = json.load(open('Login_details/profit_graphing.json', 'r'))
        if points is None:
            points = len(data)
        ignored = len(data) - points
        date_values = [date for date in data.keys()[ignored:]]  # generate x values
        tot_values = [float(value[0]) for value in data.values()[ignored:]]  # generate the y values
        tod_values = [float(value[1]) for value in data.values()[ignored:]]
        pre_values = [float(value[2]) for value in data.values()[ignored:]]

        # plot the number in the list and set the line thickness.
        plt.setp(plt.plot(date_values, tod_values, linewidth=3), color='blue')
        plt.setp(plt.plot(date_values, tot_values, linewidth=3), color='orange')
        plt.setp(plt.plot(date_values, pre_values, linewidth=3), color='green')

        plt.title(f'A graph to show your bot\'s profit over the last {points} days', fontsize=16)
        plt.xlabel('Date', fontsize=10)
        plt.ylabel('Keys', fontsize=10)
        plt.tick_params(axis='x', labelsize=8, rotation=90)
        plt.gca().legend(('Days profit', 'Total profit', 'Projected profit'))
        plt.tight_layout(h_pad=20, w_pad=20)
        buf = BytesIO()
        plt.savefig(buf, format='png', transparent=True)
        buf.seek(0)
        plt.close()
        return discord.File(buf, filename='graph.png')

    @commands.command()
    @commands.is_owner()
    async def last(self, ctx, bot: Optional[SteamBot] = None, days: int = None):
        """Used to get the last x days profit
        eg. `{prefix}last 7` (days has to be an integer)"""
        async with ctx.typing():
            if bot is None:
                bots_data = []
                for file in Path('config'):
                    if file.name.startswith('profit_graphing.json'):
                        bots_data.append(json.load(open(f'config/{file.name}')))
            else:
                bots_data = [json.load(open(f'config/profit_graphing {bot.id64}.json'))]
            for data in bots_data:
                if days is None or days > len(data):
                    days = len(data)
                ignored = len(data) - days
                file = await ctx.run_async(self.gen_graph, days)
                entries = [f'__**{date}**__ - Days profit **{day}** keys. Total profit '
                           f'**{total}** keys. Predicted profit **{predicted}** keys. '
                           f'Total trades **{trades}**' for date, (day, total, predicted, trades) in
                           reversed(list(data.items())[ignored:])]
                last = ScrollingPaginator(title=f'Last {days} days profit', entries=entries, file=file)
                await last.start(ctx)

    @commands.command()
    @commands.is_owner()
    async def graph(self, ctx, bot: Optional[SteamBot] = None, points: int = 0):
        """Used to generate a graph of all of your profit whilst using the bot"""
        async with ctx.typing():
            if bot is None:
                bots_data = []
                for file in Path('config').glob('**'):
                    if file.name.startswith('profit_graphing.json'):
                        bots_data.append(len(json.load(open(f'config/{file.name}'))))
            else:
                bots_data = [len(json.load(open(f'config/profit_graphing {bot.id64}.json')))]
            for len_points in bots_data:
                if points == 0 or points > len_points:
                    points = len_points
                if points <= 1:
                    points = 3
                file = await ctx.run_async(self.gen_graph, points)
                embed = discord.Embed(title=f'Last {points} days profit', color=self.bot.color)
                embed.set_image(url='attachment://graph.png')
                await ctx.send(embed=embed, file=file)

    @commands.command(aliases=['about', 'stats', 'status'])
    async def info(self, ctx):
        """Get some interesting info about the bot"""
        ram = psutil.virtual_memory()
        checkout = await ctx.get_output(f'git checkout {os.getcwd()}')
        emoji = ctx.emoji.tick if 'Your branch is up to date with' in checkout else ctx.emoji.cross

        embed = discord.Embed(
            title="**tf2-autocord:** - System information",
            description=f'Commands loaded & Cogs loaded: `{len(self.bot.commands)}` commands loaded, '
                        f'`{len(self.bot.cogs)}` cogs loaded :gear:',
            colour=discord.Colour.blurple())
        embed.add_field(name=f'{ctx.emoji.ram} RAM Usage',
                        value=f'Using `{humanize.naturalsize(ram[3])}`/`{humanize.naturalsize(ram[0])}` '
                              f'`{round(ram[3] / ram[0] * 100, 2)}`%')
        embed.add_field(name=f'{ctx.emoji.cpu} CPU Usage',
                        value=f'`{psutil.cpu_percent()}`% used')
        embed.add_field(name=f'{self.bot.user.name} has been online for:',
                        value=self.bot.uptime)
        embed.add_field(name=f'{ctx.emoji.autocord} tf2-autocord Version',
                        value=f'Version: `{__version__}`.\nUp to date: {emoji}')
        embed.add_field(name=f'{ctx.emoji.automatic} About the bot',
                        value='It was coded in Python to help you manage your tf2automatic bot')

        embed.add_field(name='\u200b', value='\u200b', inline=False)

        embed.add_field(name=f'{ctx.emoji.dpy} Discord.py Version',
                        value=f'`{discord.__version__}` works with versions 1.1+ of discord.py')
        embed.add_field(name=f'{ctx.emoji.python} Python Version',
                        value=f'`{python_version()}` works with versions 3.6+ (uses f-strings)')
        embed.add_field(name=f'{ctx.emoji.steam} Steam Version',
                        value=f'`{steam.__version__}` works with versions that work')
        dev = self.bot.get_user(340869611903909888)
        embed.set_footer(text=f"If you need any help contact the creator of this code @{dev}", icon_url=dev.avatar_url)
        await ctx.send(embed=embed)

    @commands.command()
    async def uptime(self, ctx):
        """See how long the bot has been online for"""
        await ctx.send(f'{self.bot.user.mention} has been online for {self.bot.uptime}')

    @commands.command()
    @commands.is_owner()
    @commands.cooldown(rate=1, per=7200, type=commands.BucketType.user)
    async def suggest(self, ctx, *, suggestion):
        """Suggest a feature to <@340869611903909888>
         eg. `{prefix}suggest update the repo` your bot needs to be in the
         [tf2autocord server](discord.gg/S3eVmxD) for this to work"""
        embed = discord.Embed(color=0x2e3bad, description=suggestion)
        embed.set_author(name=f'Message from {ctx.author}')
        try:
            await self.bot.get_user(340869611903909888).send(embed=embed)
        except discord.HTTPException:
            await ctx.send(f"I could not deliver your message. ¯\\_(ツ)_/¯, "
                           f"probably as your bot isn't in the server send {self.bot.user.id} to <@340869611903909888>")
        else:
            await ctx.send('I have delivered your message to <@340869611903909888> (I may be in contact), '
                           'this command is limited to working every 2 hours so you can\'t spam me')

    @commands.command()
    async def ping(self, ctx):
        """Check if your bot is online on both Steam and Discord"""
        embed = discord.Embed(color=discord.Colour.blurple()).set_author(name='Pong!')
        start = perf_counter()
        m = await ctx.send(embed=embed)
        end = perf_counter()
        message_duration = (end - start) * 1000

        message = f'{ctx.emoji.tick} You are logged into Steam in as: `{self.bot.client.user}`' \
            if self.bot.client else f"{ctx.emoji.cross} You aren't logged into Steam"

        embed = discord.Embed(description=f'{self.bot.user.mention} is online.\n{message}',
                              colour=discord.Colour.blurple())
        embed.description = f'{self.bot.user.mention} is online. {message}'
        embed.set_author(name='Pong!', icon_url=self.bot.user.avatar_url)
        embed.add_field(name=f':heartbeat: Discord Heartbeat latency is:',
                        value=f'`{self.bot.latency * 1000:.2f}` ms.')
        embed.add_field(name=f':heartbeat: Steam Heartbeat latency is:',
                        value=f'`{self.bot.client.latency * 1000:.2f}` ms.')
        embed.add_field(name=f'{ctx.emoji.text} Message latency is:',
                        value=f'`{message_duration:.2f}` ms.')
        embed.set_author(name='Pong!', icon_url=self.bot.user.avatar_url)
        await m.edit(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def profit(self, ctx, bot: SteamBot = None):
        async with ctx.typing():
            if bot is None:
                bots_data = []
                for location in preferences.bots_steam_ids.values():
                    bots_data.append(json.load(open(f'{location}/polldata.json')))
            else:
                bots_data = [json.load(open(f'{preferences.bots_steam_ids[bot.id64]}/polldata.json'))]

            for polldata in bots_data:
                total_profit = 0
                todays_profit = 0
                predicted_profit = 0
                timestamps = []
                midnight = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

                for trade in polldata['offerData'].values():
                    if trade.get('action', 'ADMIN') != 'ADMIN' and trade.get('isAccepted'):
                        try:
                            key_price = trade['value']['rate']
                            for item in trade['prices'].values():
                                bought_for = round(item['buy']['metal'] +
                                                   item['buy']['keys'] * key_price, 4)

                                sold_for = round(trade['value']['their']['metal'] +
                                                 trade['value']['their']['keys'] * key_price, 4)

                                final = math.floor((sold_for - bought_for) * 100) / 100
                                total_profit += final
                                if trade['finishTimestamp'] / 1000 >= midnight.timestamp():
                                    todays_profit += final
                                timestamps.append(trade['finishTimestamp'])

                                sell_for = round(item['sell']['metal'] +
                                                 item['sell']['keys'] * key_price, 4)
                                predicted_profit += math.floor((sell_for - bought_for) * 100) / 100

                        except KeyError:
                            pass

                resp = await ctx.request('GET', 'https://api.prices.tf/items/5021;6?src=bptf')
                key_price = resp['buy']['metal']
                timedelta = humanize.naturaldelta(datetime.utcnow() - datetime.utcfromtimestamp(min(timestamps) / 1000))

                await ctx.send(
                    f"You've made {round(todays_profit, 2)} ref today. {round(total_profit / key_price, 2)} keys in "
                    f"total over the last {timedelta}. ({round(predicted_profit / key_price, 2)} keys more if all "
                    f"items sold at current price)")


def setup(bot):
    bot.add_cog(Discord(bot))
