"""Unit tests for history.py module."""
import json
import os
import tempfile
import unittest
from unittest.mock import patch, mock_open
import sys

# Add src to path so we can import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from history import (
    history_file_path,
    load_history,
    save_history,
    append_history,
    history_to_messages,
    parse_ai_commands
)


class TestHistory(unittest.TestCase):
    """Test cases for history management functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_history = [
            {"sender": "You", "message": "Hello", "timestamp": "2023-01-01T00:00:00"},
            {"sender": "Stapler-y", "message": "Hi there!", "timestamp": "2023-01-01T00:00:01"},
        ]

    def test_parse_ai_commands_json(self):
        """Test parsing JSON command format."""
        text = 'Here is my response. {"command": "jump", "args": {"height": 10}}'
        cmds = parse_ai_commands(text)
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0]["command"], "jump")
        self.assertEqual(cmds[0]["args"], {"height": 10})

    def test_parse_ai_commands_line(self):
        """Test parsing line-based command format."""
        text = "COMMAND: move_to x=100 y=200"
        cmds = parse_ai_commands(text)
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0]["command"], "move_to")
        self.assertEqual(cmds[0]["args"], {"x": "100", "y": "200"})

    def test_parse_ai_commands_slash(self):
        """Test parsing slash-style command format."""
        text = "/walk"
        cmds = parse_ai_commands(text)
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0]["command"], "walk")
        self.assertEqual(cmds[0]["args"], {})

    def test_parse_ai_commands_cmd_prefix(self):
        """Test parsing /cmd prefixed commands."""
        text = "/cmdjump height=5"
        cmds = parse_ai_commands(text)
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0]["command"], "jump")
        self.assertEqual(cmds[0]["args"], {"height": "5"})

    def test_parse_ai_commands_multiple(self):
        """Test parsing multiple commands in text (only first JSON is found)."""
        text = """First command: {"command": "sit"}
        Then another: COMMAND: stand
        And finally: /run"""
        cmds = parse_ai_commands(text)
        self.assertEqual(len(cmds), 1)  # Only finds the first JSON command
        self.assertEqual(cmds[0]["command"], "sit")

    def test_parse_ai_commands_empty(self):
        """Test parsing empty or no commands."""
        self.assertEqual(parse_ai_commands(""), [])
        self.assertEqual(parse_ai_commands("Just regular text"), [])
        self.assertEqual(parse_ai_commands("COMMAND:"), [])

    def test_history_to_messages(self):
        """Test converting history to message format."""
        messages = history_to_messages(self.test_history)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[0]["content"], "Hello")
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertEqual(messages[1]["content"], "Hi there!")

    def test_history_to_messages_skip_system(self):
        """Test that system messages are skipped."""
        history_with_system = self.test_history + [
            {"sender": "System", "message": "Some meta info", "timestamp": "2023-01-01T00:00:02"}
        ]
        messages = history_to_messages(history_with_system)
        self.assertEqual(len(messages), 2)  # System message should be excluded

    @patch('history.history_file_path')
    @patch('builtins.open', new_callable=mock_open, read_data='[]')
    def test_load_history_empty(self, mock_file, mock_path):
        """Test loading empty history."""
        mock_path.return_value = '/fake/path'
        history = load_history()
        self.assertEqual(history, [])

    @patch('history.history_file_path')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_history_with_data(self, mock_file, mock_exists, mock_path):
        """Test loading history with data."""
        mock_path.return_value = '/fake/path'
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = '[{"sender": "You", "message": "Hello", "timestamp": "2023-01-01T00:00:00"}, {"sender": "Stapler-y", "message": "Hi there!", "timestamp": "2023-01-01T00:00:01"}]'
        history = load_history()
        expected = [
            {"sender": "You", "message": "Hello", "timestamp": "2023-01-01T00:00:00"},
            {"sender": "Stapler-y", "message": "Hi there!", "timestamp": "2023-01-01T00:00:01"},
        ]
        self.assertEqual(history, expected)

    @patch('history.history_file_path')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_save_history(self, mock_makedirs, mock_file, mock_path):
        """Test saving history."""
        mock_path.return_value = '/fake/path'
        save_history(self.test_history)
        mock_file.assert_called_once_with('/fake/path', 'w', encoding='utf-8')
        # Verify write was called
        handle = mock_file()
        self.assertTrue(handle.write.called)


if __name__ == '__main__':
    unittest.main()