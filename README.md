# Wrapped

A personal, more comprehensive version of Spotify Wrapped — built from my own
Spotify data as a project to learn ML concepts and Python.

## Goals
- Analyze my listening history (stats, trends, moods over time)
- Learn core ML ideas hands-on: clustering, classification, recommendation
- Build toward a playlist recommender

## Data sources
1. **Extended streaming history** — full play-by-play export from Spotify
   (Privacy Settings → request "Extended streaming history"). Lives in `data/`
   (git-ignored, never committed).
2. **Spotify Web API** — audio features (energy, valence, tempo…) and genres
   per track.

## Project structure
```
wrapped/
├── data/          # raw Spotify export + API pulls (git-ignored)
├── notebooks/     # exploration and analysis
├── src/           # reusable Python code
└── README.md
```

## Status
🚧 Just getting started — setting up the repo and requesting my data export.
# wrapped
