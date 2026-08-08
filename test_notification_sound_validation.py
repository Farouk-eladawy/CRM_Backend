import unittest
import notification_sound_validation as v


class TestNotificationSoundValidation(unittest.TestCase):
    def test_valid_minimal(self):
        ok, parsed = v.validate_notification_sound_prefs(
            {
                "version": 1,
                "profiles": {
                    "All": {
                        "message_new": {"enabled": True, "volume": 1, "source": {"type": "builtin", "id": "beep"}}
                    }
                },
            }
        )
        self.assertTrue(ok)
        self.assertEqual(parsed["version"], 1)

    def test_invalid_volume(self):
        ok, msg = v.validate_notification_sound_prefs(
            {"version": 1, "profiles": {"All": {"message_new": {"enabled": True, "volume": 2, "source": {"type": "builtin", "id": "beep"}}}}}
        )
        self.assertFalse(ok)
        self.assertIn("volume", msg.lower())

    def test_invalid_custom(self):
        ok, msg = v.validate_notification_sound_prefs(
            {"version": 1, "profiles": {"All": {"message_new": {"enabled": True, "volume": 1, "source": {"type": "custom", "dataUrl": "http://x"}}}}}
        )
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()

