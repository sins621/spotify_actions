import os

import json
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
        print(json.dumps(current_playback, indent=2))
        if current_playback:

            return {
                "song_link": current_playback["item"]["external_urls"]["spotify"],
                "playlist_link": current_playback["context"]["external_urls"][
                    "spotify"
                ],
                "artists": [
                    artist_data["name"]
                    for artist_data in current_playback["item"]["artists"]
                ],
                "song_name": current_playback["item"]["name"],
            }

    def skip_song(self):
        self.sp.next_track()
        return {"message": "Skipped Song"}

    def search(self, args):
        request = self.sp.search(q=args["q"], limit=1)
        song_data = request["tracks"]["items"][0]  # pyright:ignore
        self.add_to_queue(song_data["uri"])
        return {
            "song_name": song_data["name"],
            "artists": [artist_data["name"] for artist_data in song_data["artists"]],
        }

    def add_to_queue(self, url):
        if url:
            self.sp.add_to_queue(url)
