import yt_dlp
import os

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
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])

    print(f"Audio snippet saved as {output_file}")

# url = "https://www.youtube.com/watch?v=ZXZMIC-Z-XA&ab_channel=%C3%9Cst%C3%A2dKem%C3%A2nke%C5%9F%F0%9F%8F%B9"
# user_name = "984511687942094888"
# start = 4
# stop = 9
#
# download_audio_snippet(url, start, stop, user_name)