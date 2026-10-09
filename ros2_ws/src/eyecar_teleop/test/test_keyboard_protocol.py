import unittest

from eyecar_teleop.keyboard_protocol import KeyEvent, TerminalKeyboard


class TerminalInputTests(unittest.TestCase):
    def test_plain_wasd_and_russian(self):
        reader = TerminalKeyboard()
        self.assertEqual([e.key for e in reader.feed('WASD ЦФЫВ '.encode())],
                         list('wasd цфыв '))

    def test_csi_arrows_and_modifiers(self):
        reader = TerminalKeyboard()
        events = reader.feed(b'\x1b[A\x1b[B\x1b[C\x1b[D\x1b[1;2A')
        self.assertEqual([e.key for e in events], list('wsdaw'))

    def test_split_arrow_sequences_do_not_create_plain_letters(self):
        reader = TerminalKeyboard()
        self.assertEqual(reader.feed(b'\x1bO'), [])
        self.assertEqual(reader.feed(b'A'), [KeyEvent('w')])
        self.assertEqual(reader.feed(b'\x1b['), [])
        self.assertEqual(reader.feed(b'D'), [KeyEvent('a')])

    def test_kitty_releases_preserved(self):
        reader = TerminalKeyboard()
        self.assertEqual(reader.feed(b'\x1b[119;1:3u'), [KeyEvent('w', 'release')])


if __name__ == '__main__':
    unittest.main()
