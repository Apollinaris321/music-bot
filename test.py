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




ydl_opts = {
    'format': 'bestaudio/best/worstaudio/worst',
    'quiet': True,
    'no_warnings': True,
    'verbose': False,
    'noplaylist': True,
}

url = "https://www.youtube.com/watch?v=bRU91WgnDbA&ab_channel=Klangkuenstler-Topic"
info = yt_dlp.YoutubeDL(ydl_opts).extract_info(url)
print(info['url'])

url = "https://rr4---sn-4g5edndr.googlevideo.com/videoplayback?expire=1745112897&ei=4foDaN7gFrGPi9oPrMqsqQM&ip=2003%3Af0%3A3f13%3A709%3A203c%3A4d22%3A29ec%3Adf5d&id=o-ADuDLj6Q39AQlx6tBhiGDzllp8pmhfz2Vwr2YZM9dcDG&itag=251&source=youtube&requiressl=yes&xpc=EgVo2aDSNQ%3D%3D&met=1745091297%2C&mh=Ka&mm=31%2C26&mn=sn-4g5edndr%2Csn-h0jelne7&ms=au%2Conr&mv=m&mvi=4&pl=37&rms=au%2Cau&gcr=de&initcwndbps=2462500&bui=AccgBcP-I7iMunWNslKxpWC7VJwLDBf192FLfV7H0FMEuOk8phsqJ-W6kLVA-DNmF2ArhJxAn6MWaA0w&vprv=1&svpuc=1&mime=audio%2Fwebm&ns=UxQ-yd3tH1M64yYzEkEVLNwQ&rqh=1&gir=yes&clen=5365282&dur=359.161&lmt=1714723233287726&mt=1745090921&fvip=5&keepalive=yes&lmw=1&c=TVHTML5&sefc=1&txp=2318224&n=WLwhV392eJXOVQ&sparams=expire%2Cei%2Cip%2Cid%2Citag%2Csource%2Crequiressl%2Cxpc%2Cgcr%2Cbui%2Cvprv%2Csvpuc%2Cmime%2Cns%2Crqh%2Cgir%2Cclen%2Cdur%2Clmt&lsparams=met%2Cmh%2Cmm%2Cmn%2Cms%2Cmv%2Cmvi%2Cpl%2Crms%2Cinitcwndbps&lsig=ACuhMU0wRQIgZRmPju7X5QNbkfvzlFLpLNqbK2dyTIfsPouBmqqF4J8CIQD4ySusEdLJE72sloNoF6W2rs1yfJdgiifiTspjsLe3Yw%3D%3D&sig=AJfQdSswRAIgE3u1Kf1P8riOPCsGN-q62SXZKXMDWE1HYh4cT0j70KICIA_V2b6IvUjqXHfEuyiCutDAxgtrHoJQnib9Rwwb6rKY"