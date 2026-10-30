"""Offline checks for the build guide and its checked-in assets."""
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class DocumentationTests(unittest.TestCase):
    def test_english_and_local_links(self):
        pages = [ROOT / 'README.md', *sorted((ROOT / 'docs').glob('*.md')),
                 ROOT / 'models/eyecar/README.md']
        for page in pages:
            content = page.read_text()
            with self.subTest(page=page.relative_to(ROOT)):
                self.assertIsNone(re.search('[А-Яа-яЁё]', content))
                for target in re.findall(r'\]\(([^)]+)\)', content):
                    url = urlsplit(target.strip('<>'))
                    if url.scheme or not url.path:
                        continue
                    path = page.parent / unquote(url.path)
                    self.assertTrue(path.exists(), f'{page.name}: missing {target}')

    def test_gallery_covers_photos_and_model_exports(self):
        gallery = (ROOT / 'docs/Gallery.md').read_text()
        for folder in ('public', 'models/eyecar/generated'):
            for path in sorted((ROOT / folder).iterdir()):
                if path.is_file():
                    with self.subTest(asset=path.name):
                        self.assertIn(path.name.replace(' ', '%20'), gallery)
        self.assertIn('public/bonus.jpg', (ROOT / 'README.md').read_text())


if __name__ == '__main__':
    unittest.main()
