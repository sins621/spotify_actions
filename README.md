# Spotify Actions API

A Flask-based REST API that provides seamless control and interaction with the Spotify Web API, allowing users to manage their Spotify playback, search for songs, and manage queues programmatically.

## Tech Stack

- **Backend Framework**: Flask
- **Authentication**: OAuth 2.0 with Spotify API
- **Deployment**: Docker-ready
- **Dependencies Management**: pip with requirements.txt

## Features

- 🎵 **Current Playback Control**
  - Get currently playing track information
  - Skip to next track
  - View song and playlist details

- 🔍 **Search Functionality**
  - Search for tracks with smart query parsing
  - Automatic queue addition for found tracks

- 📋 **Queue Management**
  - Add tracks to queue via URI
  - View upcoming queue (up to 5 tracks)
  - Add tracks via direct Spotify links

- 🔐 **Secure Authentication**
  - OAuth 2.0 implementation
  - Automatic token refresh
  - State verification for security

## API Endpoints

- `GET /api/spotify/playing` - Get current playback information
- `GET /api/spotify/skip` - Skip to next track
- `GET /api/spotify/search?q={query}` - Search and queue a track
- `GET /api/spotify/queue` - View upcoming queue
- `POST /api/spotify/add_link` - Add track to queue via URI

## Setup

1. Clone the repository
2. Create a `.env` file with the following variables:
   ```
   SPOTIFY_SECRET=your_spotify_secret
   SPOTIFY_ID=your_spotify_client_id
   SPOTIFY_REDIRECT_URI=your_redirect_uri
   SPOTIFY_STATE=your_state_value
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   python wsgi.py
   ```
   Or using Docker:
   ```bash
   docker build -t spotify-actions .
   docker run -p 8000:8000 spotify-actions
   ```

## Required Spotify Scopes

- user-modify-playback-state
- user-read-currently-playing
- user-read-playback-state

## Contributing

Feel free to open issues and pull requests for any improvements or bug fixes.

## License

This project is open source and available under the MIT License.
