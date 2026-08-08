import json

ALLOWED_CATEGORIES = {"message_new", "urgent_needs_help", "urgent_reminder_15m", "system_alert"}
ALLOWED_BUILTIN = {"chime", "beep", "urgent", "none"}


def validate_notification_sound_prefs(val):
    parsed = val
    if isinstance(val, str) and val.strip():
        try:
            parsed = json.loads(val)
        except Exception:
            return False, "Invalid JSON for notification sound preferences"

    if not isinstance(parsed, dict) or parsed.get("version") != 1 or not isinstance(parsed.get("profiles"), dict):
        return False, "Invalid notification sound preferences schema"

    profiles = parsed.get("profiles") or {}
    for _, cat_map in profiles.items():
        if cat_map is None:
            continue
        if not isinstance(cat_map, dict):
            return False, "Invalid profiles map"
        for cat, prof in cat_map.items():
            if cat not in ALLOWED_CATEGORIES:
                continue
            if not isinstance(prof, dict):
                return False, "Invalid sound profile"
            if "volume" in prof:
                v = prof.get("volume")
                if not isinstance(v, (int, float)) or v < 0 or v > 1:
                    return False, "Invalid volume value"
            src = prof.get("source")
            if not isinstance(src, dict):
                return False, "Invalid sound source"
            st = src.get("type")
            if st == "builtin":
                if src.get("id") not in ALLOWED_BUILTIN:
                    return False, "Invalid builtin sound id"
            elif st == "custom":
                data_url = src.get("dataUrl")
                remote_url = src.get("url")
                has_data_url = isinstance(data_url, str) and data_url.startswith("data:audio/")
                has_remote_url = isinstance(remote_url, str) and remote_url.startswith(("http://", "https://"))
                if not has_data_url and not has_remote_url:
                    return False, "Invalid custom audio data"
                if has_data_url and len(data_url) > 2_000_000:
                    return False, "Custom audio file too large"
            else:
                return False, "Invalid sound source type"

    return True, parsed
