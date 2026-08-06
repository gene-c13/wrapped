"""
Load Spotify "Extended Streaming History" JSON into a clean pandas DataFrame.

Spotify gives you one or more files named like:
    Streaming_History_Audio_2023-2024_0.json
Each file is a big JSON list of play events. This script reads them all,
combines them, cleans them up, and adds a few handy columns so the rest of
the project can just ask for a ready-to-analyze table.

Run it directly to see a summary of whatever data it finds:
    python src/load_history.py
It uses your real export in data/ if present, otherwise the sample file.
"""

import glob
import json
import os

import pandas as pd

# Folders, relative to the project root (one level up from this file).
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SAMPLE_DATA_DIR = os.path.join(PROJECT_ROOT, "sample_data")

# Friendlier names for Spotify's very long column names.
COLUMN_RENAMES = {
    "master_metadata_track_name": "track",
    "master_metadata_album_artist_name": "artist",
    "master_metadata_album_album_name": "album",
    "spotify_track_uri": "track_uri",
}


def find_history_files(data_dir):
    """Return all streaming-history JSON files in a folder."""
    pattern = os.path.join(data_dir, "Streaming_History_Audio_*.json")
    return sorted(glob.glob(pattern))


def load_streaming_history(data_dir):
    """Read every history file in data_dir into one cleaned DataFrame."""
    files = find_history_files(data_dir)
    if not files:
        raise FileNotFoundError(f"No history files found in {data_dir}")

    # Read each JSON file (a list of dicts) and collect all the plays.
    all_plays = []
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            all_plays.extend(json.load(f))

    # Turn the list of dicts into a table.
    df = pd.DataFrame(all_plays)
    df = df.rename(columns=COLUMN_RENAMES)

    # Parse the timestamp string into a real datetime we can do math on.
    df["ts"] = pd.to_datetime(df["ts"], utc=True)

    # Keep only music: podcast episodes have no track name.
    df = df[df["track"].notna()].copy()

    # Add convenience columns for later analysis.
    df["minutes_played"] = df["ms_played"] / 60000
    df["hour"] = df["ts"].dt.hour
    df["day_of_week"] = df["ts"].dt.day_name()
    df["date"] = df["ts"].dt.date
    df["month"] = df["ts"].dt.strftime("%Y-%m")

    # Sort oldest-to-newest and reset the row numbers.
    df = df.sort_values("ts").reset_index(drop=True)
    return df


def print_summary(df):
    """Print a quick, human-readable overview of the listening data."""
    total_hours = df["minutes_played"].sum() / 60
    skip_rate = df["skipped"].mean() * 100 if "skipped" in df else float("nan")

    print(f"Plays (music only): {len(df)}")
    print(f"Date range:         {df['ts'].min().date()} to {df['ts'].max().date()}")
    print(f"Total listening:    {total_hours:.1f} hours")
    print(f"Skip rate:          {skip_rate:.1f}%")

    print("\nTop 5 artists by time played:")
    top_artists = (
        df.groupby("artist")["minutes_played"].sum().sort_values(ascending=False).head(5)
    )
    for artist, minutes in top_artists.items():
        print(f"  {artist:<20} {minutes:6.1f} min")

    print("\nTop 5 tracks by play count:")
    top_tracks = df["track"].value_counts().head(5)
    for track, count in top_tracks.items():
        print(f"  {track:<20} {count} plays")


if __name__ == "__main__":
    # Prefer the real export; fall back to the sample so this always runs.
    if find_history_files(REAL_DATA_DIR):
        data_dir = REAL_DATA_DIR
        print(f"Using your real export in: {data_dir}\n")
    else:
        data_dir = SAMPLE_DATA_DIR
        print(f"No real export yet — using the sample in: {data_dir}\n")

    df = load_streaming_history(data_dir)
    print_summary(df)
