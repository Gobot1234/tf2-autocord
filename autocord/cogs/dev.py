# -*- coding: utf-8 -*-

import asyncio
import importlib
from contextlib import redirect_stdout
from io import StringIO
from platform import python_version
from textwrap import indent
from time import perf_counter

import discord
import typing
from discord.ext import commands

from .utils.paginator import ScrollingPaginator, TextPaginator
from .utils.formats import format_error
from .utils.converters import CodeBlock


class Development(commands.Cog):
    """These commands are for development purposes"""

    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    async def cog_check(self, ctx):
        if await ctx.bot.is_owner(ctx.author):
            return True
        return False

    @commands.command(aliases=["r"], hidden=True)
    @commands.is_owner()
    async def reload(self, ctx, *, extension=None):
        """Reload an extension
        eg. `{prefix}reload staff`"""
        await ctx.trigger_typing()
        if extension is None:
            reloaded = []
            failed = []
            for extension in self.bot.initial_extensions:
                try:
                    self.bot.reload_extension(f"cogs.{extension}")
                    self.bot.dispatch("extension_reload", extension)
                except commands.ExtensionNotLoaded:
                    try:
                        self.bot.load_extension(f"cogs.{extension}")

                    except Exception as e:
                        failed.append((extension, e))

                    else:
                        self.bot.dispatch("extension_load", extension)
                        reloaded.append(extension)
                except Exception as e:
                    self.bot.dispatch("extension_fail", extension, e)
                    failed.append((extension, e))
                else:
                    self.bot.dispatch("extension_load", extension)
                    reloaded.append(extension)
            exc = (
                f'\nFailed to load {len(failed)} cog{"s" if len(failed) > 1 else ""} '
                f'(`{"`, `".join(fail[0] for fail in failed)}`)'
                if len(failed) > 0
                else ""
            )
            entries = ["\n".join([f"{ctx.emoji.tick} `{r}`" for r in reloaded])]
            for f in failed:
                entries.append(f"{ctx.emoji.cross} `{f[0]}` - Failed\n```py\n{format_error(f[1])}```")
            reload = ScrollingPaginator(
                title=f'Reloaded `{len(reloaded)}` cog{"s" if len(reloaded) != 1 else ""} {exc}',
                entries=entries,
                per_page=1,
            )
            return await reload.start(ctx)
        try:
            self.bot.reload_extension(f"cogs.{extension}")
        except commands.ExtensionNotLoaded:
            if extension in self.bot.initial_extensions:
                try:
                    self.bot.load_extension(f"cogs.{extension}")
                    self.bot.dispatch("extension_reload", extension)

                except Exception as e:
                    self.bot.dispatch("extension_fail", extension, e)
                    result = TextPaginator(
                        title=f"**`ERROR:`** `{extension}` {ctx.emoji.cross}",
                        text=format_error(e),
                        colour=discord.Colour.red(),
                    )
                    await result.start(ctx)
                else:
                    await ctx.send(f"**`SUCCESS`** {ctx.emoji.tick} `{extension}` has been loaded")

        except Exception as e:
            self.bot.dispatch("extension_fail", extension, e)
            await ctx.send(f"**`ERROR:`** `{extension}` ```py\n{format_error(e)}```")
        else:
            await ctx.send(f"**`SUCCESS`** {ctx.emoji.tick} `{extension}` has been reloaded")

    @commands.command(name="eval", aliases=["e"], hidden=True)
    @commands.is_owner()
    async def _eval(self, ctx, *, body: CodeBlock):
        """This will evaluate your code-block if type some python code.
        Input is interpreted as newline separated statements.
        If the last statement is an expression, if the last line is returnable it will be returned.

        **Usage**
        `{prefix}eval` ```py
        await ctx.send('lol')```
        """
        async with ctx.typing():
            env = {
                "bot": self.bot,
                "ctx": ctx,
                "client": self.bot.client,
                "commands": commands,
                "discord": discord,
                "session": self.bot.session,
                "self": self,
                "_": self._last_result,
            }
            env.update(globals())
            stdout = StringIO()
            split = body.splitlines()
            previous_lines = "\n".join(split[:-1]) if split[:-1] else ""
            last_line = "".join(split[-1:])
            if not last_line.strip().startswith("return"):
                if not last_line.strip().startswith(("import", "print", "raise", "return", "pass")):
                    body = f'{previous_lines}\n{" " * (len(last_line) - len(last_line.lstrip()))}return {last_line}'
            to_compile = f'async def func():\n{indent(body, "  ")}'

            try:
                start = perf_counter()
                exec(to_compile, env)
            except Exception as e:
                end = perf_counter()
                timer = (end - start) * 1000
                await ctx.bool(False)
                result = TextPaginator(
                    title=f"{ctx.emoji.cross} {e.__class__.__name__}",
                    text=format_error(e, strip=True),
                    colour=discord.Colour.red(),
                    footer=f"Python: {python_version()} • Process took {timer:.2f} ms to run",
                    footer_icon_url=ctx.emoji.python.url,
                )
                return await result.start(ctx)
            func = env["func"]
            try:
                with redirect_stdout(stdout):
                    ret = await self.bot.loop.create_task(asyncio.wait_for(func(), timeout=60))
            except Exception as e:
                value = stdout.getvalue()
                end = perf_counter()
                timer = (end - start) * 1000

                await ctx.bool(False)
                result = TextPaginator(
                    title=f"{ctx.emoji.cross} {e.__class__.__name__}",
                    text=f"{value}\n{format_error(e, strip=True)}",
                    colour=discord.Colour.red(),
                    footer=f"Python: {python_version()} • Process took {timer:.2f} ms to run",
                    footer_icon_url=ctx.emoji.python.url,
                )
                return await result.start(ctx)
            else:
                value = stdout.getvalue()
                end = perf_counter()
                timer = (end - start) * 1000

                await ctx.bool(True)
                if isinstance(ret, discord.File):
                    await ctx.send(file=ret)
                elif isinstance(ret, discord.Embed):
                    await ctx.send(embed=ret)
                else:
                    if not isinstance(value, str):
                        # repr all non-strings
                        value = repr(value)

                    if ret is None and value:
                        result = TextPaginator(
                            title=f"{ctx.emoji.tick} Evaluation completed {ctx.author.display_name}:",
                            text=f'{str(ret).replace(self.bot.http.token, "[token omitted]")}\nType: {type(ret)}',
                            colour=discord.Colour.green(),
                            footer=f"Python: {python_version()} • Process took {timer:.2f} ms to run",
                            footer_icon_url=ctx.emoji.python.url,
                        )
                    else:
                        self._last_result = ret
                        result = TextPaginator(
                            title=f"{ctx.emoji.tick} Evaluation returned {ctx.author.display_name}:",
                            text=f'{str(ret).replace(self.bot.http.token, "[token omitted]")}\nType: {type(ret)}',
                            colour=discord.Colour.green(),
                            footer=f"Python: {python_version()} • Process took {timer:.2f} ms to run",
                            footer_icon_url=ctx.emoji.python.url,
                        )
                    await result.start(ctx)

    @commands.command(aliases=["logout"])
    @commands.is_owner()
    async def restart(self, ctx):
        """Used to restart the bot"""
        await ctx.message.add_reaction(ctx.emoji.loading)
        await ctx.send(f"**Restarting the Bot** {ctx.author.mention}")
        open("channel.txt", "w+").write(str(ctx.channel.id))
        await self.bot.close()

    @commands.group(hidden=True)
    @commands.is_owner()
    async def git(self, ctx):
        """Git commands for pushing/pulling to repos"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @git.command()
    async def push(self, ctx, add_first: typing.Optional[bool], *, commit_msg):
        """Push changes to the GitHub repo"""
        if ctx.author.id != 340869611903909888:
            return await ctx.send("Why are you running this?")
        errored = ("fatal", "error")
        embed = discord.Embed(title="GitHub Commit & Push", description="", colour=discord.Colour.blurple(),)
        message = await ctx.send(embed=embed)
        await message.add_reaction(ctx.emoji.loading)
        if add_first:
            add = await ctx.get_output("git add .")
            if any([word in add.split() for word in errored]):
                await message.add_reaction(ctx.emoji.cross)
                await message.remove_reaction(ctx.emoji.loading, self.bot.user)
                embed.description = f"{embed.description}{ctx.emoji.cross} **Add result:**```js\n{add}```\n"
                return await message.edit(embed=embed)
            else:
                add = f"```js\n{add}```" if add else ":ok_hand:"
                embed.description = f"{embed.description}{ctx.emoji.tick} **Add result:**{add}\n"
            await message.edit(embed=embed)

        commit = await ctx.get_output(f'git commit -m "{commit_msg}"')
        if any([word in commit.split() for word in errored]):
            await message.add_reaction(ctx.emoji.cross)
            await message.remove_reaction(ctx.emoji.loading, self.bot.user)
            embed.description = f"{embed.description}{ctx.emoji.cross} **Commit result:**```js\n{commit}```"
            return await message.edit(embed=embed)
        else:
            embed.description = f"{embed.description}{ctx.emoji.tick} **Commit result:**```js\n{commit}```"
        await message.edit(embed=embed)

        push = await ctx.get_output("git push")
        if any([word in push.split() for word in errored]):
            await message.add_reaction(ctx.emoji.cross)
            await message.remove_reaction(ctx.emoji.loading, self.bot.user)
            embed.description = f"{embed.description}\n{ctx.emoji.cross} **Push result:**```js\n{push}```"
            return await message.edit(embed=embed)
        else:
            await message.add_reaction(ctx.emoji.tick)
            embed.description = f"{embed.description}\n{ctx.emoji.tick} **Push result:**```js\n{push}```"

        await message.remove_reaction(ctx.emoji.loading, ctx.guild.me)
        await message.edit(embed=embed)
        await ctx.bin(message)

    @git.command()
    async def pull(self, ctx, hard: bool = False):
        """Pull any changes from the GitHub repo"""
        errored = ("fatal", "error")
        embed = discord.Embed(
            title=f'GitHub{" Hard" if hard else ""} Pull', description="", colour=discord.Colour.blurple(),
        )
        message = await ctx.send(embed=embed)
        await message.add_reaction(ctx.emoji.loading)
        if hard:
            reset = await ctx.get_output("git reset --hard HEAD")
            if any([word in reset.split() for word in errored]):
                await message.add_reaction(ctx.emoji.cross)
                await message.remove_reaction(ctx.emoji.loading, ctx.guild.me)
                embed.description = f"{embed.description}\n{ctx.emoji.cross} **Reset result:**```js\n{reset}```"
                return await message.edit(embed=embed)
            else:
                embed.description = f"{embed.description}\n{ctx.emoji.tick} **Reset result:**```js\n{reset}```"
        pull = await ctx.get_output("git pull")
        if any([word in pull.split() for word in errored]):
            await message.add_reaction(ctx.emoji.cross)
            await message.remove_reaction(ctx.emoji.loading, ctx.guild.me)
            embed.description = f"{embed.description}\n{ctx.emoji.cross} **Pull result:**```js\n{pull}```"
            return await message.edit(embed=embed)
        else:
            await ctx.bool(True)
            embed.description = f"{embed.description}\n{ctx.emoji.tick} **Pull result:**```js\n{pull}```"
        await message.remove_reaction(ctx.emoji.loading, ctx.guild.me)
        await message.edit(embed=embed)
        await ctx.bin(message)

    @commands.command(aliases=["ru"], hidden=True)
    @commands.is_owner()
    async def reloadutil(self, ctx, module_name: str):
        """Reload a Utils module"""
        try:
            module = importlib.import_module(f".utils.{module_name}")
            importlib.reload(module)
        except ModuleNotFoundError:
            return await ctx.send(f"I couldn't find `.utils.{module_name}`.")
        except Exception as e:
            await ctx.send(f"```py\n{format_error(e)}```")
        else:
            await ctx.send(f"Reloaded `.utils.{module_name}`")


def setup(bot):
    bot.add_cog(Development(bot))
