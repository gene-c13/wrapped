# Wrapped — Spotify Playlist Analysis

A data analysis of my music taste, built from the songs I've collected across my
Spotify playlists. Tracks are pulled from the Spotify Web API and explored in a
Jupyter notebook using pandas, matplotlib, and seaborn.

**▶ [View the analysis](https://gene-c13.github.io/wrapped/)** *(live once GitHub Pages is enabled)*

## What it looks at

- Most common artists and which ones reach across the most playlists
- Distributions of song length, release year, and decade
- Playlist personality: eclecticism (era spread), explicit ratio, artist concentration
- Curation habits: library growth over time, and which days/hours I add songs

## Data

Data is pulled from the Spotify Web API — my playlists and the tracks inside them —
by `src/pull_api_data.py`, which writes CSVs to `data/api/`. A normalized
`track_artists` table maps each song to its individual artists (so collaborations
are credited to everyone).

Spotify no longer exposes genre or audio-feature data to newly-created API apps,
so this analysis focuses on library structure and metadata rather than sonic
qualities. Personal data (`data/`) and credentials (`.env`) are git-ignored and
never committed.

## Tech

Python · pandas · matplotlib · seaborn · spotipy · Jupyter

## Running it yourself

1. Create an app at [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard),
   then copy your Client ID/Secret into a `.env` file (see `.env.example`).
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Pull your data (opens a browser once to authorize):
   ```
   make data          # or: python src/pull_api_data.py
   ```
4. Open the notebook:
   ```
   jupyter notebook notebooks/playlist_analysis.ipynb
   ```
5. (Optional) Export the static site for GitHub Pages:
   ```
   make site          # notebooks/playlist_analysis.ipynb -> docs/index.html
   ```

## Project structure

```
wrapped/
├── notebooks/
│   └── playlist_analysis.ipynb   # the analysis
├── src/
│   ├── pull_api_data.py          # Spotify Web API -> data/api/*.csv
│   └── load_history.py           # loader for the extended-streaming-history export
├── sample_data/                  # small sample for the history loader
├── docs/                         # exported static site (GitHub Pages)
├── requirements.txt
└── Makefile
```
