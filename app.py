import base64
import json
import os
from datetime import datetime, timedelta
from urllib.parse import urlencode
from functools import wraps

import spotipy
from dotenv import load_dotenv
from flask import Blueprint, Flask, jsonify, redirect, request
from requests import post

load_dotenv()

app = Flask(__name__)
spotify_bp = Blueprint("spotify", __name__, url_prefix="/api/spotify")

SPOTIFY_SECRET = os.getenv("SPOTIFY_SECRET")
SPOTIFY_ID = os.getenv("SPOTIFY_ID")
SCOPES = (
    "user-modify-playback-state user-read-currently-playing user-read-playback-state"
)
REDIRECT_URI = os.getenv(
    "SPOTIFY_REDIRECT_URI", "http://localhost:8000/api/spotify/auth_redirect"
)
STATE = os.getenv("SPOTIFY_STATE", "some-state-value")
sp = None
refresh_token = None
expire_time = None


def spotify_auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        global sp, expire_time

        if not sp:
            return jsonify({"error": "Please Authenticate Spotify"}), 400

        if expire_time and expire_time < datetime.now():
            refresh_spotify()

        try:
            return f(*args, **kwargs)
        except spotipy.SpotifyException as e:
            return jsonify({"error": f"Spotify Error: {str(e)}"}), 500

    return decorated_function


def refresh_spotify():
    global refresh_token, expire_time, sp
    refresh_url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic "
        + base64.b64encode(f"{SPOTIFY_ID}:{SPOTIFY_SECRET}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "refresh_token", "refresh_token": refresh_token}

    try:
        token_response = post(refresh_url, headers=headers, data=data).json()
    except Exception as e:
        return None, f"Token request failed: {e}"

    if "refresh_token" in token_response:
        print(json.dumps(token_response, indent=2))
        access_token = token_response["access_token"]
        expires_in = int(token_response["expires_in"])
        refresh_token = token_response["refresh_token"]
        expire_time = datetime.now()
        expire_time += timedelta(0, expires_in)
        sp = spotipy.Spotify(auth=access_token)
    else:
        print("No refresh token in response")


def authenticate_spotify(code, state):
    if not code or state != STATE:
        return None, "Authorization failed."

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

    try:
        token_response = post(token_url, headers=headers, data=data).json()
    except Exception as e:
        return None, f"Token request failed: {e}"

    if "access_token" in token_response:
        access_token = token_response["access_token"]
        expires_in = int(token_response["expires_in"])

        global refresh_token, expire_time
        refresh_token = token_response["refresh_token"]
        expire_time = datetime.now()
        expire_time += timedelta(0, expires_in)
        return spotipy.Spotify(auth=access_token), None
    else:
        return None, f"Token retrieval failed: {token_response}"


@spotify_bp.route("/")
@spotify_auth_required
def home():
    return "Hello"


@spotify_bp.route("/authenticate")
def authenticate():
    auth_url = "https://accounts.spotify.com/authorize?" + urlencode(
        {
            "response_type": "code",
            "client_id": SPOTIFY_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "state": STATE,
        }
    )
    return redirect(auth_url, 302)


@spotify_bp.route("/auth_redirect")
def auth_redirect():
    code = request.args.get("code")
    state = request.args.get("state")

    global sp
    sp, error_message = authenticate_spotify(code, state)

    if sp:
        return "Spotify Authenticated Successfully"
    else:
        return jsonify({"error": error_message}), 400


@spotify_bp.route("/now_playing")
@spotify_auth_required
def now_playing():
    current_playback = sp.current_playback() #pyright: ignore
    if current_playback and current_playback.get("item"):
        item = current_playback["item"]
        context = current_playback.get("context", {})
        return jsonify(
            {
                "song_link": item["external_urls"]["spotify"],
                "playlist_link": (
                    context.get("external_urls", {}).get("spotify") if context else None
                ),
                "artists": [artist_data["name"] for artist_data in item["artists"]],
                "song_name": item["name"],
            }
        )
    else:
        return (
            jsonify({"message": "No song is currently playing."}),
            204,
        )


@spotify_bp.route("/skip_song")
@spotify_auth_required
def skip_song():
    sp.next_track() #pyright: ignore
    return jsonify({"message": "Skipped Song"})


@spotify_bp.route("/search")
@spotify_auth_required
def search():

    query = request.args.get("q")
    if not query:
        return jsonify({"error": "Search query is required."}), 400

    response = sp.search(q=query, limit=1, market="ZA") #pyright: ignore
    print(json.dumps(response, indent=2))
    items = response.get("tracks", {}).get("items", []) # pyright: ignore
    if items:
        song_data = items[0]
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
        return jsonify({"message": "No results found."}), 404


@spotify_bp.route("/add", methods=["POST"])
@spotify_auth_required
def add_to_queue_route():

    data = request.get_json()
    if not data or "uri" not in data:
        return jsonify({"error": "Track URI is required in the request body."}), 400

    uri = data["uri"]
    return add_to_queue(uri)


def add_to_queue(uri):
    if sp:
        try:
            sp.add_to_queue(uri)
            return jsonify({"message": "Successfully added to queue"})
        except spotipy.SpotifyException as e:
            return (
                jsonify({"error": f"Error adding to queue: {e}"}),
                500,
            )
    else:
        return jsonify({"error": "Please Authenticate Spotify"}), 400


app.register_blueprint(spotify_bp)
