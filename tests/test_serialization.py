"""Canonical serializer bytes must not depend on the host newline convention."""
import json
from pathlib import Path
import tempfile
import unittest
from campaign import save


class SerializationTests(unittest.TestCase):
    def test_literal_lf_canonical_bytes(self):
        data = {'owned': [0, '1/4'], 'note': 'benign metadata'}
        with tempfile.TemporaryDirectory(prefix='owned-json-lf-') as directory:
            path = Path(directory) / 'record.json'
            save(path, data)
            self.assertEqual(path.read_bytes(), (json.dumps(data, indent=2, sort_keys=True) + '\n').encode('utf-8'))
            self.assertNotIn(b'\r', path.read_bytes())


if __name__ == '__main__':
    unittest.main()
