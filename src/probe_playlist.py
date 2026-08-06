"""
Diagnostic: dump the RAW API response for one of your own playlists, so we can
see exactly what (if anything) Spotify returns for playlist contents.

Run with:  python src/probe_playlist.py
"""

import json
import os

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCOPES = "playlist-read-private user-read-private"

load_dotenv()
sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope=SCOPES,
        cache_path=os.path.join(PROJECT_ROOT, ".cache"),
    )
)

me = sp.current_user()["id"]

# Find the first playlist YOU own.
playlists = sp.current_user_playlists(limit=50)["items"]
mine = [p for p in playlists if p["owner"]["id"] == me]
if not mine:
    raise SystemExit("No playlists owned by you found in the first page.")

p = mine[0]
print(f"Probing your playlist: '{p['name']}'  (id: {p['id']})")
print(f"Playlist object 'tracks' field: {p.get('tracks')}\n")

# Ask for just the first few items.
resp = sp.playlist_items(p["id"], limit=5)
print(f"Response 'total': {resp.get('total')}")
print(f"Number of items returned: {len(resp.get('items', []))}\n")

items = resp.get("items", [])
if items:
    print("Raw structure of the FIRST item:")
    print(json.dumps(items[0], indent=2, ensure_ascii=False)[:2000])
else:
    print("No items returned at all.")
