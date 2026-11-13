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

    def test_get_discord_webhook_url_none(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True), \
             mock.patch("pathlib.Path.is_file", return_value=False):
            self.assertIsNone(notifier.get_discord_webhook_url())

    def test_get_discord_webhook_url_from_env(self) -> None:
        valid_url = "https://discord.com/api/webhooks/12345/abcdef"
        with mock.patch.dict("os.environ", {"DISCORD_WEBHOOK_URL": valid_url}):
            self.assertEqual(notifier.get_discord_webhook_url(), valid_url)

    def test_valid_webhook_url_rejects_unsafe_chars(self) -> None:
        self.assertIsNone(notifier._valid_webhook_url('https://discord.com/api/webhooks/1"2'))
        self.assertIsNone(notifier._valid_webhook_url("https://discord.com/api/webhooks/1\nurl=bad"))
        self.assertIsNone(notifier._valid_webhook_url("https://evil.com/webhooks/123"))

    def test_send_discord_notification_no_url(self) -> None:
        with mock.patch("notifier.get_discord_webhook_url", return_value=None), \
             mock.patch("subprocess.Popen") as mock_popen:
            notifier.send_discord_notification("test message")
            mock_popen.assert_not_called()

    def test_send_discord_notification_with_url(self) -> None:
        valid_url = "https://discord.com/api/webhooks/12345/abcdef"
        mock_proc = mock.MagicMock()
        with mock.patch("notifier.get_discord_webhook_url", return_value=valid_url), \
             mock.patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            notifier.send_discord_notification("test message")
            mock_popen.assert_called_once()
            cmd = mock_popen.call_args[0][0]
            self.assertNotIn(valid_url, cmd)
            self.assertIn("-K", cmd)
            mock_proc.stdin.write.assert_called_once_with(f'url = "{valid_url}"\n'.encode("utf-8"))
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
