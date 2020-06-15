from typing import Optional

import steam
from discord.ext import commands


class SteamBot(commands.Converter):
    async def convert(self, ctx, argument) -> Optional[steam.User]:
        if argument.isdigit():
            user = ctx.bot.client.get_user(argument)
            if user in ctx.steam_bots:
                return user
        return None


class CodeBlock(commands.Converter):
    async def convert(self, ctx, argument) -> str:
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if argument.startswith('```') and argument.endswith('```'):
            return '\n'.join(argument.split('\n')[1:-1])

        # remove `foo`
        return argument.strip('` \n')
