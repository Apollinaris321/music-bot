import functools

import discord
from discord.ext import commands
import yt_dlp
import asyncio
import queue
import os
import time
import threading
import sys
import signal
from Song import Song, Playlist
from collections import deque
from dotenv import load_dotenv

#TODO
# before adding intros i need to store the timestamps of the songs and when they were paused
# then i can try intro's
# use some debug to print the current playlist with url and timestamp
# i think tomorrow i will have the intros ready

#TODO intro
# implement the feature to play a song from a specific timestamp
# when user joins. stop song and store timestamp
# put intro song in front of the queue
# play intro using normal play_song()
# afterwards everything resumes normally
# --- what if second user joins at the same time?
# this will cause the first intro to stop and second one to play
# fuck this seperate intro playlist
# wenn jemaind joined dann normale playlist anhalten wie oben erwähnt
# dann spielt intro playlist und wenn jemand rein joined einfach in die queue packen und das intro
# spielt dann als nächstes ab
# in der callback function nachschauen -> intro queue leer ? -> resume normale playlist play_song()
# fertig


# Guild == Server

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
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

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
        self.playlist = asyncio.PriorityQueue()
        self.song_index = 0
        self.voice_client = None
        self.current_song = None

    async def add_song(self, info):
        timestamp = time.time()
        await self.playlist.put((2, timestamp, info))

    async def add_intro(self, info):
        timestamp = time.time()
        await self.playlist.put((1, timestamp, info))

#this has to be global and others have to use block or release
lock = asyncio.Lock()

playlist = Playlist(ctx=None)

ydl_opts = {
    'format': 'bestaudio/best/worstaudio/worst',
    'quiet': True,
    'no_warnings': True,
    'verbose': False,
    'noplaylist': True,
    "cookiefile": cookie_path,
}


# TODO callback when finished -> play next song
async def play_song():
    global playlist

    if playlist.voice_client and not playlist.voice_client.is_playing():
        priority , timestamp, info = await playlist.playlist.get()
        if info is None:
            return
        if priority == 2:
            playlist.current_song = info
        else:
            playlist.current_song = None
        start_time = 0
        ffmpeg_options = {
            "before_options": f"-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -ss {start_time}",
            "options": "-vn",
        }
        source = discord.FFmpegPCMAudio(info['url'], **ffmpeg_options)
        def after_playing(error):
            asyncio.run_coroutine_threadsafe(play_song(), bot.loop)

        playlist.voice_client.play(source, after=after_playing)


@bot.command()
async def join(ctx):
    """Joins the voice channel of the user."""
    global lock

    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send(f"{ctx.author.mention}, you need to be in a voice channel first!")
        return

    async with lock:
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
                    print(f"Error moving to channel {channel.id}: {e}") # Log for debugging

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

    async with lock:
        if playlist.voice_client and playlist.voice_client.is_connected():
            await playlist.voice_client.disconnect()
            playlist.voice_client = None


@bot.command()
async def play(ctx, url: str):
    """!play [url]   # Adds a song to the queue or plays immediately if idle."""
    global lock, playlist

    # Optional: Show immediate feedback that the command was received
    # --- Run the BLOCKING code in a separate thread ---
    loop = asyncio.get_running_loop()

    info = ""
    try:
        # Use functools.partial to pass arguments to the blocking function
        # The first argument to run_in_executor is the executor (None uses default ThreadPoolExecutor)
        # The second is the function to run
        # Subsequent arguments are passed TO that function
        info = await loop.run_in_executor(
            None,  # Use the default executor
            functools.partial(yt_dlp.YoutubeDL(ydl_opts).extract_info, url, download=False)
        )
        await playlist.add_song(info)
        print(f"[{ctx.guild.id}] Finished info extraction for: {url}")

    except Exception as e:
        print(f"Error during info extraction: {e}")
        await ctx.message.add_reaction('❌')
        await ctx.send(f"Failed to get info for the URL. Error: {e}")
        return

    await ctx.message.add_reaction('✅') # Indicate success
    await ctx.send(f"Added **{info.get('title', 'Unknown Title')}** to the queue.")
    async with lock:
        await play_song()


# TODO
@bot.command()
async def stop(ctx):
    """Stops the current song."""
    global playlist, lock

    async with lock:
        if playlist.voice_client and playlist.voice_client.is_playing():
            playlist.voice_client.stop()
            await ctx.send("⏹️ Stopped playback.")


@bot.command()
async def next(ctx):
    """Skips to the next song."""
    global playlist, lock

    async with lock:
        if playlist.voice_client and playlist.voice_client.is_playing():
            playlist.voice_client.stop()
            await ctx.send("⏭️ Skipping to next song.")
        await ctx.send("nothing to skip...")


@bot.command()
async def pause(ctx):
    """Pauses the audio."""
    global playlist, lock

    async with lock:
        if playlist.voice_client and playlist.voice_client.is_playing():
            playlist.voice_client.pause()
            await ctx.send("⏸️ Paused.")


@bot.command()
async def resume(ctx):
    """Resumes the audio."""
    global playlist, lock

    async with lock:
        if playlist.voice_client and playlist.voice_client.is_paused():
            playlist.voice_client.resume()
            await ctx.send("▶️ Resumed.")


@bot.command()
async def intro(ctx):
    global playlist, lock

    await playlist.add_intro({'url': "https://rr5---sn-4g5edndr.googlevideo.com/videoplayback?expire=1743883949&ei=TTrxZ7_BC5ybsvQP9bHz4AQ&ip=2003%3Af0%3A3f13%3A767%3Ad587%3A27a2%3Ae0f1%3A902a&id=o-AB4tS3xoXpD3cvu0IEQbt5r7OZ-Z4LS6f89jUs3YbkbU&itag=251&source=youtube&requiressl=yes&xpc=EgVo2aDSNQ%3D%3D&met=1743862349%2C&mh=7s&mm=31%2C26&mn=sn-4g5edndr%2Csn-h0jeenle&ms=au%2Conr&mv=m&mvi=5&pl=35&rms=au%2Cau&initcwndbps=2537500&bui=AccgBcPs8hgs6H463eD0Oz-IK0mu3MsGB-7s3f1MTzomBrlP8xwWZAOnLDVQpnrDHxMKfbjzM4Je1Yfr&vprv=1&svpuc=1&mime=audio%2Fwebm&ns=3iuqyECWLPt9y9B2uBddeQQQ&rqh=1&gir=yes&clen=83809&dur=8.121&lmt=1743028121993696&mt=1743861907&fvip=3&keepalive=yes&lmw=1&c=TVHTML5&sefc=1&txp=4432534&n=nfMIfBMQ0a3jiQ&sparams=expire%2Cei%2Cip%2Cid%2Citag%2Csource%2Crequiressl%2Cxpc%2Cbui%2Cvprv%2Csvpuc%2Cmime%2Cns%2Crqh%2Cgir%2Cclen%2Cdur%2Clmt&sig=AJfQdSswRQIgeF47_cZjHwKEALhCiCsB8rWDmW-P8KSPPqrlnbkHna0CIQDUE5vK_d8CijR1B2-TCOsBJGa-KwsH6X3aVFbMDa_ggQ%3D%3D&lsparams=met%2Cmh%2Cmm%2Cmn%2Cms%2Cmv%2Cmvi%2Cpl%2Crms%2Cinitcwndbps&lsig=ACuhMU0wRAIgBW8DDP13nE2Zp8oqCAnUWClwdpCy0rox9eEhL28CcsUCIBDAvx3UYYuhWDLeW8T7fXW0yIov7LZnvzL4U0SRo2I6"})
    async with lock:
        if playlist.voice_client and playlist.voice_client.is_playing():
            await playlist.add_song(playlist.current_song)
            playlist.current_song = None
            playlist.voice_client.stop()
        else:
            await play_song()
    print("releasing lock...")


# Run the bot
bot.run(TOKEN)