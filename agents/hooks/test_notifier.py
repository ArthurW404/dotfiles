#!/usr/bin/env python3
"""Unit tests for notifier.py lifecycle hook."""

from __future__ import annotations

import unittest
from unittest import mock

import notifier


class TestNotifier(unittest.TestCase):
    def test_stop_sound_completed(self) -> None:
        payload = {"fullyIdle": True, "terminationReason": "DONE"}
        self.assertEqual(notifier.stop_sound(payload), notifier.SOUND_DONE)

    def test_stop_sound_error(self) -> None:
        payload = {"fullyIdle": True, "terminationReason": "ERROR"}
        self.assertEqual(notifier.stop_sound(payload), notifier.SOUND_ERROR)

    def test_stop_sound_silent(self) -> None:
        payload = {"fullyIdle": True, "terminationReason": "USER_CANCELED"}
        self.assertIsNone(notifier.stop_sound(payload))

    def test_stop_sound_not_idle(self) -> None:
        payload = {"fullyIdle": False, "terminationReason": "DONE"}
        self.assertIsNone(notifier.stop_sound(payload))

    def test_get_discord_target_none(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True), \
             mock.patch("notifier._load_json_config", return_value={}):
            self.assertIsNone(notifier.get_discord_target())

    def test_get_discord_target_webhook_env(self) -> None:
        valid_url = "https://discord.com/api/webhooks/12345/abcdef"
        with mock.patch.dict("os.environ", {"DISCORD_WEBHOOK_URL": valid_url}, clear=True), \
             mock.patch("notifier._load_json_config", return_value={}):
            self.assertEqual(notifier.get_discord_target(), (valid_url, []))

    def test_get_discord_target_bot_channel(self) -> None:
        ch_id = "1165173417356558400"
        with mock.patch.dict("os.environ", {}, clear=True), \
             mock.patch("notifier._load_json_config", return_value={"channel_id": ch_id}), \
             mock.patch("notifier._load_bot_token", return_value="tok123"):
            target = notifier.get_discord_target()
            self.assertIsNotNone(target)
            url, headers = target
            self.assertEqual(url, f"https://discord.com/api/v10/channels/{ch_id}/messages")
            self.assertTrue(any("Authorization: Bot tok123" in h for h in headers))

    def test_sanitize_cfg_value_rejects_unsafe_chars(self) -> None:
        self.assertIsNone(notifier._sanitize_cfg_value('abc"def'))
        self.assertIsNone(notifier._sanitize_cfg_value("abc\nurl=bad"))
        self.assertIsNone(notifier._sanitize_cfg_value("abc\\def"))
        self.assertEqual(notifier._sanitize_cfg_value("  tok123  "), "tok123")

    def test_send_discord_notification_no_target(self) -> None:
        with mock.patch("notifier.get_discord_target", return_value=None), \
             mock.patch("subprocess.Popen") as mock_popen:
            self.assertFalse(notifier.send_discord_notification("test message"))
            mock_popen.assert_not_called()

    def test_send_discord_notification_with_target_hides_secrets_off_ps(self) -> None:
        valid_url = "https://discord.com/api/v10/channels/1165173417356558400/messages"
        headers = ['header = "Authorization: Bot secret-tok"']
        mock_proc = mock.MagicMock()
        with mock.patch("notifier.get_discord_target", return_value=(valid_url, headers)), \
             mock.patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            self.assertTrue(notifier.send_discord_notification("test message"))
            mock_popen.assert_called_once()
            cmd = mock_popen.call_args[0][0]
            self.assertNotIn(valid_url, cmd)
            self.assertNotIn("secret-tok", " ".join(cmd))
            self.assertIn("-K", cmd)
            written = mock_proc.stdin.write.call_args[0][0].decode("utf-8")
            self.assertIn(f'url = "{valid_url}"', written)
            self.assertIn('header = "Authorization: Bot secret-tok"', written)
            mock_proc.stdin.close.assert_called_once()

    def test_main_stop_clean_does_not_notify_discord(self) -> None:
        with mock.patch("sys.argv", ["notifier.py", "--event", "stop"]), \
             mock.patch("notifier.read_payload", return_value={"fullyIdle": True, "terminationReason": "DONE"}), \
             mock.patch("notifier.play_sound"), \
             mock.patch("notifier.send_discord_notification") as mock_discord:
            notifier.main()
            mock_discord.assert_not_called()

    def test_main_stop_error_notifies_discord(self) -> None:
        with mock.patch("sys.argv", ["notifier.py", "--event", "stop"]), \
             mock.patch("notifier.read_payload", return_value={"fullyIdle": True, "terminationReason": "ERROR"}), \
             mock.patch("notifier.play_sound"), \
             mock.patch("notifier.send_discord_notification") as mock_discord:
            notifier.main()
            mock_discord.assert_called_once()


if __name__ == "__main__":
    unittest.main()
