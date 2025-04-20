from dataclasses import dataclass
from typing import Dict, List

@dataclass
class Song:
    url: str
    info: str
    start_time: int

class Playlist:
    def __init__(self):
        self.songs: List[Song] = []
        self.current_index = 0
        self.max_size: int = 100

    def add_song(self, song: Song):
        if len(self.songs) >= self.max_size:
            self.songs.pop(0)
        self.songs.append(song)

    def remove_song(self, idx):
        if len(self.songs) > idx and idx >= 0:
            self.songs.pop(idx)

    def delete_playlist(self):
        self.song = []

    def next_song(self):
        if self.songs:
            self.current_index = (self.current_index + 1) % len(self.songs)
        return self.get_current_song()

    def previous_song(self):
        if self.songs:
            self.current_index = (self.current_index -1) % len(self.songs)
        return self.get_current_song()

    def get_current_song(self):
        if self.songs:
            return self.songs[self.current_index]
        else:
            return None

    def print_playlist(self):
        for i, song in enumerate(self.songs):
            print(f"{i}. {song.info['title']}")

playlist = Playlist()

song = Song("youtube.com", "hello", 0)
playlist.add_song(song)
playlist.remove_song(10)

