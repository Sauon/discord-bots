from datetime import datetime, timedelta, timezone

from discord.ext.commands import Bot, Context, check, command
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound

from discord_bots.checks import is_admin
from discord_bots.cogs.base import BaseCog
from discord_bots.config import RE_ADD_DELAY
from discord_bots.models import (
    Map,
    MapVote,
    Queue,
    Rotation,
    RotationMap,
    Session,
    SkipMapVote,
    VotePassedWaitlist,
)
from discord_bots.utils import update_next_map_to_map_after_next

# The number of votes needed to succeed a map skip / replacement
MAP_VOTE_THRESHOLD: int = 7


class VoteCommands(BaseCog):
    def __init__(self, bot: Bot):
        super().__init__(bot)

    def get_maps_str():
        maps: list[Map] = Session().query(Map).all()
        return ", ".join([map.short_name for map in maps])

    @command()
    @check(is_admin)
    async def setmapvotethreshold(self, ctx: Context, threshold: int):
        """
        Set the number of votes required to pass
        """
        global MAP_VOTE_THRESHOLD
        MAP_VOTE_THRESHOLD = threshold

        await self.send_success_message(
            f"Map vote threshold set to {MAP_VOTE_THRESHOLD}"
        )

    @command()
    async def unvote(self, ctx: Context):
        """
        Remove all of a player's votes
        """
        message = ctx.message
        session = ctx.session

        session.query(MapVote).filter(MapVote.player_id == message.author.id).delete()
        session.query(SkipMapVote).filter(
            SkipMapVote.player_id == message.author.id
        ).delete()
        session.commit()

        await self.send_success_message("All map votes deleted")

    @command()
    async def unvotemap(self, ctx: Context, map_short_name: str):
        """
        Remove all of a player's votes for a map
        Use irrespective of rotation/queue because that seems like a super niche use case
        TODO: Unvote for many maps at once
        """
        session = ctx.session
        message = ctx.message

        map: Map | None = (
            session.query(Map).filter(Map.short_name.ilike(map_short_name)).first()
        )

        map_votes: list[MapVote] | None = (
            session.query(MapVote)
            .join(RotationMap, RotationMap.id == MapVote.rotation_map_id)
            .filter(
                MapVote.player_id == message.author.id,
                RotationMap.map_id == map.id,
            )
            .all()
        )
        if not map_votes:
            await self.send_error_message(
                f"You don't have any votes for {map_short_name}"
            )
            return

        for map_vote in map_votes:
            session.delete(map_vote)
        session.commit()
        await self.send_success_message(f"Your vote for {map.short_name} was removed")

    @command()
    async def unvoteskip(self, ctx: Context):
        """
        Remove all of a player's votes to skip the next map
        Same disregard for rotation/queue as with unvotemap
        """
        session = ctx.session
        message = ctx.message

        skip_map_votes: SkipMapVote | None = (
            session.query(SkipMapVote)
            .filter(SkipMapVote.player_id == message.author.id)
            .all()
        )
        if not skip_map_votes:
            await self.send_error_message(
                "You don't have a vote to skip the current map."
            )
            return

        for skip_map_vote in skip_map_votes:
            session.delete(skip_map_vote)
        session.commit()
        await self.send_success_message(
            "Your vote to skip the current map was removed."
        )

    @command()
    async def mockvotes(self, ctx: Context):
        # To be removed
        message = ctx.message
        session = ctx.session

        session.add(
            SkipMapVote(
                message.channel.id,
                59148727633321984,
                "e8a8186a-d315-44e6-8ab1-c190410fe28c",
            )
        )
        session.add(
            SkipMapVote(
                message.channel.id,
                71834517970620416,
                "e8a8186a-d315-44e6-8ab1-c190410fe28c",
            )
        )
        session.add(
            SkipMapVote(
                message.channel.id,
                79349357186396160,
                "e8a8186a-d315-44e6-8ab1-c190410fe28c",
            )
        )
        session.add(
            SkipMapVote(
                message.channel.id,
                83207382410199040,
                "e8a8186a-d315-44e6-8ab1-c190410fe28c",
            )
        )
        session.add(
            SkipMapVote(
                message.channel.id,
                83686402927104000,
                "e8a8186a-d315-44e6-8ab1-c190410fe28c",
            )
        )
        session.add(
            SkipMapVote(
                message.channel.id,
                86254915835400192,
                "e8a8186a-d315-44e6-8ab1-c190410fe28c",
            )
        )

        session.commit()

    @command()
    async def votemap(self, ctx: Context, queue_name: str, map_short_name: str):
        """
        Vote for a map in a queue
        TODO: Vote for many maps at once
        TODO: Decide if/how to list voteable maps for each queue/rotation
        """
        session = ctx.session
        message = ctx.message

        queue: Queue | None = (
            session.query(Queue).filter(Queue.name.ilike(queue_name)).first()
        )
        if not queue:
            await self.send_error_message(f"Could not find queue **{queue_name}**")
            return

        rotation: Rotation | None = (
            session.query(Rotation)
            .join(Queue, Queue.rotation_id == Rotation.id)
            .filter(Queue.id == queue.id)
            .first()
        )

        map: Map | None = (
            session.query(Map).filter(Map.short_name.ilike(map_short_name)).first()
        )

        rotation_map: RotationMap | None = (
            session.query(RotationMap)
            .filter(RotationMap.map_id == map.id)
            .filter(RotationMap.rotation_id == rotation.id)
            .first()
        )

        session.add(MapVote(message.channel.id, message.author.id, rotation_map.id))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()

        rotation_map_votes: list[MapVote] = (
            session.query(MapVote)
            .filter(MapVote.rotation_map_id == rotation_map.id)
            .all()
        )
        if len(rotation_map_votes) == MAP_VOTE_THRESHOLD:
            session.query(RotationMap).filter(
                RotationMap.rotation_id == rotation.id
            ).filter(RotationMap.is_next == True).update({"is_next": False})
            rotation_map.is_next = True
            session.query(MapVote).delete()
            session.query(SkipMapVote).delete()

            if message.guild:
                # TODO: Check if another vote already exists
                session.add(
                    VotePassedWaitlist(
                        channel_id=message.channel.id,
                        guild_id=message.guild.id,
                        end_waitlist_at=datetime.now(timezone.utc)
                        + timedelta(seconds=RE_ADD_DELAY),
                    )
                )
            session.commit()

            await self.send_success_message(
                f"Vote for **{map.full_name} ({map.short_name})** passed!\nMap rotated, all votes removed"
            )
        else:
            map_votes = (
                session.query(MapVote)
                .filter(MapVote.rotation_map_id == rotation_map.id)
                .count()
            )

            await self.send_success_message(
                f"Added map vote for **{map.short_name}** in **{queue.name}**.\n`!unvotemap` to remove your vote.\nMap vote status: [{map_votes}/{MAP_VOTE_THRESHOLD}]"
            )

            # old logic for showing current vote status
            # map_votes: list[MapVote] = session.query(MapVote).all()
            # voted_map_ids: list[str] = [map_vote.map_id for map_vote in map_votes]
            # voted_maps: list[Map] = (
            #     session.query(Map).filter(Map.id.in_(voted_map_ids)).all()  # type: ignore
            # )
            # voted_maps_str = ", ".join(
            #     [
            #         f"{voted_map.short_name} [{voted_map_ids.count(voted_map.id)}/{MAP_VOTE_THRESHOLD}]"
            #         for voted_map in voted_maps
            #     ]
            # )


    @command()
    async def voteskip(self, ctx: Context, queue_name: str):
        """
        Vote to skip a map in a queue
        """
        session = ctx.session
        message = ctx.message

        queue: Queue | None = (
            session.query(Queue).filter(Queue.name.ilike(queue_name)).first()
        )
        if not queue:
            await self.send_error_message(f"Could not find queue **{queue_name}**")
            return

        rotation: Rotation | None = (
            session.query(Rotation)
            .join(Queue, Queue.rotation_id == Rotation.id)
            .filter(Queue.id == queue.id)
            .first()
        )

        session.add(SkipMapVote(message.channel.id, message.author.id, rotation.id))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()

        skip_map_votes_count = (
            session.query(SkipMapVote)
            .filter(SkipMapVote.rotation_id == rotation.id)
            .count()
        )
        if skip_map_votes_count >= MAP_VOTE_THRESHOLD:
            await self.send_success_message(
                f"Vote to skip the current map passed!  All votes removed."
            )
            await update_next_map_to_map_after_next(rotation.id, True)
            session.query(MapVote).delete()
            session.query(SkipMapVote).delete()

            if message.guild:
                # TODO: Might be bugs if two votes pass one after the other
                vpw: VotePassedWaitlist | None = session.query(
                    VotePassedWaitlist
                ).first()
                if not vpw:
                    session.add(
                        VotePassedWaitlist(
                            channel_id=message.channel.id,
                            guild_id=message.guild.id,
                            end_waitlist_at=datetime.now(timezone.utc)
                            + timedelta(seconds=RE_ADD_DELAY),
                        )
                    )

            session.commit()
        else:
            await self.send_success_message(
                f"Added vote to skip the current map.\n!unvoteskip to remove vote.\nVotes to skip: [{skip_map_votes_count}/{MAP_VOTE_THRESHOLD}]"
            )
