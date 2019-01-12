from discord.ext import commands
import pytz
from datetime import datetime

from firetail.utils import make_embed
from firetail.core import checks


class EveTime:
    """This extension handles the time commands."""

    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config
        self.logger = bot.logger

    TIMEZONES = {
        'EVE Time': 'UTC',
        'SA': 'Australia/Adelaide',
        'VIC': 'Australia/Melbourne',
        'NSW': 'Australia/Sydney',
        'QLD': 'Australia/Brisbane',
        'WA': 'Australia/Perth',
        'TAS': 'Australia/Hobart',
        'Salem, MA': 'America/New_York',
    }
    @commands.command(name='time')
    @checks.spam_check()
    @checks.is_whitelist()
    async def _time(self, ctx):
        """Shows the time in a range of timezones."""
        self.logger.info('EveTime - {} requested time info.'.format(str(ctx.message.author)))
        tz_field = []
        time_field = []
        for display, zone in self.TIMEZONES.items():
            tz_field.append("**{}**".format(display))\
            eve_year = "YC" + str(datetime.now(pytz.timezone("Australia/Adelaide")).year - 1898)
            time_field.append("`" + datetime.now(pytz.timezone(zone)).strftime('%a %b %d %H:%M ') + eve_year + "`")

        embed = make_embed(guild=ctx.guild)
        embed.set_footer(icon_url=ctx.bot.user.avatar_url,
                         text="Provided Via Firetail Bot")
        embed.add_field(name="Time Zones", value='\n'.join(tz_field), inline=True)
        embed.add_field(name="Time", value='\n'.join(time_field), inline=True)
        dest = ctx.author if ctx.bot.config.dm_only else ctx
        await dest.send(embed=embed)
        if ctx.bot.config.delete_commands:
            await ctx.message.delete()
