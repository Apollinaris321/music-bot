import functools

import discord
from discord.ext import commands, tasks
import yt_dlp
import asyncio
import queue
import os
import time
import threading
import sys
import signal
from collections import deque
from dotenv import load_dotenv


# TODO make two bots

#   ctx
#   channel = ctx.author.voice.channel
#   store the channel so i can connect to it
#   voice_client = await channel.connect()
#   voice_client.disconnect()
#   move_to()
#   is_connected()

# Handle termination signals
async def shutdown():
    print("Shutting down gracefully...")
    await bot.close()  # Disconnect from Discord
    sys.exit(0)  # Exit script cleanly


def signal_handler(sig, frame):
    asyncio.create_task(shutdown())  # Run the shutdown coroutine


# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


# pip install --upgrade yt-dlp
cookie_path = "cookies.txt"

load_dotenv()
TOKEN = os.getenv("DISCORD_INTRO_BOT_TOKEN")

# Set up bot
PREFIX = "!"
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)


# Global context
class Playlist():
    def __init__(self, ctx):
        self.ctx = None
        self.intro_playlist = []
        self.lock = asyncio.Lock()
        self.voice_client = None

    async def add_song(self, userId):
        async with self.lock:
            self.intro_playlist.append(userId)


    async def reset(self):
        async with self.lock:
            if playlist.voice_client:
                playlist.voice_client.stop()
                playlist.intro_playlist.clear()


    async def play_next_song(self):
        async with self.lock:
            if len(self.intro_playlist) > 0:
                asyncio.create_task(self.play_song())


    async def play_song(self):
        async with self.lock:
            if self.voice_client and self.voice_client.is_connected() and not self.voice_client.is_playing():

                # there are intro songs to be played
                if len(self.intro_playlist) > 0:

                    url = self.intro_playlist.pop()
                    source = discord.FFmpegPCMAudio(url)
                    def after_playing(error):
                        asyncio.run_coroutine_threadsafe(self.play_next_song(), bot.loop)

                    try:
                        self.voice_client.play(source, after=after_playing)
                    except:
                        return


playlist = Playlist(ctx=None)

ydl_opts = {
    'format': 'bestaudio/best/worstaudio/worst',
    'quiet': True,
    'no_warnings': True,
    'verbose': False,
    'noplaylist': True,
    "cookiefile": cookie_path,
}


@bot.command()
async def join(ctx):
    """Joins the voice channel of the user."""
    global playlist

    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send(f"{ctx.author.mention}, you need to be in a voice channel first!")
        return

    async with playlist.lock:
        # Get the voice channel the user is in
        channel = ctx.author.voice.channel
        voice_client = ctx.voice_client

        if voice_client is None:
            # Bot is not connected to any voice channel in this guild, try to connect
            try:
                playlist.voice_client = await channel.connect()
                await ctx.send(f"Successfully joined `{channel.name}`!")
            except discord.Forbidden:
                await ctx.send(f"I don't have permission to join `{channel.name}`.")
            except discord.ClientException as e:
                await ctx.send(f"Failed to join the channel: {e}") # E.g., Already connecting
            except Exception as e:
                await ctx.send(f"An unexpected error occurred: {e}")
                print(f"Error joining channel {channel.id}: {e}") # Log for debugging

        elif voice_client.is_connected():
            # Bot is already connected in this guild
            if voice_client.channel == channel:
                # Bot is already in the SAME channel as the user
                await ctx.send(f"I'm already in the channel: `{channel.name}`")
            else:
                # Bot is in a DIFFERENT channel, move to the user's channel
                try:
                    await voice_client.move_to(channel)
                    await ctx.send(f"Moved to `{channel.name}`.")
                except discord.Forbidden:
                    await ctx.send(f"I don't have permission to move to `{channel.name}`.")
                except Exception as e:
                    await ctx.send(f"Failed to move to the channel: {e}")
                    print(f"Error moving to channel {channel.id}: {e}")

        else:
            # This case is unlikely if voice_client was not None, but handles edge cases
            # where voice_client exists but isn't properly connected. Treat as needing to connect.
            try:
                playlist.voice_client = await channel.connect()
                await ctx.send(f"Reconnected to `{channel.name}`!")
            except Exception as e:
                await ctx.send(f"An error occurred while trying to connect/reconnect: {e}")
                print(f"Error reconnecting to channel {channel.id}: {e}")


@bot.command()
async def leave(ctx):
    """Disconnects the bot from voice."""
    global playlist, lock

    async with playlist.lock:
        if playlist.voice_client and playlist.voice_client.is_connected():
            await playlist.reset()
            await playlist.voice_client.disconnect()


@bot.command()
async def ireset(ctx):
    """Stops the current song."""
    global playlist, lock
    await playlist.reset()


@bot.event
async def on_voice_state_update(member, before, after):
    # Ignore bot users
    if member.bot:
        return

    # Check if the member joined a voice channel
    if before.channel is None and after.channel is not None:
        # Get the bot's voice client for the guild
        voice_client = discord.utils.get(bot.voice_clients, guild=member.guild)
        if voice_client and voice_client.channel == after.channel:
            playlist.intro_playlist.append(str(member.id) + ".mp3")
            if voice_client and not playlist.voice_client.is_playing():
                await playlist.play_song()



@tasks.loop(minutes=5)
async def auto_disconnect_if_alone():
    for vc in bot.voice_clients:
        channel = vc.channel
        members = channel.members

        # Count non-bot members
        non_bots = [m for m in members if not m.bot]

        if len(non_bots) == 0:
            print(f"Bot is alone in {channel.name}, disconnecting...")
            await vc.disconnect()


@bot.command()
async def set_intro(ctx, url: str, start_time: int, stop_time: int):
    """[url] [start_time_seconds] [stop_time_seconds] . example: youtube.com/watchdd 82 90   sets the intro song for a user. will play everytime the user joins the channel. every user can only have one. new song will overwrite old one"""
    global voice_client

    print(f"start:{start_time}, stop: {stop_time}, user_id: {ctx.author.id}, url: {url}")

    # Validate inputs
    if start_time < 0 or stop_time <= start_time:
        await ctx.send("Invalid times! Start time must be >= 0 and stop time must be > start time.")
        return

    # Start the processing in a background thread
    thread = threading.Thread(
        target=download_audio_snippet,
        args=(url, start_time, stop_time, ctx.author.id)
    )
    thread.start()


def download_audio_snippet(url="", start=0, stop=0, output_file="snippet"):
    print(f"download_audio_snippet: start:{start}, stop:{stop} url:{url}, output_file:{output_file}")
    output_file = str(output_file)
    cookie_path = "cookies.txt"

    if start > stop:
        return

    if stop - start > 20:
        return

    if os.path.exists(f"{output_file}.mp3"):
        os.remove(f"{output_file}.mp3")

    if stop:
        stop = int(stop)
    if start:
        start = int(start)

    if stop == 0:
        stop = start + 5

    options = {
        "format": "bestaudio",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
        }],
        "postprocessor_args": [
            "-ss", str(start), "-to", str(stop)
        ],
        'outtmpl': output_file,
        'quiet': False,
        'no_warnings': True,
        'verbose': False,
        'logger': None,
        'progress_hooks': [],
        "cookiefile": cookie_path,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])

    print(f"Audio snippet saved as {output_file}")


# Run the bot
bot.run(TOKEN)