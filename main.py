import base64
import json
import os
from urllib.parse import urlencode

import spotipy
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, request
from requests import post

load_dotenv()

app = Flask(__name__)
ENDPOINT = "/api/spotify"

SPOTIFY_SECRET = os.getenv("SPOTIFY_SECRET")
SPOTIFY_ID = os.getenv("SPOTIFY_ID")
SCOPES = (
    "user-modify-playback-state user-read-currently-playing user-read-playback-state"
)
REDIRECT_URI = f"http://localhost:3000{ENDPOINT}/auth_redirect"

sp = None


@app.route(f"{ENDPOINT}/authenticate")
def authenticate():
    auth_url = "https://accounts.spotify.com/authorize?" + urlencode(
        {
            "response_type": "code",
            "client_id": SPOTIFY_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "state": "some-state-value",
        }
    )
    return redirect(auth_url, 302)


@app.route(f"{ENDPOINT}/auth_redirect")
def auth_redirect():
    code = request.args.get("code")
    state = request.args.get("state")

    if not code or state != "some-state-value":
        return jsonify({"error": "Authorization failed."}), 400

    token_url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic "
        + base64.b64encode(f"{SPOTIFY_ID}:{SPOTIFY_SECRET}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    token_response = post(token_url, headers=headers, data=data).json()

    if "access_token" in token_response:
        access_token = token_response["access_token"]
        global sp
        sp = spotipy.Spotify(auth=access_token)
        return "Spotify Authenticated Successfully"

    else:
        return (
            jsonify({"error": "Token retrieval failed.", "details": token_response}),
            400,
        )


@app.route(f"{ENDPOINT}/now_playing")
def now_playing():
    if sp:
        current_playback = sp.current_playback()
        print(json.dumps(current_playback, indent=2))
        if current_playback:
            return jsonify(
                {
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
            )
        else:
            return ""
    else:
        return jsonify({"error": "Please Authenticate Spotify"}), 400


@app.route(f"{ENDPOINT}/skip_song")
def skip_song():
    if sp:
        sp.next_track()
        return jsonify({"message": "Skipped Song"})
    else:
        return jsonify({"error": "Please Authenticate Spotify"}), 400


@app.route(f"{ENDPOINT}/search")
def search():
    if sp:
        response = sp.search(q=request.args.get("q"), limit=1)
        song_data = response["tracks"]["items"][0]  # pyright:ignore
        add_to_queue(song_data["uri"])
        return jsonify(
            {
                "song_name": song_data["name"],
                "artists": [
                    artist_data["name"] for artist_data in song_data["artists"]
                ],
            }
        )
    else:
        return jsonify({"error": "Please Authenticate Spotify"}), 400


@app.route(f"{ENDPOINT}/add")
def add_to_queue(url):
    if sp:
        if url:
            sp.add_to_queue(url)
        return jsonify({"ok": "successfully added to que"})
    else:
        return jsonify({"error": "Please Authenticate Spotify"}), 400


if __name__ == "__main__":
    app.run(debug=True, port=3000)
