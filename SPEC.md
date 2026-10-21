# Hockey Music Bot: Specification

Snapshot taken Oct 21, 2026.

## 1. Purpose

The Hockey Music Bot runs game-day music at a hockey rink. It plays music through the user's Spotify account into the rink PA. Songs start on demand at a pre-set offset, so the hook or main hit lands within about 15 seconds. Most songs aim for 5 to 12 seconds. Music stops instantly when asked. The operator drives everything from a button panel in chat. Each tap runs one command, and the bot re-sends the panel after every action.

## 2. Spotify integration

- **Method:** The Spotify Web API controls a Spotify Connect device. The bot never clicks the desktop app or web player. Playback goes to whichever device is active on the account. A specific device can be pinned by adding `device_id` to `config.json`.
- **App:** The user owns a Spotify developer app named "Hockey Music Bot", running in development mode. Its client ID is in `config.json`.
- **Sign-in:** Authorization code with PKCE (no client secret). The redirect URI is `http://127.0.0.1:8888/callback`. Running `sp.py auth` prints the consent URL and listens on port 8888 for the callback.
- **Tokens:** `token.json` holds the access and refresh tokens and refreshes itself automatically.
- **Permissions (scopes):** `user-read-playback-state`, `user-modify-playback-state`, `user-read-currently-playing`, `playlist-read-private`, `playlist-modify-private`, and `playlist-modify-public`.
- **API calls used:**
  - Play: `PUT /me/player/play` with `{uris:[track], position_ms}`.
  - Pause: `PUT /me/player/pause`.
  - Status: `GET /me/player` and `GET /me/player/devices`.
  - Search: `GET /search?type=track`, capped at 10 results in dev mode.
  - Create a playlist: `POST /me/playlists`.
  - Add songs to a playlist: `POST /playlists/{id}/items`.
- **Dev-mode limits:**
  - Reading a playlist's track list through the API returns 403. To read track lists, the bot scrapes the public embed page (`open.spotify.com/embed/playlist/<id>`, the `__NEXT_DATA__` JSON), which also gives the `isExplicit` flag.
  - The audio-analysis endpoint isn't available.

## 3. Control script: `sp.py`

Run as `python3 sp.py <command>`.

| Command | Behavior |
|---|---|
| `auth` | Runs the PKCE sign-in and saves `token.json`. |
| `devices` / `now` | Lists Connect devices, or shows current playback. |
| `play <n or title> [m:ss]` | Plays a song by number or name. With no time given, it starts at the song's `start` field. |
| `stop` | Pauses immediately. |
| `cat short` / `cat medium` / `cat long` | Picks and plays a song from that category (see section 5). |
| `startgame` | Starts a new game: clears the played list in `game.json` and deletes `next.json`. |
| `queue <n or title>` | Lines up the next song in `next.json`. It plays on the next category tap. |
| `suggest [k]` | Prints k random songs not yet played this game (5 by default). |
| `preview <n> [long]` | Plays a song at its `short_start` (or `long_start` with `long`). Used for auditions. |
| `earlier [s]` / `later [s]` | Moves the last-played song's `short_start` by s seconds (3 by default, fractions allowed), saves it, and replays. |

**How names are matched:** Removed songs are skipped. A number picks that song directly. A name is tried as an exact title match, then as part of the alias or title, then as part of the title plus artist.

## 4. Data files

| File | Contents |
|---|---|
| `songs.json` | `{playlist, tracks:[...]}`, the master song list. |
| `game.json` | `{played:[n...], started}`, the songs played this game. |
| `next.json` | `{n}`, the queued next song, if any. |
| `recent.json` | The last 25 song URIs played, which avoids repeats across games. |
| `last_n` / `last_play` | The last song played, and a timestamp or "stopped" marker. |
| `audition.json` | The audition queue (currently empty). |
| `playlists.json` | The IDs of the three Hockey Game playlists. |
| `penalty_candidates.json` | The new penalty songs found by search. |
| `spdur.json`, `lrc.json`, `start_times.json`, `analysis.json` | Durations, timestamped lyrics, and start-time analysis results. |

**Song fields in `songs.json`:**
- **Identity:** `n`, `title`, `artist`, `sec`, `uri`, and an optional `alias`.
- **Clean-version flags:** `explicit`, plus `swapped` and `orig_uri` for clean-version swaps.
- **Start points:**
  - `start` is the legacy start point.
  - `short_start` is used by the Short and Penalty buttons.
  - `long_start` is used by the Break button.
- **Short-break fit:** `short_ok` says whether the song works for a whistle.
- **Analysis results:** `hit` is the estimated time of the hook, and `conf` is the confidence (high, med, or low).
- **Button categories:** `cats` holds any of `short`, `medium`, and `long`.
- **Other:** `removed`, `note`, and `penalty`.

## 5. Song selection

1. **Pool:** Songs whose `cats` include the category, minus explicit and removed songs. A song with no `cats` counts for every category.
2. **Queued song first:** If `next.json` exists, that song plays (shown as QUEUED) and the queue is cleared.
3. **Otherwise random:** The bot picks randomly from songs not played this game that also aren't in the last 25 plays. If that's empty, it drops the last-25 rule. If every song has been played this game, it picks from the whole pool and reports ALL-PLAYED-REPEAT.
4. **Logging:** The play is recorded in `game.json`, `recent.json`, and `last_n`.
5. **Start point:** `short` and `medium` use `short_start`. `long` uses `long_start`.
6. **No auto-stop:** Music never stops by itself. It plays until the operator taps Stop. The old auto-stop code is still there but switched off.
7. **In progress:** The Penalty button (`cat medium`) is being switched to pick only songs marked `penalty: true`.

## 6. Operator interface

The main panel has six buttons:
- **Short - Whistle** runs `cat short`.
- **Penalty - Medium** runs `cat medium`.
- **Break - Long** runs `cat long`.
- **Stop** runs `stop`.
- **Choose next song** runs `suggest 5` and shows those songs as choices. The operator can also type a title or number, which is then queued and plays on the next category tap at that category's start point.
- **Start game** runs `startgame`.

After every action, the bot reports what is playing (number, title, artist, and start time) and shows the panel again. Typed requests by name or number also work, such as "play Thunderstruck" or "play 12 from 0:45".

**Audition mode:** The bot works through `audition.json`. For each song it runs `preview`, then offers:
- **Earlier 3s** and **Later 3s** nudge the start point.
- **Good, next** sets `short_ok` to true and adds `short`.
- **Not for whistles** removes `short` and sets `short_ok` to false.
- **Stop** pauses.

The operator can also type an exact time ("try from 0:47") or "remove it". When the queue is done, the bot goes back to the main panel.

## 7. Rules

- Never auto-stop music, and stop instantly when asked.
- **The playlist must be clean:** no explicit language. Use clean or radio edits, swapping the URI and keeping `orig_uri`.
- **Approved exceptions to the clean rule:**
  - Killing In The Name and Bulls On Parade stay as originals, for whistle and penalty only, with no Break play.
  - Mother (Danzig) is back for all categories.
- **Kept off Break:** Firestarter has "bitch" at 1:29, so it never plays during long breaks.
- **Removed entirely:** Psycho (#26) and Fight the Power (#96).
- No song plays twice in a game.
- **Penalty songs** are about someone being wrong or naughty, or are fight songs.
- **Finding start times:**
  - Line up a YouTube copy of the song with the Spotify duration, find where the energy jumps, and check that against timestamped lyrics.
  - Aim for the hook landing 5 to 12 seconds after `short_start`.
  - Low-confidence songs get auditioned by the operator.

**Clean-version swaps in use:**

| # | Song | Clean version used |
|---|---|---|
| 17 | Sabotage | `3EyyhPW2GcLYuwV1MajRd6` |
| 21 | Freak On a Leash | `3ZZlPtyFBKiqqJpRNiCSF9` |
| 25 | Walk | `5y24oK62rEt4XdE3JDkyuh` |
| 54 | Free Bird | TOTEM Remix, `7ub59vgVaO2lr8aPLEyVcz` |
| 64 | Push It | Re-Recorded, `2OvyGP2JLi2zKc7ch7HCWf` |
| 74 | Barbra Streisand | Radio Edit, `782lNGn2rEHVn8JomdtRA7` |
| 76 | JUMPIN | `0qLrNIdgLhNw2sBEGqq1mY` |
| 77 | Boom Boom Boom | Radio Version, `3zg4stPJlbNSBPA8HJzLZA` |

## 8. Playlists (current state)

| Playlist | Spotify ID | State |
|---|---|---|
| Transitions (main source) | `1wdCSa5g5VGdDWtjhbQ0a2` | The original list. It's mirrored in `songs.json`. |
| Hockey Game - Penalties | `0SaJyUnsbCFSyI3dR0GxfR` | Populated with penalty songs. |
| Hockey Game - Short Transitions | `3IenKLPY2ycdx8k4WDCMDS` | Empty |
| Hockey Game - Long Breaks | `6FzPDtGmYli48L6g6mqaRS` | Empty |

The three Hockey Game playlists are private. Button selection still runs off `songs.json`, not off these Spotify playlists.

## 9. Master song list

See `songs.json` for the full list of 117 entries (including new penalty songs). Active clean songs are the primary pool. Categories, start times, confidence, and notes are stored per track.

## 10. Recreating the bot

1. Create a Spotify developer app with redirect URI `http://127.0.0.1:8888/callback`, and add the account as a dev-mode user.
2. Put the client ID in `config.json`, then run `sp.py auth` and approve the consent page.
3. Open Spotify (web player or desktop) on the PA computer so it shows up as an active Connect device.
4. Copy `songs.json` and `sp.py`, then run `startgame` at the start of each game.
5. Drive play with the six-button panel, following the rules in section 7.
