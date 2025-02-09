import os

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()


class SpotifyActions:
    SPOTIFY_SECRET = os.getenv("SPOTIFY_SECRET")
    SPOTIFY_ID = os.getenv("SPOTIFY_ID")
    SCOPES = "user-modify-playback-state user-read-currently-playing user-read-playback-state"

    auth_manager = SpotifyOAuth(
        client_secret=SPOTIFY_SECRET,
        client_id=SPOTIFY_ID,
        redirect_uri="http://localhost:3000/spotify_auth",
        scope=SCOPES,
    )

    sp = spotipy.Spotify(auth_manager=auth_manager)

    def now_playing(self):
        current_playback = self.sp.current_playback()
        if current_playback:
            return {
                "song": current_playback["item"]["external_urls"]["spotify"],
                "playlist": current_playback["context"]["external_urls"]["spotify"],
            }

    def skip_song(self):
        self.sp.next_track()

    def add_to_queue(self, uri):
        if uri:
            self.sp.add_to_queue(uri)
