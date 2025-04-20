import os
import yt_dlp



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
