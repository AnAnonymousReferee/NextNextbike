import unittest

from backend.backend_api import (
    BAD_REQUEST,
    ELECTRIC_BIKE_TYPE,
    NORMAL_BIKE_TYPE,
    OK,
    change_password,
    getAllBikes,
    getNextNextbike,
    markFav,
    register_user,
    userLogin,
)
from backend.security import hash_password, verify_password


BONN_CITY_UID = "1170"
BONN_CENTER = "50.733334,7.100000"
BONN_GEOJSON_ROUTE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[7.100000, 50.733334], [7.101200, 50.734100]],
            },
            "properties": {"summary": {"distance": 185.4, "duration": 144.0}},
        }
    ],
}


def normal_bike(number):
    return {"number": str(number), "bike_type": NORMAL_BIKE_TYPE}


def electric_bike(number):
    return {"number": str(number), "bike_type": ELECTRIC_BIKE_TYPE}


def fast_password_hash(password):
    return hash_password(password, iterations=1)


def place(uid, lat, lng, bikes):
    return {
        "uid": uid,
        "lat": lat,
        "lng": lng,
        "bikes_available_to_rent": len(bikes),
        "bike_list": bikes,
        "bike_types": {
            str(NORMAL_BIKE_TYPE): sum(
                1 for bike in bikes if bike["bike_type"] == NORMAL_BIKE_TYPE
            ),
            str(ELECTRIC_BIKE_TYPE): sum(
                1 for bike in bikes if bike["bike_type"] == ELECTRIC_BIKE_TYPE
            ),
        },
    }


def nextbike_payload(places):
    return {
        "countries": [
            {
                "lat": 50.7147,
                "lng": 7.12875,
                "cities": [
                    {
                        "uid": int(BONN_CITY_UID),
                        "lat": 50.7147,
                        "lng": 7.12875,
                        "places": places,
                    }
                ],
            }
        ]
    }


class FakeNextbikeClient:
    def __init__(self, places):
        self.places = places
        self.calls = []

    def get_places(self, *, city_uid, lat=None, lng=None, bike_distance=None):
        self.calls.append(
            {
                "city_uid": city_uid,
                "lat": lat,
                "lng": lng,
                "bike_distance": bike_distance,
            }
        )
        return nextbike_payload(self.places)


class FakeOrsClient:
    def __init__(self, durations=None, route=None):
        self.durations = durations or []
        self.route = route or BONN_GEOJSON_ROUTE
        self.matrix_calls = []
        self.directions_calls = []

    def walking_matrix(self, *, locations, sources, destinations):
        self.matrix_calls.append(
            {
                "locations": locations,
                "sources": sources,
                "destinations": destinations,
            }
        )
        return {"durations": [self.durations]}

    def walking_directions(self, *, start, end):
        self.directions_calls.append({"start": start, "end": end})
        return self.route


class FakeUserStore:
    def __init__(self):
        self.users = {
            "alice": {
                "password_hash": fast_password_hash("CorrectHorseBatteryStaple1!"),
                "email": "alice@example.org",
                "api_key": "api_alice_123",
                "favourites": ["535218"],
            },
            "bob_2026": {
                "password_hash": fast_password_hash("B0nnBike!2026"),
                "email": "bob.2026@example.org",
                "api_key": "api_bob_456",
                "favourites": [],
            },
        }
        self.register_calls = []
        self.password_reset_calls = []
        self.favourite_calls = []

    def authenticate(self, username, password):
        user = self.users.get(username)
        return bool(user and verify_password(password, user["password_hash"]))

    def api_key_for(self, username):
        return self.users[username]["api_key"]

    def username_for_api_key(self, api_key):
        for username, user in self.users.items():
            if user["api_key"] == api_key:
                return username
        return None

    def favourites_for_api_key(self, api_key):
        username = self.username_for_api_key(api_key)
        if username is None:
            return None
        return list(self.users[username]["favourites"])

    def user_exists(self, username):
        return username in self.users

    def email_exists(self, email):
        return any(user["email"] == email for user in self.users.values())

    def register(self, username, password, email):
        if self.user_exists(username) or self.email_exists(email):
            raise ValueError("duplicate user")
        password_hash = fast_password_hash(password)
        self.register_calls.append(
            {"username": username, "password_hash": password_hash, "email": email}
        )
        self.users[username] = {
            "password_hash": password_hash,
            "email": email,
            "api_key": f"api_{username}",
            "favourites": [],
        }

    def request_password_reset(self, email):
        if not self.email_exists(email):
            return None
        self.password_reset_calls.append(email)
        return "reset-token-123"

    def add_favourite(self, api_key, bike_number):
        username = self.username_for_api_key(api_key)
        if username is None:
            return False
        favourites = self.users[username]["favourites"]
        if bike_number not in favourites:
            favourites.append(bike_number)
        self.favourite_calls.append({"api_key": api_key, "bike_number": bike_number, "action": "add"})
        return True

    def remove_favourite(self, api_key, bike_number):
        username = self.username_for_api_key(api_key)
        if username is None:
            return False
        favourites = self.users[username]["favourites"]
        if bike_number in favourites:
            favourites.remove(bike_number)
        self.favourite_calls.append({"api_key": api_key, "bike_number": bike_number, "action": "remove"})
        return True


class FakeMailSender:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.sent = []

    def send_password_reset(self, *, email, token):
        if self.should_fail:
            raise RuntimeError("mail delivery failed")
        self.sent.append({"email": email, "token": token})


class BackendApiTestCase(unittest.TestCase):
    def assert_ok(self, result, expected_body=None):
        self.assertIsInstance(result, tuple)
        self.assertEqual(2, len(result))
        status, body = result
        self.assertEqual(OK, status)
        if expected_body is not None:
            self.assertEqual(expected_body, body)
        return body

    def assert_bad_request(self, result):
        self.assertIsInstance(result, tuple)
        self.assertEqual(2, len(result))
        status, body = result
        self.assertEqual(BAD_REQUEST, status)
        self.assertIsInstance(body, dict)
        self.assertIn("error", body)


class TestGetNextNextbike(BackendApiTestCase):
    def test_01_empty_user_input_returns_400(self):
        self.assert_bad_request(
            getNextNextbike(
                {},
                nextbike_client=FakeNextbikeClient([]),
                ors_client=FakeOrsClient(),
            )
        )

    def test_02_simple_input_returns_geojson_and_bike_number(self):
        nextbike_client = FakeNextbikeClient(
            [place(10044348, 50.7341, 7.1012, [normal_bike("535218")])]
        )
        ors_client = FakeOrsClient(durations=[144.0])

        body = self.assert_ok(
            getNextNextbike(
                {
                    "city_uid": BONN_CITY_UID,
                    "location_lat_lng": BONN_CENTER,
                    "search_radius_in_meter": "500",
                    "biketype_electric_yesno": "no",
                },
                nextbike_client=nextbike_client,
                ors_client=ors_client,
            )
        )

        self.assertEqual(
            {"shortest_path": BONN_GEOJSON_ROUTE, "bikenumber": "535218"}, body
        )
        self.assertEqual(1, len(nextbike_client.calls))
        self.assertEqual(1, len(ors_client.matrix_calls))
        self.assertEqual(1, len(ors_client.directions_calls))

    def test_03_many_realistic_inputs_choose_shortest_walking_duration(self):
        nextbike_client = FakeNextbikeClient(
            [
                place(1001, 50.7339, 7.1005, [normal_bike("535218")]),
                place(1002, 50.7351, 7.1024, [normal_bike("535219")]),
                place(1003, 50.7308, 7.0982, [electric_bike("900001")]),
                place(1004, 50.7362, 7.1051, [normal_bike("535220")]),
            ]
        )
        ors_client = FakeOrsClient(durations=[780.0, 155.0, 240.0])

        body = self.assert_ok(
            getNextNextbike(
                {
                    "city_uid": 1170,
                    "location_lat_lng": [50.733334, 7.100000],
                    "search_radius_in_meter": 1200,
                    "biketype_electric_yesno": False,
                },
                nextbike_client=nextbike_client,
                ors_client=ors_client,
            )
        )

        self.assertEqual("535219", body["bikenumber"])
        self.assertEqual(BONN_GEOJSON_ROUTE, body["shortest_path"])

    def test_04_realistic_electric_filter_uses_electric_bikes_only(self):
        nextbike_client = FakeNextbikeClient(
            [
                place(1001, 50.7339, 7.1005, [normal_bike("535218")]),
                place(1002, 50.7351, 7.1024, [electric_bike("900001")]),
                place(1003, 50.7308, 7.0982, [normal_bike("535219")]),
            ]
        )
        ors_client = FakeOrsClient(durations=[100.0])

        body = self.assert_ok(
            getNextNextbike(
                {
                    "city_uid": BONN_CITY_UID,
                    "location_lat_lng": BONN_CENTER,
                    "search_radius_in_meter": "1000",
                    "biketype_electric_yesno": "yes",
                },
                nextbike_client=nextbike_client,
                ors_client=ors_client,
            )
        )

        self.assertEqual("900001", body["bikenumber"])

    def test_05_boundaries_for_radius_are_accepted(self):
        for radius in ("100", "2000"):
            with self.subTest(radius=radius):
                self.assert_ok(
                    getNextNextbike(
                        {
                            "city_uid": BONN_CITY_UID,
                            "location_lat_lng": BONN_CENTER,
                            "search_radius_in_meter": radius,
                            "biketype_electric_yesno": "no",
                        },
                        nextbike_client=FakeNextbikeClient(
                            [place(10044348, 50.7341, 7.1012, [normal_bike("535218")])]
                        ),
                        ors_client=FakeOrsClient(durations=[144.0]),
                    )
                )

    def test_06_invalid_formats_and_edge_cases_return_400(self):
        invalid_queries = [
            {
                "city_uid": "",
                "location_lat_lng": BONN_CENTER,
                "search_radius_in_meter": "500",
                "biketype_electric_yesno": "no",
            },
            {
                "city_uid": "1170<script>",
                "location_lat_lng": BONN_CENTER,
                "search_radius_in_meter": "500",
                "biketype_electric_yesno": "no",
            },
            {
                "city_uid": BONN_CITY_UID,
                "location_lat_lng": "not-a-coordinate",
                "search_radius_in_meter": "500",
                "biketype_electric_yesno": "no",
            },
            {
                "city_uid": BONN_CITY_UID,
                "location_lat_lng": "91.0,7.1",
                "search_radius_in_meter": "500",
                "biketype_electric_yesno": "no",
            },
            {
                "city_uid": BONN_CITY_UID,
                "location_lat_lng": "50.7,181.0",
                "search_radius_in_meter": "500",
                "biketype_electric_yesno": "no",
            },
            {
                "city_uid": BONN_CITY_UID,
                "location_lat_lng": BONN_CENTER,
                "search_radius_in_meter": "0",
                "biketype_electric_yesno": "no",
            },
            {
                "city_uid": BONN_CITY_UID,
                "location_lat_lng": BONN_CENTER,
                "search_radius_in_meter": "2001",
                "biketype_electric_yesno": "no",
            },
            {
                "city_uid": BONN_CITY_UID,
                "location_lat_lng": BONN_CENTER,
                "search_radius_in_meter": "500",
                "biketype_electric_yesno": "maybe",
            },
        ]

        for queries in invalid_queries:
            with self.subTest(queries=queries):
                self.assert_bad_request(
                    getNextNextbike(
                        queries,
                        nextbike_client=FakeNextbikeClient([]),
                        ors_client=FakeOrsClient(),
                    )
                )

    def test_07_no_matching_bike_returns_400(self):
        self.assert_bad_request(
            getNextNextbike(
                {
                    "city_uid": BONN_CITY_UID,
                    "location_lat_lng": BONN_CENTER,
                    "search_radius_in_meter": "500",
                    "biketype_electric_yesno": "yes",
                },
                nextbike_client=FakeNextbikeClient(
                    [place(10044348, 50.7341, 7.1012, [normal_bike("535218")])]
                ),
                ors_client=FakeOrsClient(),
            )
        )


class TestGetAllBikes(BackendApiTestCase):
    def test_01_empty_user_input_returns_400(self):
        self.assert_bad_request(
            getAllBikes(
                {},
                {},
                nextbike_client=FakeNextbikeClient([]),
                user_store=FakeUserStore(),
            )
        )

    def test_02_simple_input_returns_locations_and_empty_favourites(self):
        body = self.assert_ok(
            getAllBikes(
                {"api_key_user": "api_bob_456"},
                {"city_uid": BONN_CITY_UID, "biketype_electric_yesno": "no"},
                nextbike_client=FakeNextbikeClient(
                    [place(10044348, 50.7341, 7.1012, [normal_bike("535218")])]
                ),
                user_store=FakeUserStore(),
            )
        )

        self.assertEqual(
            {
                "bike_locations": [[50.7341, 7.1012]],
                "favourites": [],
                "bikes": [
                    {
                        "bike_number": "535218",
                        "lat": 50.7341,
                        "lng": 7.1012,
                        "is_electric": False,
                        "is_favorite": False,
                    }
                ],
            },
            body,
        )

    def test_03_many_realistic_inputs_separate_favourites_from_other_bikes(self):
        body = self.assert_ok(
            getAllBikes(
                {"api-key": "api_alice_123"},
                {"city_uid": 1170, "biketype_electric_yesno": False},
                nextbike_client=FakeNextbikeClient(
                    [
                        place(
                            1001,
                            50.7339,
                            7.1005,
                            [normal_bike("535218"), normal_bike("535219")],
                        ),
                        place(1002, 50.7351, 7.1024, [electric_bike("900001")]),
                        place(1003, 50.7308, 7.0982, [normal_bike("535220")]),
                    ]
                ),
                user_store=FakeUserStore(),
            )
        )

        self.assertEqual([[50.7339, 7.1005], [50.7308, 7.0982]], body["bike_locations"])
        self.assertEqual([[50.7339, 7.1005]], body["favourites"])
        self.assertEqual(
            [
                {
                    "bike_number": "535218",
                    "lat": 50.7339,
                    "lng": 7.1005,
                    "is_electric": False,
                    "is_favorite": True,
                },
                {
                    "bike_number": "535219",
                    "lat": 50.7339,
                    "lng": 7.1005,
                    "is_electric": False,
                    "is_favorite": False,
                },
                {
                    "bike_number": "535220",
                    "lat": 50.7308,
                    "lng": 7.0982,
                    "is_electric": False,
                    "is_favorite": False,
                },
            ],
            body["bikes"],
        )

    def test_04_realistic_electric_filter_returns_electric_locations(self):
        body = self.assert_ok(
            getAllBikes(
                {"api_key_user": "api_bob_456"},
                {"city_uid": BONN_CITY_UID, "biketype_electric_yesno": "yes"},
                nextbike_client=FakeNextbikeClient(
                    [
                        place(1001, 50.7339, 7.1005, [normal_bike("535218")]),
                        place(1002, 50.7351, 7.1024, [electric_bike("900001")]),
                    ]
                ),
                user_store=FakeUserStore(),
            )
        )

        self.assertEqual([[50.7351, 7.1024]], body["bike_locations"])
        self.assertEqual([], body["favourites"])
        self.assertEqual(
            [
                {
                    "bike_number": "900001",
                    "lat": 50.7351,
                    "lng": 7.1024,
                    "is_electric": True,
                    "is_favorite": False,
                }
            ],
            body["bikes"],
        )

    def test_05_empty_nextbike_result_returns_empty_lists(self):
        body = self.assert_ok(
            getAllBikes(
                {"api_key_user": "api_bob_456"},
                {"city_uid": BONN_CITY_UID, "biketype_electric_yesno": "no"},
                nextbike_client=FakeNextbikeClient([]),
                user_store=FakeUserStore(),
            )
        )

        self.assertEqual({"bike_locations": [], "favourites": [], "bikes": []}, body)

    def test_06_invalid_formats_and_edge_cases_return_400(self):
        invalid_cases = [
            ({}, {"city_uid": BONN_CITY_UID, "biketype_electric_yesno": "no"}),
            (
                {"api_key_user": "unknown"},
                {"city_uid": BONN_CITY_UID, "biketype_electric_yesno": "no"},
            ),
            (
                {"api_key_user": "api_bob_456"},
                {"city_uid": "", "biketype_electric_yesno": "no"},
            ),
            (
                {"api_key_user": "api_bob_456"},
                {"city_uid": "1170 OR 1=1", "biketype_electric_yesno": "no"},
            ),
            (
                {"api_key_user": "api_bob_456"},
                {"city_uid": BONN_CITY_UID, "biketype_electric_yesno": "maybe"},
            ),
        ]

        for headers, queries in invalid_cases:
            with self.subTest(headers=headers, queries=queries):
                self.assert_bad_request(
                    getAllBikes(
                        headers,
                        queries,
                        nextbike_client=FakeNextbikeClient([]),
                        user_store=FakeUserStore(),
                    )
                )


class TestUserLogin(BackendApiTestCase):
    def test_01_empty_user_input_returns_400(self):
        self.assert_bad_request(userLogin({}, user_store=FakeUserStore()))

    def test_02_simple_input_returns_api_key(self):
        body = self.assert_ok(
            userLogin(
                {
                    "username": "alice",
                    "passwort": "CorrectHorseBatteryStaple1!",
                },
                user_store=FakeUserStore(),
            )
        )

        self.assertEqual({"api_key": "api_alice_123"}, body)

    def test_03_many_realistic_logins_return_their_api_keys(self):
        store = FakeUserStore()
        store.register("max.mustermann", "SehrSicher2026!", "max@example.org")

        cases = [
            ("alice", "CorrectHorseBatteryStaple1!", "api_alice_123"),
            ("bob_2026", "B0nnBike!2026", "api_bob_456"),
            ("max.mustermann", "SehrSicher2026!", "api_max.mustermann"),
        ]

        for username, password, api_key in cases:
            with self.subTest(username=username):
                self.assert_ok(
                    userLogin(
                        {"username": username, "passwort": password},
                        user_store=store,
                    ),
                    {"api_key": api_key},
                )

    def test_04_wrong_password_or_unknown_user_returns_400(self):
        cases = [
            {"username": "alice", "passwort": "wrong"},
            {"username": "unknown", "passwort": "B0nnBike!2026"},
        ]

        for queries in cases:
            with self.subTest(queries=queries):
                self.assert_bad_request(userLogin(queries, user_store=FakeUserStore()))

    def test_05_invalid_formats_and_edge_cases_return_400(self):
        invalid_queries = [
            {"username": "", "passwort": "B0nnBike!2026"},
            {"username": "ab", "passwort": "B0nnBike!2026"},
            {"username": "x" * 33, "passwort": "B0nnBike!2026"},
            {"username": "alice<script>", "passwort": "B0nnBike!2026"},
            {"username": "alice", "passwort": ""},
            {"username": "alice", "passwort": "short"},
        ]

        for queries in invalid_queries:
            with self.subTest(queries=queries):
                self.assert_bad_request(userLogin(queries, user_store=FakeUserStore()))


class TestRegisterUser(BackendApiTestCase):
    def test_01_empty_user_input_returns_400(self):
        self.assert_bad_request(register_user({}, user_store=FakeUserStore()))

    def test_02_simple_input_registers_user_and_returns_no_json(self):
        store = FakeUserStore()

        body = self.assert_ok(
            register_user(
                {
                    "username": "charlie",
                    "passwort": "SicheresPasswort2026!",
                    "email": "charlie@example.org",
                },
                user_store=store,
            )
        )

        self.assertIsNone(body)
        self.assertEqual("charlie", store.register_calls[0]["username"])
        self.assertEqual("charlie@example.org", store.register_calls[0]["email"])
        self.assertNotIn("password", store.register_calls[0])
        self.assertNotEqual(
            "SicheresPasswort2026!",
            store.register_calls[0]["password_hash"],
        )
        self.assertTrue(
            verify_password(
                "SicheresPasswort2026!",
                store.register_calls[0]["password_hash"],
            )
        )

    def test_03_many_realistic_registrations_are_accepted(self):
        store = FakeUserStore()
        cases = [
            ("dana", "DanaPassword2026!", "dana@example.org"),
            ("erik_2026", "ErikPassword2026!", "erik.2026@example.org"),
            ("frida.h", "FridaPassword2026!", "frida+poose@example.org"),
        ]

        for username, password, email in cases:
            with self.subTest(username=username):
                self.assert_ok(
                    register_user(
                        {"username": username, "passwort": password, "email": email},
                        user_store=store,
                    )
                )

        self.assertEqual(3, len(store.register_calls))

    def test_04_duplicate_user_or_email_returns_400(self):
        duplicate_cases = [
            {
                "username": "alice",
                "passwort": "SicheresPasswort2026!",
                "email": "newalice@example.org",
            },
            {
                "username": "newalice",
                "passwort": "SicheresPasswort2026!",
                "email": "alice@example.org",
            },
        ]

        for queries in duplicate_cases:
            with self.subTest(queries=queries):
                self.assert_bad_request(
                    register_user(queries, user_store=FakeUserStore())
                )

    def test_05_invalid_formats_and_edge_cases_return_400(self):
        invalid_queries = [
            {"username": "", "passwort": "SicheresPasswort2026!", "email": "a@b.de"},
            {"username": "ab", "passwort": "SicheresPasswort2026!", "email": "a@b.de"},
            {
                "username": "x" * 33,
                "passwort": "SicheresPasswort2026!",
                "email": "x@example.org",
            },
            {
                "username": "bad user",
                "passwort": "SicheresPasswort2026!",
                "email": "bad@example.org",
            },
            {"username": "newuser", "passwort": "short", "email": "new@example.org"},
            {
                "username": "newuser",
                "passwort": "SicheresPasswort2026!",
                "email": "not-an-email",
            },
            {
                "username": "newuser",
                "passwort": "SicheresPasswort2026!",
                "email": "name@example.org<script>",
            },
        ]

        for queries in invalid_queries:
            with self.subTest(queries=queries):
                self.assert_bad_request(
                    register_user(queries, user_store=FakeUserStore())
                )


class TestChangePassword(BackendApiTestCase):
    def test_01_empty_user_input_returns_400(self):
        self.assert_bad_request(
            change_password(
                {},
                user_store=FakeUserStore(),
                mail_sender=FakeMailSender(),
            )
        )

    def test_02_simple_input_sends_reset_mail_and_returns_no_json(self):
        store = FakeUserStore()
        mail_sender = FakeMailSender()

        body = self.assert_ok(
            change_password(
                {"email": "alice@example.org"},
                user_store=store,
                mail_sender=mail_sender,
            )
        )

        self.assertIsNone(body)
        self.assertEqual(["alice@example.org"], store.password_reset_calls)
        self.assertEqual(
            [{"email": "alice@example.org", "token": "reset-token-123"}],
            mail_sender.sent,
        )

    def test_03_many_realistic_emails_are_accepted(self):
        store = FakeUserStore()
        store.register("charlie", "SicheresPasswort2026!", "charlie@example.org")
        store.register("dana", "SicheresPasswort2026!", "dana+poose@example.org")
        mail_sender = FakeMailSender()

        for email in ("charlie@example.org", "dana+poose@example.org"):
            with self.subTest(email=email):
                self.assert_ok(
                    change_password(
                        {"email": email},
                        user_store=store,
                        mail_sender=mail_sender,
                    )
                )

        self.assertEqual(2, len(mail_sender.sent))

    def test_04_unknown_email_returns_400(self):
        self.assert_bad_request(
            change_password(
                {"email": "missing@example.org"},
                user_store=FakeUserStore(),
                mail_sender=FakeMailSender(),
            )
        )

    def test_05_invalid_formats_and_edge_cases_return_400(self):
        invalid_queries = [
            {"email": ""},
            {"email": "not-an-email"},
            {"email": "alice@example"},
            {"email": "alice @example.org"},
            {"email": "alice@example.org<script>"},
        ]

        for queries in invalid_queries:
            with self.subTest(queries=queries):
                self.assert_bad_request(
                    change_password(
                        queries,
                        user_store=FakeUserStore(),
                        mail_sender=FakeMailSender(),
                    )
                )

    def test_06_mail_delivery_failure_returns_400(self):
        self.assert_bad_request(
            change_password(
                {"email": "alice@example.org"},
                user_store=FakeUserStore(),
                mail_sender=FakeMailSender(should_fail=True),
            )
        )


class TestMarkFav(BackendApiTestCase):
    def test_01_empty_user_input_returns_400(self):
        self.assert_bad_request(markFav({}, {}, user_store=FakeUserStore()))

    def test_02_simple_input_marks_favourite_and_returns_no_json(self):
        store = FakeUserStore()

        body = self.assert_ok(
            markFav(
                {"api-key": "api_bob_456"},
                {"bike_number": "535218"},
                user_store=store,
            )
        )

        self.assertIsNone(body)
        self.assertEqual(["535218"], store.users["bob_2026"]["favourites"])

    def test_03_many_realistic_favourites_are_accepted_idempotently(self):
        store = FakeUserStore()
        cases = ["535218", "535219", "900001", "000123"]

        for bike_number in cases:
            with self.subTest(bike_number=bike_number):
                self.assert_ok(
                    markFav(
                        {"api_key_user": "api_bob_456"},
                        {"bike_number": bike_number},
                        user_store=store,
                    )
                )

        self.assertEqual(cases, store.users["bob_2026"]["favourites"])

        self.assert_ok(
            markFav(
                {"api_key_user": "api_bob_456"},
                {"bike_number": "535218"},
                user_store=store,
            )
        )
        self.assertEqual(cases, store.users["bob_2026"]["favourites"])

    def test_04_unknown_user_returns_400(self):
        self.assert_bad_request(
            markFav(
                {"api-key": "unknown"},
                {"bike_number": "535218"},
                user_store=FakeUserStore(),
            )
        )

    def test_05_existing_favourite_can_be_removed(self):
        store = FakeUserStore()
        store.users["bob_2026"]["favourites"] = ["535218", "900001"]

        body = self.assert_ok(
            markFav(
                {"api-key": "api_bob_456"},
                {"bike_number": "535218", "action": "remove"},
                user_store=store,
            )
        )

        self.assertIsNone(body)
        self.assertEqual(["900001"], store.users["bob_2026"]["favourites"])

    def test_06_invalid_formats_and_edge_cases_return_400(self):
        invalid_cases = [
            ({}, {"bike_number": "535218"}),
            ({"api-key": ""}, {"bike_number": "535218"}),
            ({"api-key": "api_bob_456"}, {}),
            ({"api-key": "api_bob_456"}, {"bike_number": "535218", "action": "toggle"}),
            ({"api-key": "api_bob_456"}, {"bike_number": ""}),
            ({"api-key": "api_bob_456"}, {"bike_number": "bike-535218"}),
            ({"api-key": "api_bob_456"}, {"bike_number": "535218<script>"}),
            ({"api-key": "api_bob_456"}, {"bike_number": "1" * 13}),
        ]

        for headers, queries in invalid_cases:
            with self.subTest(headers=headers, queries=queries):
                self.assert_bad_request(
                    markFav(headers, queries, user_store=FakeUserStore())
                )


if __name__ == "__main__":
    unittest.main()
