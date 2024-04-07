import unittest
from util import get_keys_for_stroke


class TestUtil(unittest.TestCase):
    def test_get_keys_for_stroke(self):
        self.assertEqual(
            get_keys_for_stroke("PHRO-FR"),
            ("P-", "H-", "R-", "O-", "-F", "-R"),
        )


if __name__ == "__main__":
    unittest.main()
