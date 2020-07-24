from typing import TYPE_CHECKING, Optional

import steam
from discord.ext import commands
from steam.ext import commands as steam_commands

if TYPE_CHECKING:
    from .context import Contexter


class SteamCTX:
    @classmethod
    def from_discord_context(cls, context: Contexter):
        self = cls()
        self.bot = context.bot.client
        return self


class SteamBot(commands.Converter):
    async def convert(self, ctx, argument) -> Optional[steam.User]:
        old_ctx = ctx
        ctx = SteamCTX.from_discord_context(ctx)
        user = await steam_commands.UserConverter().convert(ctx, argument)
        return user if user in old_ctx.steam_bots else None


class CodeBlock(commands.Converter):
    async def convert(self, ctx, argument) -> str:
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if argument.startswith('```') and argument.endswith('```'):
            return '\n'.join(argument.split('\n')[1:-1])

        # remove `foo`
        return argument.strip('` \n')
