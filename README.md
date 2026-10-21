# Hockey Music Bot

Specification, control script, and song data for a Grok Bot that runs timed Spotify playback for hockey games.

Songs start at pre-set offsets so the hook lands within ~5–12 seconds. The operator drives everything from a six-button panel in chat (Short / Penalty / Break / Stop / Choose next / Start game).

## What you get
- `SPEC.md` — complete operating rules, selection logic, button behavior, clean-playlist rules, and song table
- `sp.py` — Spotify Web API controller (PKCE auth, play with `position_ms`, category picks, queue, startgame, earlier/later)
- `songs.json` — master list with start offsets, categories, clean-version swaps, penalty flags, and removals
- Supporting JSON files

## Setup for someone recreating it

1. Create a Spotify developer app (https://developer.spotify.com/dashboard). Set redirect URI to `http://127.0.0.1:8888/callback`. Add your account as a development-mode user.
2. Put your client ID in `config.json` (create the file; example below).
3. Clone this repo and run `python3 sp.py auth`. Approve the consent page. This writes `token.json` (keep private).
4. Open Spotify (web or desktop) on the computer that will feed the PA so it appears as an active Connect device.
5. Create a new Grok Bot and give it the contents of `SPEC.md` plus these instructions: "You control Spotify via the `sp.py` script on the shared computer. Use the six-button panel. Follow the rules in the spec."
6. At the start of each game, the bot (or you) runs `python3 sp.py startgame`.

### config.json example
```json
{
  "client_id": "your_spotify_client_id_here"
}
```

Optional: add `"device_id": "..."` to pin a specific Connect device.

## Notes
- Playback uses the Spotify Web API (`PUT /me/player/play` with `position_ms`). No clicking the desktop app.
- Playlist must stay clean (radio/clean edits). A few explicit tracks are allowed only for short/penalty by explicit operator approval.
- No auto-stop. Stop is immediate.
- Selection prefers unplayed songs this game that are also not in the last 25 plays.

This snapshot is from October 21, 2026. Start times for newer penalty songs are included; adjust via the audition flow if needed.
