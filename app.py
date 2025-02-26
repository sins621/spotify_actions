import base64
import json
import os
from datetime import datetime, timedelta
from urllib.parse import urlencode
from functools import wraps

from dotenv import load_dotenv
from flask import Blueprint, Flask, jsonify, redirect, request
from requests import post, get

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
SPOTIFY_URL = "https://accounts.spotify.com/api/token"

sp = None
access_token = None
refresh_token = None
expire_time = None


def spotify_auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if expire_time and expire_time < datetime.now():
            refresh_spotify()

        try:
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": f"Spotify Error: {str(e)}"}), 500

    return decorated_function


def set_access_token(url, headers, data):
    global access_token, refresh_token, expire_time
    try:
        token_response = post(url, headers=headers, data=data).json()
    except Exception as e:
        return None, f"Token request failed: {e}"

    if "access_token" in token_response:
        access_token = token_response["access_token"]
        if "expires_in" in token_response:
            expires_in = int(token_response["expires_in"])
            expire_time = datetime.now()
            expire_time += timedelta(0, expires_in)

        if "refresh_token" in token_response:
            refresh_token = token_response["refresh_token"]
    else:
        return None, f"Token retrieval failed: {token_response}"


def refresh_spotify():
    global refresh_token, expire_time, sp
    headers = {
        "Authorization": "Basic "
        + base64.b64encode(f"{SPOTIFY_ID}:{SPOTIFY_SECRET}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    set_access_token(SPOTIFY_URL, headers, data)


def authenticate_spotify(code, state):
    if not code or state != STATE:
        return None, "Authorization failed."

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

    set_access_token(SPOTIFY_URL, headers, data)


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
    global access_token
    code = request.args.get("code")
    state = request.args.get("state")
    authenticate_spotify(code, state)

    if access_token:
        return "Spotify Authenticated Successfully"
    else:
        return jsonify({"error": "Error Authenticating"}), 400


@spotify_bp.route("/")
@spotify_auth_required
def home():
    return "Hello"


@spotify_bp.route("/now_playing")
@spotify_auth_required
def now_playing():
    ENDPOINT = "https://api.spotify.com/v1/me/player/currently-playing"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = get(ENDPOINT, headers=headers, params={"market": "AF"})
    current_playback = response.json()
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
    ENDPOINT = "https://api.spotify.com/v1/me/player/next"
    headers = {"Authorization": f"Bearer {access_token}"}
    post(ENDPOINT, headers=headers)
    return jsonify({"message": "Skipped Song"})


@spotify_bp.route("/search")
@spotify_auth_required
def search():
    query = request.args.get("q")
    if not query:
        return jsonify({"error": "Search query is required."}), 400
    q = query.replace("by", "").title()

    params = {"q": q, "limit": 1, "market": "ZA", "type": "track", "offset": 0}
    ENDPOINT = "https://api.spotify.com/v1/search"
    headers = {"Authorization": f"Bearer {access_token}"}
    get_request = get(ENDPOINT, headers=headers, params=params)
    get_request.raise_for_status()
    response = get_request.json()
    items = response.get("tracks", {}).get("items", [])
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
    try:
        ENDPOINT = "https://api.spotify.com/v1/me/player/queue"
        headers = {"Authorization": f"Bearer {access_token}"}
        post(ENDPOINT, headers=headers, params={"uri": uri})
        return jsonify({"message": "Successfully added to queue"})
    except Exception as e:
        return (
            jsonify({"error": f"Error adding to queue: {e}"}),
            500,
        )


app.register_blueprint(spotify_bp)
