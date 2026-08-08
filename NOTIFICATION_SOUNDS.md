# Dynamic Notification Sounds

## Overview
The dashboard supports dynamic notification sounds based on the currently selected location filter in Inbox.

Preferences are stored per user using:
- Backend key: `notification_sound_prefs_<user_id>` via `GET/POST /api/settings/<key>`
- Value: JSON schema `version: 1`

## Notification Categories
Current categories (extendable):
- `message_new`: A new incoming customer message detected via Inbox polling.
- `urgent_needs_help`: A new incoming customer message where the chat is flagged `needs_help=1`.
- `urgent_reminder_15m`: A reminder sound when `needs_help=1` and the chat is unattended for 15 minutes.
- `system_alert`: Reserved for future system/channel alerts.

## Filter Matching
Sounds are selected based on the user's current Inbox location filter:
- `All`: all chats
- `NeedHelp`: chats with `needs_help=1`
- `Hurghada/Cairo`: matches `Hurghada/Cairo` plus `Unknown`/empty
- `Sharm`, `Sales`, ...: exact match on `chat.location`

## Built-in Sounds
Built-in sounds are synthesized using Web Audio (no audio files required):
- `chime`
- `beep`
- `urgent`
- `none`

## Custom Sounds
Users can upload an `audio/*` file (max 1MB). It is stored as a DataURL in preferences under:
`source: { type: "custom", dataUrl: "data:audio/..." }`

## Adding a New Notification Category
1) Frontend:
   - Add the category id to `NOTIFICATION_CATEGORIES` in `notificationSounds.ts`.
   - Update the UI label mapping in `SettingsView.tsx`.
   - Trigger the category from `App.tsx` where events are detected.
2) Backend:
   - Add the category id to `ALLOWED_CATEGORIES` in `notification_sound_validation.py`.
3) Tests:
   - Extend `notificationSounds.test.ts`.
   - Extend `test_notification_sound_validation.py`.

## Adding a New Built-in Sound
1) Frontend:
   - Add the id to `BUILTIN_SOUNDS` in `notificationSounds.ts`.
   - Add the waveform pattern inside `playSoundProfile`.
2) Backend:
   - Add the id to `ALLOWED_BUILTIN` in `notification_sound_validation.py`.

