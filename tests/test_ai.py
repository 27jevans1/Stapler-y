"""Unit tests for ai.py module."""
import json
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path so we can import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai import (
    get_response,
    _fallback_response,
    _build_messages
)


class TestAI(unittest.TestCase):
    """Test cases for AI response functions."""

    def test_fallback_response_hello(self):
        """Test fallback response for hello prompts."""
        response = _fallback_response("hello")
        self.assertIn(response, [
            "Hey there! Need some help?",
            "Hello! Ready when you are.",
        ])

    def test_fallback_response_who_are_you(self):
        """Test fallback response for identity prompts."""
        response = _fallback_response("who are you")
        self.assertIn(response, [
            "Hello, I'm Stapler-y, your personal AI Assistant!",
            "Hi! I'm Stapler-y.",
        ])

    def test_fallback_response_empty(self):
        """Test fallback response for empty prompt."""
        response = _fallback_response("")
        self.assertEqual(response, "Say something and I'll try to help!")

    def test_fallback_response_unknown(self):
        """Test fallback response for unknown prompts."""
        response = _fallback_response("some random text")
        self.assertTrue(response.startswith("I heard: 'some random text'"))

    def test_fallback_response_long_prompt(self):
        """Test fallback response truncates long prompts."""
        long_prompt = "a" * 250
        response = _fallback_response(long_prompt)
        self.assertTrue("..." in response)
        self.assertTrue(len(response) < 250)

    def test_build_messages_basic(self):
        """Test building messages without history."""
        messages = _build_messages("Hello", None, None, None)
        self.assertEqual(len(messages), 2)  # system + user
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[1]["content"], "Hello")

    def test_build_messages_with_history(self):
        """Test building messages with conversation history."""
        history = [
            {"sender": "You", "message": "Hi"},
            {"sender": "Stapler-y", "message": "Hello!"},
        ]
        messages = _build_messages("How are you?", history, None, None)
        self.assertEqual(len(messages), 4)  # system + history user + history assistant + current user
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[1]["content"], "Hi")
        self.assertEqual(messages[2]["role"], "assistant")
        self.assertEqual(messages[2]["content"], "Hello!")
        self.assertEqual(messages[3]["role"], "user")
        self.assertEqual(messages[3]["content"], "How are you?")

    def test_build_messages_with_screen_context(self):
        """Test building messages with screen context."""
        screen_context = "Screen shows a browser window"
        messages = _build_messages("What's on screen?", None, screen_context, None)
        self.assertEqual(len(messages), 2)
        expected_content = "What's on screen?\n\nScreen shows a browser window"
        self.assertEqual(messages[1]["content"], expected_content)

    def test_build_messages_with_image(self):
        """Test building messages with base64 image."""
        screen_b64 = "base64imagedata"
        messages = _build_messages("Analyze this", None, None, screen_b64)
        self.assertEqual(len(messages), 2)
        self.assertIn("images", messages[1])
        self.assertEqual(messages[1]["images"], [screen_b64])

    @patch('ai.ollama')
    def test_get_response_with_ollama(self, mock_ollama):
        """Test get_response when ollama is available."""
        # Mock ollama response
        mock_response = MagicMock()
        mock_response.message.content = "Hello from Ollama!"
        mock_ollama.chat.return_value = mock_response

        response = get_response("Hello")
        self.assertEqual(response, "Hello from Ollama!")
        mock_ollama.chat.assert_called_once()

    @patch('ai.ollama', None)
    def test_get_response_fallback(self):
        """Test get_response falls back when ollama unavailable."""
        response = get_response("hello")
        # Should get a fallback response
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)

    @patch('ai.ollama')
    def test_get_response_ollama_error(self, mock_ollama):
        """Test get_response handles ollama errors gracefully."""
        mock_ollama.chat.side_effect = Exception("Connection failed")

        response = get_response("hello")
        # Should fall back to canned response
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)


if __name__ == '__main__':
    unittest.main()