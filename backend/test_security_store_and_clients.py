import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from backend.external_clients import (
    NEXTBIKE_LIVE_URL,
    ORS_DIRECTIONS_URL,
    ORS_MATRIX_URL,
    NextbikeClient,
    OpenRouteServiceClient,
    require_https,
)
from backend.security import PASSWORD_HASH_ALGORITHM, hash_password, verify_password
from backend.user_store import SQLiteUserStore


def fast_hash(password):
    return hash_password(password, iterations=1)


class TestPasswordSecurity(unittest.TestCase):
    def test_password_hash_does_not_store_plaintext_and_can_be_verified(self):
        password = "CorrectHorseBatteryStaple1!"

        stored_hash = fast_hash(password)

        self.assertTrue(stored_hash.startswith(f"{PASSWORD_HASH_ALGORITHM}$"))
        self.assertNotIn(password, stored_hash)
        self.assertTrue(verify_password(password, stored_hash))
        self.assertFalse(verify_password("wrong-password", stored_hash))

    def test_same_password_gets_different_hashes_because_salt_is_random(self):
        first_hash = fast_hash("SamePassword2026!")
        second_hash = fast_hash("SamePassword2026!")

        self.assertNotEqual(first_hash, second_hash)
        self.assertTrue(verify_password("SamePassword2026!", first_hash))
        self.assertTrue(verify_password("SamePassword2026!", second_hash))

    def test_malformed_hash_returns_false(self):
        self.assertFalse(verify_password("password", "not-a-valid-hash"))
        self.assertFalse(
            verify_password("password", "pbkdf2_sha256$1$not-base64$also-not-base64")
        )


class TestSQLiteUserStore(unittest.TestCase):
    def setUp(self):
        self.store = SQLiteUserStore(":memory:")
        self.hash_patch = patch("backend.user_store.hash_password", fast_hash)
        self.api_key_patch = patch("backend.user_store.generate_api_key")
        self.hash_patch.start()
        self.mock_generate_api_key = self.api_key_patch.start()
        self.mock_generate_api_key.side_effect = [
            "api_alice_123",
            "api_bob_456",
            "api_malicious_789",
        ]

    def tearDown(self):
        self.api_key_patch.stop()
        self.hash_patch.stop()
        self.store.close()

    def test_schema_uses_password_hash_column_and_no_plain_password_column(self):
        columns = [
            row["name"]
            for row in self.store.connection.execute("PRAGMA table_info(users)")
        ]

        self.assertIn("password_hash", columns)
        self.assertNotIn("password", columns)

    def test_register_stores_hash_and_authenticates_against_hash(self):
        self.store.register("alice", "CorrectHorseBatteryStaple1!", "alice@example.org")

        row = self.store.connection.execute(
            "SELECT username, password_hash, email, api_key FROM users WHERE username = ?",
            ("alice",),
        ).fetchone()

        self.assertEqual("alice", row["username"])
        self.assertEqual("alice@example.org", row["email"])
        self.assertEqual("api_alice_123", row["api_key"])
        self.assertNotEqual("CorrectHorseBatteryStaple1!", row["password_hash"])
        self.assertTrue(
            verify_password("CorrectHorseBatteryStaple1!", row["password_hash"])
        )
        self.assertTrue(
            self.store.authenticate("alice", "CorrectHorseBatteryStaple1!")
        )
        self.assertFalse(self.store.authenticate("alice", "wrong-password"))

    def test_duplicate_username_or_email_is_rejected(self):
        self.store.register("alice", "CorrectHorseBatteryStaple1!", "alice@example.org")

        with self.assertRaises(ValueError):
            self.store.register("alice", "OtherSecurePassword2026!", "new@example.org")

        with self.assertRaises(ValueError):
            self.store.register("newalice", "OtherSecurePassword2026!", "alice@example.org")

    def test_favourites_are_stored_in_sql_user_record(self):
        self.store.register("bob", "B0nnBike!2026", "bob@example.org")

        self.assertEqual([], self.store.favourites_for_api_key("api_alice_123"))
        self.assertTrue(self.store.add_favourite("api_alice_123", "535218"))
        self.assertTrue(self.store.add_favourite("api_alice_123", "535218"))
        self.assertTrue(self.store.add_favourite("api_alice_123", "900001"))

        self.assertEqual(
            ["535218", "900001"],
            self.store.favourites_for_api_key("api_alice_123"),
        )

        self.assertTrue(self.store.remove_favourite("api_alice_123", "535218"))
        self.assertEqual(
            ["900001"],
            self.store.favourites_for_api_key("api_alice_123"),
        )

    def test_parameterized_sql_keeps_malicious_username_as_data(self):
        malicious_username = "eve'); DROP TABLE users; --"

        self.store.register(
            malicious_username,
            "StillAValidPassword2026!",
            "eve@example.org",
        )

        table = self.store.connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'users'"
        ).fetchone()
        row = self.store.connection.execute(
            "SELECT username FROM users WHERE username = ?",
            (malicious_username,),
        ).fetchone()

        self.assertIsNotNone(table)
        self.assertEqual(malicious_username, row["username"])


class TestHttpsClients(unittest.TestCase):
    def test_all_external_base_urls_use_https(self):
        self.assertEqual("https", urlparse(NEXTBIKE_LIVE_URL).scheme)
        self.assertEqual("https", urlparse(ORS_DIRECTIONS_URL).scheme)
        self.assertEqual("https", urlparse(ORS_MATRIX_URL).scheme)

    def test_http_urls_are_rejected(self):
        with self.assertRaises(ValueError):
            require_https("http://example.org/insecure")

        with self.assertRaises(ValueError):
            NextbikeClient(base_url="http://maps2.nextbike.net/maps/nextbike-live.json")

        with self.assertRaises(ValueError):
            OpenRouteServiceClient(
                "ors-key",
                directions_url="http://api.openrouteservice.org/v2/directions/foot-walking",
            )

    def test_nextbike_url_builder_keeps_https_and_expected_queries(self):
        client = NextbikeClient()

        url = client.build_places_url(
            city_uid="1170",
            lat=50.733334,
            lng=7.1,
            bike_distance=500,
        )
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual("https", parsed.scheme)
        self.assertEqual(["1170"], query["city"])
        self.assertEqual(["50.733334"], query["lat"])
        self.assertEqual(["7.1"], query["lng"])
        self.assertEqual(["500"], query["bike_distance"])


if __name__ == "__main__":
    unittest.main()
