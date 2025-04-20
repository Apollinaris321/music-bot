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
from collections import deque
from dotenv import load_dotenv



#TODO
# - dont allow more than 10 songs
# - predownload links for the queue -> less lag
# - ffmpeg is really slow ????? bug
# - print queue
# - was passiert wenn mehrere joinen wegen intro song?
# - when play also automatically join
# - change set_intro
# - set_intro seconds make 00:00 format
# - maybe have two bots. one for music and the other for the intros ?
# - the intro bot could just paste the pause/resume commands
# - change the download of intros to just streaming them
# - prefetch the intro songs url


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

cookie_path = "cookies.txt"


load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Set up bot
PREFIX = "!"
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)


# VLC alternative - Discord audio
song_queue = deque()
voice_client = None
current_song = None  # To store the current song's info
start_time_tracker = 0  # Manual tracking of start time


ydl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'verbose': False,
    'noplaylist': True,
    "cookiefile": cookie_path,
}


#await play_song(ctx.author.voice.channel , url)
async def play_next(ctx):
    """Play the next song in the queue."""
    global voice_client, current_song, start_time_tracker
    if len(song_queue) > 0:
        url = song_queue.popleft()
        current_song = None
        start_time_tracker = 0
        await play_song(ctx.author.voice.channel , url)


async def play_song(voice_channel, url, start_time=0, resume=False):
    """Plays audio from a YouTube URL with optional start time."""
    global voice_client, current_song, start_time_tracker

    if not voice_client or not voice_client.is_connected():
        voice_client = await voice_channel.connect()

    if resume and current_song:
        audio_url = current_song["url"]
    else:
         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info['url']
            current_song = {"url": audio_url, "title": info['title'], "position": start_time}

    ffmpeg_options = {
        "before_options": f"-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -ss {start_time}",
        "options": "-vn",
    }
    source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
    def after_playing(error):
        asyncio.run_coroutine_threadsafe(play_next(voice_channel), bot.loop)

    voice_client.play(source, after=after_playing)
    start_time_tracker = time.time()


def download_audio_snippet(url="", start=0, stop=0, output_file="snippet"):
    print(f"download_audio_snippet: start:{start}, stop:{stop} url:{url}, output_file:{output_file}")
    output_file = str(output_file)

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


@bot.command()
async def join(ctx):
    """Joins the voice channel of the user."""
    global voice_client
    if ctx.author.voice:
        voice_client = await ctx.author.voice.channel.connect()
    else:
        await ctx.send("You need to be in a voice channel!")


@bot.command()
async def leave(ctx):
    """Disconnects the bot from voice."""
    global voice_client
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        voice_client = None


@bot.command()
async def play(ctx, url: str):
    """!play [url]   #Adds a song to the queue or plays immediately if idle."""
    if voice_client and voice_client.is_playing():
        song_queue.append(url)
        await ctx.send("🎵 Added to queue.")
    else:
        await play_song(ctx.author.voice.channel , url)



async def play_intro(member):
    """Plays the local intro song, then resumes the previous song from its last position."""
    global voice_client, current_song, start_time_tracker

    if not voice_client or not voice_client.is_connected():
        return

    #if no song is currently playing then connect to voice channel
    if not voice_client or not voice_client.is_connected():
        voice_client = await member.voice.channel.connect()

    paused_time = None
    if voice_client.is_playing():
        voice_client.pause()
        paused_time = time.time() - start_time_tracker

    # Play the intro file
    if os.path.exists(f"{member.id}.mp3"):
        intro_source = discord.FFmpegPCMAudio(f"{member.id}.mp3")
        voice_client.play(intro_source)

        while voice_client.is_playing():
            await asyncio.sleep(0.5)

    if current_song and paused_time is not None:
        # possible bug for start time watch out!
        await play_song(member.voice.channel, current_song["url"], start_time=paused_time, resume=True)


@bot.command()
async def stop(ctx):
    """Stops the current song."""
    global current_song, start_time_tracker
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        current_song = None
        start_time_tracker = 0
        await ctx.send("⏹️ Stopped playback.")


@bot.command()
async def pause(ctx):
    """Pauses the audio."""
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await ctx.send("⏸️ Paused.")


@bot.command()
async def resume(ctx):
    """Resumes the audio."""
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await ctx.send("▶️ Resumed.")


@bot.command()
async def next(ctx):
    """Skips to the next song."""
    global current_song, start_time_tracker
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        current_song = None
        start_time_tracker = 0
        await play_next(ctx)
        await ctx.send("⏭️ Skipping to next song.")


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


@bot.event
async def on_voice_state_update(member, before, after):
    bot_voice_channel = None

    # Get the bot's current voice channel
    for vc in bot.voice_clients:
        if vc.guild == member.guild:
            bot_voice_channel = vc.channel
            break

    # Check if the user joined the same channel as the bot
    if bot_voice_channel and after.channel == bot_voice_channel and before.channel != bot_voice_channel:
        print(f"{member.name} joined {bot_voice_channel.name}!")
        await play_intro(member)


# Run the bot
bot.run(TOKEN)
