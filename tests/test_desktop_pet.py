import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add src to path so we can import desktop_pet
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from desktop_pet import DesktopPet


def make_pet_for_command_tests():
    pet = DesktopPet.__new__(DesktopPet)
    pet.chat = MagicMock()
    pet.state = "idle"
    pet.frame = 0
    pet.x = 0
    pet.y = 0
    pet.target_x = None
    pet.target_y = None
    pet.velocity_x = 0
    pet.velocity_y = 0
    return pet


class TestDesktopPetCommandHandling(unittest.TestCase):
    def test_open_program_command(self):
        pet = make_pet_for_command_tests()
        with patch('desktop_pet.subprocess.Popen') as mock_popen:
            result = pet.handle_ai_command({
                'command': 'open_program',
                'args': {'program': 'notepad.exe'}
            })

        mock_popen.assert_called_once_with('notepad.exe')
        self.assertEqual(result, 'Opened program: notepad.exe.')

    def test_close_program_command(self):
        pet = make_pet_for_command_tests()
        mock_window = MagicMock()

        with patch('desktop_pet.pyautogui.getWindowsWithTitle', return_value=[mock_window]):
            result = pet.handle_ai_command({
                'command': 'close_program',
                'args': {'program': 'Notepad'}
            })

        mock_window.close.assert_called_once()
        self.assertEqual(result, 'Closed program: Notepad.')

    def test_type_text_command_focus_program(self):
        pet = make_pet_for_command_tests()
        mock_window = MagicMock()

        with patch('desktop_pet.pyautogui.getWindowsWithTitle', return_value=[mock_window]):
            with patch('desktop_pet.pyautogui.typewrite') as mock_typewrite:
                result = pet.handle_ai_command({
                    'command': 'type_text',
                    'args': {'program': 'Notepad', 'text': 'Hello world'}
                })

        mock_window.activate.assert_called_once()
        mock_typewrite.assert_called_once_with('Hello world')
        self.assertEqual(result, 'Typed text: Hello world in Notepad')


if __name__ == '__main__':
    unittest.main()
