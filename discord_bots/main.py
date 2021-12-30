from datetime import datetime, timezone
import os
import traceback

from discord import Member, Message, Reaction
from discord.abc import User
from discord.channel import GroupChannel, TextChannel
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

from .bot import bot
from .commands import handle_message
from .models import Player, QueuePlayer, Session
from .tasks import (
    afk_timer_task,
    create_voice_channel_task,
    queue_waitlist_task,
    send_message_task,
)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")


@bot.event
async def on_connect():
    try:
        send_message_task.start()
    except RuntimeError as e:
        print("Encountered exception:", e)
    try:
        create_voice_channel_task.start()
    except RuntimeError as e:
        print("Encountered exception:", e)
    try:
        afk_timer_task.start()
    except RuntimeError as e:
        print("Encountered exception:", e)
    try:
        queue_waitlist_task.start()
    except RuntimeError as e:
        print("Encountered exception:", e)


BULLIEST_BOT_ID = 912605788781035541


@bot.event
async def on_message(message: Message):
    if type(message.channel) is TextChannel or type(message.channel) is GroupChannel:
        if (
            message.channel.name == "bullies-bot"
            and message.author.id != BULLIEST_BOT_ID
        ):
            print("[on_message]", message)
            try:
                await handle_message(message)
            except Exception as e:
                print(e)
                traceback.print_exc()
                await message.channel.send(f"Encountered exception: {e}")


@bot.event
async def on_reaction_add(reaction: Reaction, user: User | Member):
    session = Session()
    player: Player | None = session.query(Player).filter(Player.id == user.id).first()
    if player:
        player.last_activity_at = datetime.now(timezone.utc)
        session.commit()


@bot.event
async def on_join(member: Member):
    session = Session()
    try:
        session.add(Player(id=member.id, name=member.name))
        session.commit()
    except IntegrityError:
        session.rollback()
        player = session.query(Player).filter(Player.id == member.id).first()
        player.name = member.name
        session.commit()


@bot.event
async def on_leave(member: Member):
    session = Session()
    session.query(QueuePlayer).filter(QueuePlayer.player_id == member.id).delete()


def main():
    load_dotenv()
    API_KEY = os.getenv("DISCORD_API_KEY")
    if API_KEY:
        bot.run(API_KEY)
    else:
        print("You must define DISCORD_API_KEY!")