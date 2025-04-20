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
# - start song at specific time
# - timestamp when song started playing
# - stop song and store time when stopped
# - use the play_after hook form play_song to check if the intro queue is full
#   - if there is a song in the intro queue play it
#   - do this until the intro queue is empty then play the playlist again
#   - intro can just be added to the intro queue
#   - in the intro event check if intro queue is empty if yes -> stop playlist

# custom stop and start functionality that stores the time and timestamp
# set intro code | userId , url, start, stop


#   ctx
#   channel = ctx.author.voice.channel
#   store the channel so i can connect to it
#   voice_client = await channel.connect()
#   voice_client.disconnect()
#   move_to()
#   is_connected()

"""
FLAGS/ATTRIBUTES
voice_client.is_connected() -> bool:
Crucial: Checks if the underlying websocket connection to the voice channel is currently active. Returns True if connected, False otherwise. Always check this before trying to interact extensively.

voice_client.is_playing() -> bool:
Crucial for Music: Returns True if the bot is currently sending audio data (i.e., a song is playing via voice_client.play()).

voice_client.is_paused() -> bool:
Crucial for Music: Returns True if playback has been paused using voice_client.pause().

voice_client.channel -> discord.VoiceChannel:
Tells you which specific VoiceChannel object this client is connected to.

voice_client.play(source: discord.AudioSource, *, after=None):

FUNCTIONS

Sends audio data to Discord.
source: An object that provides audio data. For music, this is almost always an instance of discord.FFmpegPCMAudio (or similar like discord.PCMVolumeTransformer wrapping it).
after: An optional callback function that gets executed synchronously when the source finishes playing or when voice_client.stop() is called.
This callback receives one argument: an Exception object if playback failed, or None if it finished normally or was stopped.
Vital for queues: The after callback is where you typically trigger the logic to play the next song (often by scheduling your player loop coroutine using asyncio.create_task or bot.loop.call_soon_threadsafe).

voice_client.pause():
Pauses the current audio playback. is_playing() becomes False, is_paused() becomes True.
Does NOT trigger the after callback.

voice_client.resume():
Resumes paused audio playback. is_playing() becomes True, is_paused() becomes False.

voice_client.stop():
Completely stops the current audio playback. is_playing() becomes False.
DOES trigger the after callback. This is key! stop() signals the end of the current audio stream.

voice_client.disconnect(*, force=False):
Crucial: Disconnects the bot from the voice channel. The VoiceClient object becomes invalid after this. is_connected() will become False.
Set force=True if you want to bypass the standard cleanup (rarely needed).
"""

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
        self.playlist = []
        self.song_index = 0
        self.current_song = None
        self.lock = asyncio.Lock()

        self.intro_playlist = []
        self.was_playing_music = False

        self.voice_client = None

        self.goBack = False

    def isPlaying(self):
        return self.voice_client is not None

    async def add_song(self, info, start=0):
        async with self.lock:
            timestamp = time.time()
            self.playlist.append({'info': info, 'start': start, 'start_timestamp': timestamp, 'pause_timestamp': 0})

    async def pause(self):
        async with self.lock:
            if self.voice_client and self.voice_client.is_playing():
                self.voice_client.pause()

    async def resume(self):
        async with self.lock:
            if self.voice_client and self.voice_client.is_paused():
                self.voice_client.resume()

    async def reset(self):
        async with self.lock:
            if playlist.voice_client:
                playlist.voice_client.stop()
                playlist.playlist.clear()
                playlist.song_index = 0


    async def prev(self):
        # wenn paused oder is playing dann -1 zurück
        # wenn playlist finished also nichts spielt dann den letzten song nochmal also kein -1

        # 1. wenn ein song in der playlist dann resette den immer wieder
        # 2. wenn playlist finished dann spiel den letzten song wieder
        # 3. sonst spiel den vorherigen song
        # 4. wenn der erste song läuft

        async with self.lock:
            if self.voice_client:
                is_playing = self.voice_client.is_paused() or self.voice_client.is_playing()

                if is_playing:
                    if self.song_index == 0:
                        target_index = self.song_index - 1
                    else:
                        target_index = self.song_index - 2

                    self.song_index = target_index
                    self.voice_client.stop()

                # Nichts spielt gerade -> playlist finished ?
                else:
                    # ist überhaupt was in der playlist?
                    if len(self.playlist) > 0:
                        if self.song_index < len(self.playlist):
                            task_to_run = asyncio.create_task(self.play_song())


    async def next(self):
        async with self.lock:
            if self.voice_client and (self.voice_client.is_paused() or self.voice_client.is_playing()):
                self.voice_client.stop()

    async def play_next_song(self):
        async with self.lock:
            if len(self.intro_playlist) > 0:
                asyncio.create_task(self.play_song())
            else:
                next_index = self.song_index + 1

                if 0 <= next_index < len(self.playlist):
                    self.song_index = next_index
                    asyncio.create_task(self.play_song())

    async def play_song(self):
        async with self.lock:
            if self.voice_client and self.voice_client.is_connected() and not self.voice_client.is_playing() and not self.voice_client.is_paused():
                if len(self.intro_playlist) > 0:
                    url = self.intro_playlist.pop()
                    url = "https://rr4---sn-4g5edndr.googlevideo.com/videoplayback?expire=1745112897&ei=4foDaN7gFrGPi9oPrMqsqQM&ip=2003%3Af0%3A3f13%3A709%3A203c%3A4d22%3A29ec%3Adf5d&id=o-ADuDLj6Q39AQlx6tBhiGDzllp8pmhfz2Vwr2YZM9dcDG&itag=251&source=youtube&requiressl=yes&xpc=EgVo2aDSNQ%3D%3D&met=1745091297%2C&mh=Ka&mm=31%2C26&mn=sn-4g5edndr%2Csn-h0jelne7&ms=au%2Conr&mv=m&mvi=4&pl=37&rms=au%2Cau&gcr=de&initcwndbps=2462500&bui=AccgBcP-I7iMunWNslKxpWC7VJwLDBf192FLfV7H0FMEuOk8phsqJ-W6kLVA-DNmF2ArhJxAn6MWaA0w&vprv=1&svpuc=1&mime=audio%2Fwebm&ns=UxQ-yd3tH1M64yYzEkEVLNwQ&rqh=1&gir=yes&clen=5365282&dur=359.161&lmt=1714723233287726&mt=1745090921&fvip=5&keepalive=yes&lmw=1&c=TVHTML5&sefc=1&txp=2318224&n=WLwhV392eJXOVQ&sparams=expire%2Cei%2Cip%2Cid%2Citag%2Csource%2Crequiressl%2Cxpc%2Cgcr%2Cbui%2Cvprv%2Csvpuc%2Cmime%2Cns%2Crqh%2Cgir%2Cclen%2Cdur%2Clmt&lsparams=met%2Cmh%2Cmm%2Cmn%2Cms%2Cmv%2Cmvi%2Cpl%2Crms%2Cinitcwndbps&lsig=ACuhMU0wRQIgZRmPju7X5QNbkfvzlFLpLNqbK2dyTIfsPouBmqqF4J8CIQD4ySusEdLJE72sloNoF6W2rs1yfJdgiifiTspjsLe3Yw%3D%3D&sig=AJfQdSswRAIgE3u1Kf1P8riOPCsGN-q62SXZKXMDWE1HYh4cT0j70KICIA_V2b6IvUjqXHfEuyiCutDAxgtrHoJQnib9Rwwb6rKY"

                    ffmpeg_options = {
                        "before_options": f"-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 ",
                        "options": f"-vn -ss {220} -t {5}",
                    }
                    source = discord.FFmpegPCMAudio(url, **ffmpeg_options)
                    def after_playing(error):
                        asyncio.run_coroutine_threadsafe(self.play_next_song(), bot.loop)

                    try:
                        self.voice_client.play(source, after=after_playing)
                    except:
                        return
                else:
                    if self.song_index > len(self.playlist):
                        print("song index outside of playlist range. song_index: ", str(self.song_index) , " playlist len:" , str(len(self.playlist)))
                        return
                    #TODO try except
                    info = self.playlist[self.song_index]

                    if info is None:
                        return

                    start_time = 0
                    ffmpeg_options = {
                        "before_options": f"-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -ss {start_time}",
                        "options": "-vn",
                    }
                    source = discord.FFmpegPCMAudio(info['info']['url'], **ffmpeg_options)
                    def after_playing(error):
                        asyncio.run_coroutine_threadsafe(self.play_next_song(), bot.loop)

                    try:
                        self.voice_client.play(source, after=after_playing)
                    except:
                        return

    async def get_playlist_view(self):
        """Returns a formatted string list of the current playlist."""
        async with self.lock:
            if not self.playlist:
                return "The playlist is currently empty."

            output = ["**Current Playlist:**"]
            for index, song_data in enumerate(self.playlist):
                try:
                    # Safely get title, fallback to 'Unknown Title'
                    title = song_data.get('info', {}).get('title', 'Unknown Title')
                    # Safely get URL, fallback to 'No URL Found'
                    url = song_data.get('info', {}).get('url', 'No URL Found')

                    # Add marker for currently playing/selected song
                    marker = "  ▶️ " if index == self.song_index else "     "

                    output.append(f"{marker}{index}: {title}")
                    # Optionally include URL if needed for debugging, but maybe hide from users
                    # output.append(f"       URL: <{url}>") # URLs can be long!
                except Exception as e:
                    # Handle potential errors if song_data structure is unexpected
                    output.append(f"     {index}: Error processing song data - {e}")

            # Add message if index is out of bounds (playlist finished)
            if self.song_index >= len(self.playlist):
                 output.append("\n(End of playlist reached)")
            elif self.song_index == -1 and self.playlist:
                 output.append("\n(Playlist loaded, player idle)")

            return "\n".join(output)


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

    async with playlist.lock:
        if playlist.voice_client and playlist.voice_client.is_connected():
            await playlist.reset()
            await playlist.voice_client.disconnect()


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
        print("start download")
        info = await loop.run_in_executor(
            None,  # Use the default executor
            functools.partial(yt_dlp.YoutubeDL(ydl_opts).extract_info, url, download=False)
        )
        print("done download")
        await playlist.add_song(info)
        print("added to playlist")
        print(f"[{ctx.guild.id}] Finished info extraction for: {url}")

    except Exception as e:
        print(f"Error during info extraction: {e}")
        await ctx.message.add_reaction('❌')
        await ctx.send(f"Failed to get info for the URL. Error: {e}")
        return

    await ctx.message.add_reaction('✅') # Indicate success
    await ctx.send(f"Added **{info.get('title', 'Unknown Title')}** to the queue.")
    await playlist.play_song()


@bot.command()
async def reset(ctx):
    """Stops the current song."""
    global playlist, lock
    await playlist.reset()


@bot.command()
async def prev(ctx):
    """Skips to the next song."""
    global playlist, lock

    await playlist.prev()
    # await ctx.send("⏭️ Skipping to next song.")
    # await ctx.send("nothing to skip...")


@bot.command()
async def next(ctx):
    """Skips to the next song."""
    global playlist, lock

    await playlist.next()
    # await ctx.send("⏭️ Skipping to next song.")
    # await ctx.send("nothing to skip...")


@bot.command()
async def pause(ctx):
    """Pauses the audio."""
    global playlist, lock
    await playlist.pause()


@bot.command()
async def resume(ctx):
    """Resumes the audio."""
    global playlist, lock
    await playlist.resume()


@bot.command(name='show', aliases=['q', 'list', 'playlist'])
async def show_queue(ctx):
    """Shows the current song playlist."""
    global playlist # Change for per-guild later

    # Check if player exists and get view
    if playlist:
        playlist_str = await playlist.get_playlist_view()
    else:
        playlist_str = "Player not initialized." # Should ideally not happen with global

    # Discord limits message length, handle potentially long playlists
    if len(playlist_str) > 1990: # Leave some room for ```
        # Simple truncation, could implement pagination later
        playlist_str = playlist_str[:1900] + "\n... (playlist truncated)"

    # Send the formatted string in a code block for better alignment
    await ctx.send(f"```md\n{playlist_str}\n```")


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
            print("ell")
            playlist.intro_playlist.append("hello")
            if voice_client and playlist.voice_client.is_playing():
                playlist.voice_client.stop()
            else:
                await playlist.play_song()


@bot.command()
async def search(ctx, *, query: str):
    """!search [query] # Searches YouTube and returns the first video link."""
    if not query:
        await ctx.send(f"{ctx.author.mention}, please provide something to search for!")
        return

    await ctx.send(f"🔎 Searching YouTube for: `{query}`...")

    loop = asyncio.get_running_loop()

    search_ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'verbose': False,
        'noplaylist': True,  # Important to prevent searching playlists if query matches one
        "cookiefile": cookie_path,
        'default_search': 'ytsearch1', # Tell yt-dlp to search YouTube and get 1 result
        # Alternatively, you can prefix the query with 'ytsearch1:' later
    }

    try:
        # Prepare the yt-dlp instance and the blocking call
        # Using 'ytsearch1:' prefix is very explicit and reliable
        search_query = f"ytsearch1:{query}"
        # Use slightly different opts if needed, or reuse main ones if safe
        ydl_instance = yt_dlp.YoutubeDL(search_ydl_opts) # Or use the global ydl_opts if appropriate
        blocking_call = functools.partial(ydl_instance.extract_info, search_query, download=False)

        # --- Run the BLOCKING search in a separate thread ---
        print(f"[{ctx.guild.id}] Starting YT search for: {query}")
        result = await loop.run_in_executor(
            None,  # Use the default executor
            blocking_call
        )
        print(f"[{ctx.guild.id}] Finished YT search for: {query}")



        # --- Process the result ---
        if result and 'entries' in result and result['entries']:
            # ytsearch returns a playlist-like structure with 'entries'
            first_entry = result['entries'][0]
            video_url = first_entry.get('webpage_url') or first_entry.get('original_url') # Standard URL
            video_title = first_entry.get('title', 'Unknown Title')

            if video_url:
                await ctx.send(f"Found video: **{video_title}**\n{video_url}")

                info = await loop.run_in_executor(
                    None,  # Use the default executor
                    functools.partial(yt_dlp.YoutubeDL(ydl_opts).extract_info, video_url, download=False)
                )

                await playlist.add_song(info)
            else:
                # This shouldn't happen often if an entry is found
                await ctx.send(f"Found a result for `{query}`, but couldn't extract its URL.")
                print(f"Search result entry missing URL: {first_entry}")

        else:
            # No entries found
            await ctx.send(f"Sorry, couldn't find any YouTube video results for `{query}`.")

    except yt_dlp.utils.DownloadError as e:
        # Catch specific yt-dlp errors if possible
        await ctx.send(f"An error occurred while searching YouTube: Video may be private, unavailable, or the query failed.")
        print(f"yt-dlp search error for '{query}': {e}")
    except Exception as e:
        # Catch any other unexpected errors
        await ctx.send(f"An unexpected error occurred during the search.")
        print(f"Unexpected search error for '{query}': {e}")
        # Optionally log the full traceback here for debugging


# Run the bot
bot.run(TOKEN)