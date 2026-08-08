import json
import os
import tempfile
import time
import unittest

from runtime.pi_brain.background_task_engine import BackgroundTaskEngine


class TestableBackgroundTaskEngine(BackgroundTaskEngine):
    def _load_config(self):
        return {}


class InternalMediatorScheduleTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.user_dir = os.path.join(self.temp_dir.name, "users", "u_test_user")
        self.outbox_dir = os.path.join(self.user_dir, "bridge", "outbox")
        self.inbox_dir = os.path.join(self.user_dir, "bridge", "inbox")
        self.tasks_dir = os.path.join(self.user_dir, "management", "scheduled_tasks")
        os.makedirs(self.outbox_dir, exist_ok=True)
        os.makedirs(self.inbox_dir, exist_ok=True)
        os.makedirs(self.tasks_dir, exist_ok=True)

        self.engine = TestableBackgroundTaskEngine(pi_brain_dir=self.temp_dir.name, check_interval=1)
        self.sent_notifications = []
        self.engine._send_whatsapp_notification = lambda phone, text: self.sent_notifications.append((phone, text)) or True

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_process_outbox_uses_action_phone_for_notifications(self):
        manifest = {
            "manifest_id": "man_notify_phone_override",
            "intent": "test_notification",
            "actions": [
                {
                    "type": "send_internal_notification",
                    "phone": "201010323484",
                    "payload": {
                        "message": "hello from scheduled manifest",
                    },
                }
            ],
        }
        manifest_path = os.path.join(self.outbox_dir, "man_notify_phone_override.json")
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, ensure_ascii=False, indent=2)

        self.engine.process_outbox(self.user_dir)

        self.assertEqual(len(self.sent_notifications), 1)
        self.assertEqual(self.sent_notifications[0][0], "201010323484")
        self.assertIn("hello from scheduled manifest", self.sent_notifications[0][1])

    def test_check_scheduled_tasks_sends_prealert_once(self):
        task = {
            "task_id": "dynamic_schedule_test",
            "execute_timestamp": time.time() + 5,
            "pre_alert_seconds": 30,
            "pre_alert_sent": False,
            "pre_alert_message": "pre alert message",
            "notify_phone": "201010323484",
            "action_to_execute": {
                "type": "send_internal_notification",
                "phone": "201010323484",
                "payload": {"message": "due message"},
            },
            "repeat": "daily",
        }
        task_path = os.path.join(self.tasks_dir, "dynamic_schedule_test.json")
        with open(task_path, "w", encoding="utf-8") as fh:
            json.dump(task, fh, ensure_ascii=False, indent=2)

        self.engine.check_scheduled_tasks(self.user_dir)
        self.assertEqual(self.sent_notifications, [("201010323484", "pre alert message")])

        with open(task_path, "r", encoding="utf-8") as fh:
            saved = json.load(fh)
        self.assertTrue(saved.get("pre_alert_sent"))
        self.assertEqual(os.listdir(self.outbox_dir), [])

    def test_check_scheduled_tasks_repeats_daily_after_execution(self):
        task = {
            "task_id": "dynamic_schedule_repeat",
            "execute_timestamp": time.time() - 3,
            "pre_alert_seconds": 60,
            "pre_alert_sent": True,
            "pre_alert_message": "pre alert message",
            "notify_phone": "201010323484",
            "action_to_execute": {
                "type": "send_internal_notification",
                "phone": "201010323484",
                "payload": {"message": "due message"},
            },
            "repeat": "daily",
        }
        task_path = os.path.join(self.tasks_dir, "dynamic_schedule_repeat.json")
        with open(task_path, "w", encoding="utf-8") as fh:
            json.dump(task, fh, ensure_ascii=False, indent=2)

        self.engine.check_scheduled_tasks(self.user_dir)

        outbox_files = os.listdir(self.outbox_dir)
        self.assertEqual(len(outbox_files), 1)
        with open(os.path.join(self.outbox_dir, outbox_files[0]), "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
        self.assertEqual(manifest.get("intent"), "scheduled_task_execution")

        with open(task_path, "r", encoding="utf-8") as fh:
            saved = json.load(fh)
        self.assertGreater(float(saved.get("execute_timestamp") or 0), time.time())
        self.assertFalse(saved.get("pre_alert_sent"))


if __name__ == "__main__":
    unittest.main()
