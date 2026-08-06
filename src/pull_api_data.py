"""
Pull ALL of your reachable personal Spotify data via the Web API into data/api/.

Uses the "Authorization Code" flow (user login). The FIRST run (and any run
after we add new permissions) opens a browser asking you to approve access;
a token is then cached in .cache so you won't be asked again.

Pulls:
  - your profile
  - top tracks & top artists over 4 weeks / 6 months / 1 year
  - your 50 most recently played tracks
  - your entire "Liked Songs" library (with the date each was saved)
  - your saved albums
  - the artists you follow
  - your playlists
Each is written as a CSV in data/api/ (git-ignored). It also writes
_field_samples.json: the raw, unedited API response for one track and one
artist, so you can see exactly which fields your app is allowed to receive.

Run with:  python src/pull_api_data.py
"""

import json
import logging
import os

import pandas as pd
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

# Spotipy prints a big traceback for every failed request. We handle failures
# ourselves (some playlists are simply off-limits), so quiet its logger.
logging.getLogger("spotipy").setLevel(logging.CRITICAL)

# All permissions we request. Adding to this list forces a re-approval.
SCOPES = " ".join(
    [
        "user-read-private",
        "user-top-read",
        "user-read-recently-played",
        "user-library-read",
        "user-follow-read",
        "playlist-read-private",
    ]
)

TIME_RANGES = {"4weeks": "short_term", "6months": "medium_term", "1year": "long_term"}

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "api")


def get_client():
    """Build an authenticated Spotify client (triggers login when needed)."""
    load_dotenv()
    auth = SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope=SCOPES,
        cache_path=os.path.join(PROJECT_ROOT, ".cache"),
    )
    return spotipy.Spotify(auth_manager=auth)


def paginate(sp, results):
    """Follow Spotify's 'next' links to collect every page of items."""
    items = results["items"]
    while results.get("next"):
        results = sp.next(results)
        items.extend(results["items"])
    return items


def track_fields(t):
    """Pull the useful fields out of a track object, safely."""
    return {
        "track": t.get("name"),
        "artist": ", ".join(a["name"] for a in t.get("artists", [])),
        "album": t.get("album", {}).get("name"),
        "release_date": t.get("album", {}).get("release_date"),
        "duration_ms": t.get("duration_ms"),
        "explicit": t.get("explicit"),
        # ISRC = global track ID. Our key for joining outside datasets later.
        "isrc": t.get("external_ids", {}).get("isrc"),
        "track_uri": t.get("uri"),
    }


def top_tracks_df(sp, time_range):
    items = sp.current_user_top_tracks(limit=50, time_range=time_range)["items"]
    return pd.DataFrame(
        {"rank": i + 1, **track_fields(t)} for i, t in enumerate(items)
    )


def artist_image(a):
    """First image URL for an artist, or None (genres/popularity are stripped)."""
    images = a.get("images") or []
    return images[0]["url"] if images else None


def top_artists_df(sp, time_range):
    items = sp.current_user_top_artists(limit=50, time_range=time_range)["items"]
    return pd.DataFrame(
        {
            "rank": i + 1,
            "artist": a.get("name"),
            "image_url": artist_image(a),
            "artist_uri": a.get("uri"),
        }
        for i, a in enumerate(items)
    )


def recently_played_df(sp):
    items = sp.current_user_recently_played(limit=50)["items"]
    return pd.DataFrame(
        {"played_at": it["played_at"], **track_fields(it["track"])} for it in items
    )


def saved_tracks_df(sp):
    items = paginate(sp, sp.current_user_saved_tracks(limit=50))
    return pd.DataFrame(
        {"added_at": it["added_at"], **track_fields(it["track"])} for it in items
    )


def saved_albums_df(sp):
    items = paginate(sp, sp.current_user_saved_albums(limit=50))
    return pd.DataFrame(
        {
            "added_at": it["added_at"],
            "album": it["album"].get("name"),
            "artist": ", ".join(a["name"] for a in it["album"].get("artists", [])),
            "release_date": it["album"].get("release_date"),
            "total_tracks": it["album"].get("total_tracks"),
            "album_uri": it["album"].get("uri"),
        }
        for it in items
    )


def followed_artists_df(sp):
    results = sp.current_user_followed_artists(limit=50)["artists"]
    items = results["items"]
    while results.get("next"):
        results = sp.next(results)["artists"]
        items.extend(results["items"])
    return pd.DataFrame(
        {
            "artist": a.get("name"),
            "image_url": artist_image(a),
            "artist_uri": a.get("uri"),
        }
        for a in items
    )


def playlists_df(sp):
    items = paginate(sp, sp.current_user_playlists(limit=50))
    return pd.DataFrame(
        {
            "name": p.get("name"),
            "owner": p.get("owner", {}).get("display_name"),
            "tracks_total": p.get("tracks", {}).get("total"),
            "public": p.get("public"),
            "playlist_uri": p.get("uri"),
        }
        for p in items
    )


def playlist_tracks_df(sp):
    """Walk every playlist and collect its tracks.

    Returns two tables:
      - tracks:        one row per (playlist, track) placement
      - track_artists: normalized one row per (track, artist), with artist IDs.
        A track can have several artists; this is the bridge table you JOIN on
        `track_uri` to credit every collaborator separately.
    """
    playlists = paginate(sp, sp.current_user_playlists(limit=50))
    track_rows = []
    artist_rows = []
    for p in playlists:
        name = p.get("name")
        owner = p.get("owner", {}).get("display_name")
        try:
            items = paginate(sp, sp.playlist_items(p["id"], limit=100))
        except Exception:  # editorial/other-owned playlists are off-limits
            print(f"  {str(name)[:38]:<38}  (skipped — not accessible)")
            continue
        kept = 0
        for pos, it in enumerate(items, start=1):
            # The track object is nested under "item" (older code used "track").
            t = it.get("item") or it.get("track")
            # Skip removed tracks (None) and podcast episodes (type != track).
            if not isinstance(t, dict) or t.get("type") != "track":
                continue
            track_rows.append(
                {
                    "playlist": name,
                    "playlist_owner": owner,
                    "position": pos,
                    "added_at": it.get("added_at"),
                    **track_fields(t),
                }
            )
            # One row per artist on this track (keeps IDs; no string splitting).
            for order, a in enumerate(t.get("artists", []), start=1):
                artist_rows.append(
                    {
                        "track_uri": t.get("uri"),
                        "artist_order": order,
                        "artist_id": a.get("id"),
                        "artist_name": a.get("name"),
                        "artist_uri": a.get("uri"),
                    }
                )
            kept += 1
        print(f"  {str(name)[:38]:<38} {kept:>4} tracks")

    tracks = pd.DataFrame(track_rows)
    # A track appears in many playlists, so dedupe pairs to one per (track, artist).
    track_artists = (
        pd.DataFrame(artist_rows)
        .drop_duplicates(subset=["track_uri", "artist_id"])
        .reset_index(drop=True)
    )
    return tracks, track_artists


def save(df, name):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"{name}.csv")
    df.to_csv(path, index=False)
    print(f"  saved {len(df):>4} rows -> data/api/{name}.csv")


def write_field_samples(sp):
    """Dump one raw track and one raw artist so you can inspect real fields."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    sample = {}
    saved = sp.current_user_saved_tracks(limit=1)["items"]
    if saved:
        sample["track_object"] = saved[0]["track"]
    top_artists = sp.current_user_top_artists(limit=1)["items"]
    if top_artists:
        sample["artist_object"] = top_artists[0]
    path = os.path.join(OUTPUT_DIR, "_field_samples.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sample, f, indent=2, ensure_ascii=False)
    print(f"  saved raw field samples -> data/api/_field_samples.json")
    if "track_object" in sample:
        print(f"  track fields available: {sorted(sample['track_object'].keys())}")
    if "artist_object" in sample:
        print(f"  artist fields available: {sorted(sample['artist_object'].keys())}")


if __name__ == "__main__":
    sp = get_client()
    me = sp.current_user()
    print(f"Logged in as: {me.get('display_name')} ({me.get('id')})\n")

    print("Top tracks & artists:")
    for label, time_range in TIME_RANGES.items():
        save(top_tracks_df(sp, time_range), f"top_tracks_{label}")
        save(top_artists_df(sp, time_range), f"top_artists_{label}")

    print("\nLibrary & activity:")
    save(recently_played_df(sp), "recently_played")
    save(saved_tracks_df(sp), "liked_songs")
    save(saved_albums_df(sp), "saved_albums")
    save(followed_artists_df(sp), "followed_artists")
    save(playlists_df(sp), "playlists")

    print("\nTracks inside each playlist (one request per playlist):")
    playlist_tracks, track_artists = playlist_tracks_df(sp)
    save(playlist_tracks, "playlist_tracks")
    save(track_artists, "track_artists")

    print("\nField inventory (what your app is actually allowed to receive):")
    write_field_samples(sp)

    print("\nDone. All CSVs are in data/api/ (git-ignored).")
