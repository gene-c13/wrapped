"""
Quick check that our Spotify API credentials work.

Uses the "Client Credentials" flow: app-level access, no user login needed.
That's enough for public data like search, track/artist metadata, and genres.
Run it with:  python src/test_connection.py
"""

import os

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials

# 1. Load CLIENT_ID / CLIENT_SECRET from the .env file (which git ignores).
load_dotenv()
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

if not client_id or not client_secret:
    raise SystemExit(
        "Missing credentials. Copy .env.example to .env and fill in your keys."
    )

# 2. Authenticate. spotipy handles fetching and refreshing the access token.
auth = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth)

# 3. Do a simple search to prove the connection works.
results = sp.search(q="Bohemian Rhapsody Queen", type="track", limit=1)
track = results["tracks"]["items"][0]

print("Connection works! Example lookup:")
print(f"  Track:      {track['name']}")
print(f"  Artist:     {track['artists'][0]['name']}")
print(f"  Album:      {track['album']['name']}")

# .get() returns a default instead of crashing if the key is missing.
# (Some fields, like popularity, aren't always returned for newer apps.)
popularity = track.get("popularity", "N/A")
print(f"  Popularity: {popularity}/100")

# Genres live on the ARTIST object, not the track.
artist = sp.artist(track["artists"][0]["id"])
genres = ", ".join(artist.get("genres", [])) or "none listed"
print(f"  Genres:     {genres}")
