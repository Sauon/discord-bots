import logging
from typing import List, Optional

from discord import Colour, Embed, Interaction, app_commands
from discord.ext.commands import Bot
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.session import Session as SQLAlchemySession
from table2ascii import Alignment, PresetStyle, table2ascii

from discord_bots.checks import is_admin_app_command, is_command_channel
from discord_bots.cogs.base import BaseCog
from discord_bots.models import (
    Category,
    FinishedGame,
    FinishedGamePlayer,
    Map,
    PlayerCategoryTrueskill,
    Queue,
    Rotation,
    RotationMap,
    Session,
)
from discord_bots.utils import (
    category_autocomplete_with_user_id,
    category_name_autocomplete_without_user_id,
    code_block,
    map_full_name_autocomplete,
    map_short_name_autocomplete,
    queue_autocomplete,
    win_rate,
)
from discord_bots.views.configure_map import MapConfigureView

_log = logging.getLogger(__name__)


class MapCommands(BaseCog):
    def __init__(self, bot: Bot):
        super().__init__(bot)

    group = app_commands.Group(name="map", description="Map commands")

    # broken commands
    """
    # TODO: update to !map <queue_name>

    @command(name="map")
    async def map_(ctx: Context):
        # TODO: This is duplicated
        session = ctx.session
        output = ""
        current_map: CurrentMap | None = session.query(CurrentMap).first()
        if current_map:
            rotation_maps: list[RotationMap] = session.query(RotationMap).order_by(RotationMap.created_at.asc()).all()  # type: ignore
            next_rotation_map_index = (current_map.map_rotation_index + 1) % len(
                rotation_maps
            )
            next_map = rotation_maps[next_rotation_map_index]

            time_since_update: timedelta = datetime.now(
                timezone.utc
            ) - current_map.updated_at.replace(tzinfo=timezone.utc)
            time_until_rotation = MAP_ROTATION_MINUTES - (time_since_update.seconds // 60)
            if current_map.map_rotation_index == 0:
                output += f"**Next map: {current_map.full_name} ({current_map.short_name})**\n_Map after next: {next_map.full_name} ({next_map.short_name})_\n"
            else:
                output += f"**Next map: {current_map.full_name} ({current_map.short_name})**\n_Map after next (auto-rotates in {time_until_rotation} minutes): {next_map.full_name} ({next_map.short_name})_\n"
        skip_map_votes: list[SkipMapVote] = session.query(SkipMapVote).all()
        output += (
            f"_Votes to skip (voteskip): [{len(skip_map_votes)}/{MAP_VOTE_THRESHOLD}]_\n"
        )

        # TODO: This is duplicated
        map_votes: list[MapVote] = session.query(MapVote).all()
        voted_map_ids: list[str] = [map_vote.map_id for map_vote in map_votes]
        voted_maps: list[Map] = (
            session.query(Map).filter(Map.id.in_(voted_map_ids)).all()  # type: ignore
        )
        voted_maps_str = ", ".join(
            [
                f"{voted_map.short_name} [{voted_map_ids.count(voted_map.id)}/{MAP_VOTE_THRESHOLD}]"
                for voted_map in voted_maps
            ]
        )
        output += f"_Votes to change map (votemap): {voted_maps_str}_\n\n"
        session.close()
        await ctx.send(embed=Embed(description=output, colour=Colour.blue()))

    TODO: decide where the random map comes from

    @bot.command()
    async def randommap(ctx: Context):
        session = ctx.session
        maps: list[Map] = session.query(Map).all()
        map = choice(maps)
        await send_message(
            ctx.message.channel,
            embed_description=f"Random map selected: **{map.full_name} ({map.short_name})**",
            colour=Colour.blue(),
        )

    TODO: change to !setrandommap <map_short_name> <rotation> <random_probability>
    random_probability stored in rotation_map

    @bot.command(usage="<map_full_name> <map_short_name> <random_probability>")
    @commands.check(is_admin)
    async def addrandomrotationmap(
        ctx: Context, map_full_name: str, map_short_name: str, random_probability: float
    ):
        # Adds a special map to the rotation that is random each time it comes up
        message = ctx.message
        if random_probability < 0 or random_probability > 1:
            await send_message(
                message.channel,
                embed_description=f"Random map probability must be between 0 and 1!",
                colour=Colour.red(),
            )
            return

        session = ctx.session
        session.add(
            RotationMap(
                f"{map_full_name} (R)",
                f"{map_short_name}R",
                is_random=True,
                random_probability=random_probability,
            )
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            await send_message(
                message.channel,
                embed_description=f"Error adding random map {map_full_name} ({map_short_name}) to rotation. Does it already exist?",
                colour=Colour.red(),
            )
            return

        await send_message(
            message.channel,
            embed_description=f"{map_full_name} (R) ({map_short_name}R) added to map rotation",
            colour=Colour.green(),
        )
    """

    @group.command(name="configure", description="Create or Edit a map")
    @app_commands.check(is_admin_app_command)
    @app_commands.check(is_command_channel)
    @app_commands.describe(map_full_name="New or existing map")
    @app_commands.autocomplete(map_full_name=map_full_name_autocomplete)
    @app_commands.rename(map_full_name="map")
    async def configure(self, interaction: Interaction, map_full_name: str):
        exists: bool = False
        session: SQLAlchemySession
        with Session() as session:
            map: Map | None = (
                session.query(Map).filter(Map.full_name.ilike(map_full_name)).first()
            )
            if map:
                map_configure_view = MapConfigureView(
                    map.full_name, map.short_name, map.image_url, map.id
                )
            else:
                map_configure_view = MapConfigureView(
                    map_full_name, map_full_name[:2], None
                )
            embed: Embed = map_configure_view.embed
            map_configure_view.embed = embed
            await interaction.response.send_message(
                embed=embed,
                view=map_configure_view,
                ephemeral=True,
            )

    @group.command(name="remove", description="Remove a map from the map pool")
    @app_commands.check(is_admin_app_command)
    @app_commands.check(is_command_channel)
    @app_commands.describe(map_short_name="Short name of map")
    @app_commands.autocomplete(map_short_name=map_short_name_autocomplete)
    @app_commands.rename(map_short_name="map")
    async def removemap(self, interaction: Interaction, map_short_name: str):
        """
        Remove a map from the map pool
        """
        session: SQLAlchemySession
        with Session() as session:
            try:
                map = (
                    session.query(Map)
                    .filter(Map.short_name.ilike(map_short_name))
                    .one()
                )
            except NoResultFound:
                await interaction.response.send_message(
                    embed=Embed(
                        description=f"Could not find map **{map_short_name}**",
                        colour=Colour.red(),
                    ),
                    ephemeral=True,
                )
                return

            map_rotations: List[Rotation] | None = (
                session.query(Rotation)
                .join(RotationMap, RotationMap.rotation_id == Rotation.id)
                .filter(RotationMap.map_id == map.id)
                .all()
            )

            if map_rotations:
                error = f"Please remove map from rotation first.\n\n**{map.full_name}** belongs to the following rotations:"
                for map_rotation in map_rotations:
                    error += f"\n- {map_rotation.name}"
                await interaction.response.send_message(
                    embed=Embed(
                        description=error,
                        colour=Colour.red(),
                    ),
                    ephemeral=True,
                )
            else:
                session.delete(map)
                session.commit()
                await interaction.response.send_message(
                    embed=Embed(
                        description=f"**{map.full_name} ({map.short_name})** removed from maps",
                        colour=Colour.green(),
                    )
                )

    @group.command(
        name="stats",
        description="Privately displays your stats per map. Optionally specify a category",
    )
    @app_commands.rename(category_name="category")
    @app_commands.describe(category_name="Optional name of a specific category")
    @app_commands.autocomplete(category_name=category_autocomplete_with_user_id)
    async def mapstats(
        self, interaction: Interaction, category_name: Optional[str] = None
    ):
        # TODO: merge with /stats by making this a subcommand
        session: SQLAlchemySession
        with Session() as session:
            if category_name:
                category: Category | None = (
                    session.query(Category).filter(Category.name == category_name).one()
                )
                # get the queues for each category, since rotations are per queue and not per category
                queues: list[Queue] | None = (
                    session.query(Queue).filter(Queue.category_id == category.id).all()
                )
            else:
                queues: list[Queue] | None = session.query(Queue).all()
            if not queues:
                await interaction.response.send_message(
                    embed=Embed(
                        description=f"Could not find any queues",
                        colour=Colour.red(),
                    ),
                    ephemeral=True,
                )
                return
            rotation_ids = [queue.rotation_id for queue in queues]
            maps: list[Map] | None = (
                session.query(Map)
                .join(RotationMap, RotationMap.map_id == Map.id)
                .filter(RotationMap.rotation_id.in_(rotation_ids))
                .order_by(Map.full_name)
                .all()
            )
            if not maps:
                await interaction.response.send_message(
                    embed=Embed(
                        description=f"Could not find any maps for category '{category_name}'",
                        colour=Colour.red(),
                    ),
                    ephemeral=True,
                )
                return
            fgps: List[FinishedGamePlayer] | None = (
                session.query(FinishedGamePlayer)
                .filter(FinishedGamePlayer.player_id == interaction.user.id)
                .all()
            )
            if not fgps:
                await interaction.response.send_message(
                    embed=Embed(
                        description=f"You have not played any games",
                        colour=Colour.red(),
                    ),
                    ephemeral=True,
                )
                return
            finished_game_ids: List[str] | None = [fgp.finished_game_id for fgp in fgps]
            conditions = [FinishedGame.id.in_(finished_game_ids)]
            if category_name:
                conditions.append(FinishedGame.category_name == category_name)
            fgs: List[FinishedGame] | None = (
                session.query(FinishedGame).filter(*conditions).all()
            )
            if not fgs:
                await interaction.response.send_message(
                    embed=Embed(
                        description=f"Could not find any finished games for you",
                        colour=Colour.red(),
                    ),
                    ephemeral=True,
                )
                return
            fgps_by_finished_game_id: dict[str, FinishedGamePlayer] = {
                fgp.finished_game_id: fgp for fgp in fgps
            }
            cols = []
            for m in maps:

                def map_stats(finished_games: list[FinishedGame]):
                    wins = [
                        fg
                        for fg in finished_games
                        if fg.winning_team == fgps_by_finished_game_id[fg.id].team
                    ]
                    losses = [
                        fg
                        for fg in finished_games
                        if fg.winning_team != fgps_by_finished_game_id[fg.id].team
                        and fg.winning_team != -1
                    ]
                    ties = [fg for fg in finished_games if fg.winning_team == -1]
                    return len(wins), len(losses), len(ties)

                fgs_for_map = [fg for fg in fgs if fg.map_full_name == m.full_name]
                num_games = len(fgs_for_map)
                if num_games <= 0:
                    continue
                wins, losses, ties = map_stats(fgs_for_map)
                wr = win_rate(wins, losses, ties)
                cols.append(
                    [
                        m.full_name,
                        f"{wins}",
                        f"{losses}",
                        f"{ties}",
                        num_games,
                        f"{wr}%",
                    ]
                )
        cols.sort(
            key=lambda lst: lst[-1], reverse=True
        )  # sort by WR in descending order
        table = table2ascii(
            header=["Map", "W", "L", "T", "Total", "WR"],
            body=cols,
            style=PresetStyle.plain,
            first_col_heading=True,
            alignments=[
                Alignment.LEFT,
                Alignment.DECIMAL,
                Alignment.DECIMAL,
                Alignment.DECIMAL,
                Alignment.DECIMAL,
                Alignment.RIGHT,
            ],
        )
        if category_name:
            title = f"{interaction.user.display_name} Map Stats for {category_name}"
        else:
            title = f"{interaction.user.display_name} Overall Map Stats"
        embed = Embed(
            title=title, description=code_block(table), colour=Colour.dark_embed()
        )
        # await interaction.response.send_message(embed=embed, ephemeral=True)
        await interaction.response.send_message(
            content=f"{title}\n{code_block(table)}", ephemeral=True
        )  # TODO: temp fix

    @group.command(
        name="globalstats", description="Displays global statistics for each map"
    )
    @app_commands.rename(category_name="category")
    @app_commands.describe(category_name="Optional name of a specific category")
    @app_commands.autocomplete(category_name=category_name_autocomplete_without_user_id)
    async def globalmapstats(
        self, interaction: Interaction, category_name: Optional[str] = None
    ):
        # Explicitly does not use a discord.Embed, due to the limit of the Embed length (Note: this won't look pretty on mobile)
        session: SQLAlchemySession
        with Session() as session:
            maps: list[Map] | None = session.query(Map).order_by(Map.full_name).all()

            def map_stats(finished_games: list[FinishedGame]):
                team0_wins = [fg for fg in finished_games if fg.winning_team == 0]
                team1_wins = [fg for fg in finished_games if fg.winning_team == 1]
                ties = [fg for fg in finished_games if fg.winning_team == -1]
                return len(team0_wins), len(team1_wins), len(ties)

            cols = []
            for m in maps:
                conditions = [FinishedGame.map_full_name == m.full_name]
                if category_name:
                    conditions.append(FinishedGame.category_name == category_name)
                finished_games = session.query(FinishedGame).filter(*conditions).all()
                num_games = len(finished_games)
                if num_games <= 0:
                    continue
                team0_wins, team1_wins, ties = map_stats(finished_games)
                team0_win_rate = win_rate(team0_wins, team1_wins, ties)
                team1_win_rate = win_rate(team1_wins, team0_wins, ties)
                cols.append(
                    [
                        m.full_name,
                        team0_wins,
                        f"{team0_win_rate}%",
                        team1_wins,
                        f"{team1_win_rate}%",
                        ties,
                        len(finished_games),
                    ]
                )
        table = table2ascii(
            header=["Map", "Team0", "WR", "Team1", "WR", "Ties", "Total"],
            body=cols,
            style=PresetStyle.plain,
            first_col_heading=True,
            alignments=[
                Alignment.LEFT,
                Alignment.DECIMAL,
                Alignment.RIGHT,
                Alignment.DECIMAL,
                Alignment.RIGHT,
                Alignment.DECIMAL,
                Alignment.DECIMAL,
            ],
        )
        if category_name:
            content = f"Global Map Stats for **{category_name}**"
        else:
            content = "Global Map Stats"
        content += f"\n{code_block(table)}"
        await interaction.response.send_message(
            content=content,
            ephemeral=True,
        )
