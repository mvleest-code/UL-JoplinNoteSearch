import unittest

from helpers import format_snippet, normalize_host, parse_note_payload, sanitize_url


class SanitizeUrlTests(unittest.TestCase):
    def test_masks_token_without_changing_other_parameters(self):
        result = sanitize_url("http://127.0.0.1:41184/search?query=test&token=private")
        self.assertIn("query=test", result)
        self.assertIn("token=%2A%2A%2A", result)
        self.assertNotIn("private", result)

    def test_masks_token_case_insensitively(self):
        result = sanitize_url("https://example.test/search?TOKEN=private")
        self.assertNotIn("private", result)


class NormalizeHostTests(unittest.TestCase):
    def test_uses_default_and_removes_trailing_slash(self):
        self.assertEqual(
            normalize_host("", "http://127.0.0.1:41184/"),
            "http://127.0.0.1:41184",
        )

    def test_rejects_missing_scheme(self):
        with self.assertRaises(ValueError):
            normalize_host("127.0.0.1:41184", "http://127.0.0.1:41184")

    def test_rejects_query_string(self):
        with self.assertRaises(ValueError):
            normalize_host("https://example.test?token=value", "https://example.test")

    def test_rejects_embedded_credentials(self):
        with self.assertRaises(ValueError):
            normalize_host(
                "https://user:password@example.test",
                "https://example.test",
            )


class FormattingTests(unittest.TestCase):
    def test_collapses_whitespace_and_truncates(self):
        self.assertEqual(format_snippet("one\n  two", max_length=20), "one two")
        self.assertEqual(format_snippet("123456789", max_length=8), "12345...")

    def test_parses_title_and_body(self):
        self.assertEqual(parse_note_payload("Title::Body"), ("Title", "Body"))
        self.assertEqual(parse_note_payload("::Body"), ("Untitled note", "Body"))


if __name__ == "__main__":
    unittest.main()
