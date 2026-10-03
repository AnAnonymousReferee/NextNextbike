"""Backend API functions for the BonnBike application.

The functions mirror ``Documentation_and_planning/API_Documentation/BACKEND API.md``.

User data is expected to be stored through ``backend.user_store.SQLiteUserStore``.
That store uses SQL and keeps only password hashes, never plaintext passwords.

Response contract used by the Python layer:
    (status_code, json_body)

For endpoints that return no JSON, ``json_body`` is ``None``.
"""

import math
import os
import re
import sys

from backend.external_clients import NextbikeClient, OpenRouteServiceClient
from backend.user_store import SQLiteUserStore


OK = 200
BAD_REQUEST = 400

NORMAL_BIKE_TYPE = 196
ELECTRIC_BIKE_TYPE = 349

MIN_SEARCH_RADIUS_METERS = 100
MAX_SEARCH_RADIUS_METERS = 2000
MAX_NEARBY_BIKES_FOR_ORS = 5

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
EMAIL_RE = re.compile(r"^[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+$")
BIKE_NUMBER_RE = re.compile(r"^[0-9]{1,12}$")

DEFAULT_DB_PATH = "bonnbike.sqlite3"


def getNextNextbike(queries, *, nextbike_client=None, ors_client=None):
    """Return the shortest walking route to the best matching nearby bike.

    Expected query keys:
        city_uid
        location_lat_lng
        search_radius_in_meter
        biketype_electric_yesno

    Expected success body:
        {
            "shortest_path": geojson_feature_collection,
            "bikenumber": "535218"
        }
    """
    try:
        queries = _require_mapping(queries, "queries")
        city_uid = _parse_city_uid(queries.get("city_uid"))
        user_location = _parse_location(queries.get("location_lat_lng"))
        radius = _parse_search_radius(queries.get("search_radius_in_meter"))
        want_electric = _parse_electric_flag(
            queries.get("biketype_electric_yesno")
        )

        nextbike_client = nextbike_client or NextbikeClient()
        ors_client = ors_client or _default_ors_client()

        payload = nextbike_client.get_places(
            city_uid=city_uid,
            lat=user_location[0],
            lng=user_location[1],
            bike_distance=radius,
        )
        candidates = _bike_candidates(payload, want_electric, user_location)
        if not candidates:
            print(
                f"DEBUG no matching bike found: city_uid={city_uid} location={user_location} "
                f"radius={radius} want_electric={want_electric} payload_items={len(payload)}",
                file=sys.stderr,
            )
            return _bad_request("no matching bike found")

        nearest_candidates = candidates[:MAX_NEARBY_BIKES_FOR_ORS]
        locations = [user_location] + [
            candidate["location"] for candidate in nearest_candidates
        ]
        matrix = ors_client.walking_matrix(
            locations=locations,
            sources=[0],
            destinations=list(range(1, len(locations))),
        )
        durations = _extract_candidate_durations(matrix, len(nearest_candidates))
        if not durations:
            return _bad_request("no route duration found")

        best_index = min(range(len(durations)), key=lambda index: durations[index])
        best_candidate = nearest_candidates[best_index]
        route = ors_client.walking_directions(
            start=user_location,
            end=best_candidate["location"],
        )

        return _ok(
            {
                "shortest_path": route,
                "bikenumber": best_candidate["bike_number"],
            }
        )
    except (LookupError, TypeError, ValueError) as exc:
        return _bad_request(str(exc))
    except Exception as exc:
        return _bad_request(f"backend error: {exc}")


def getAllBikes(headers, queries, *, nextbike_client=None, user_store=None):
    """Return all bike marker locations and favourite marker locations.

    Expected header keys:
        api_key_user or api-key

    Expected query keys:
        city_uid
        biketype_electric_yesno

    Expected success body:
        {
            "bike_locations": [[lat, lng], ...],
            "favourites": [[lat, lng], ...]
        }
    """
    store, close_store = _resolve_user_store(user_store)
    try:
        headers = _require_mapping(headers, "headers")
        queries = _require_mapping(queries, "queries")
        api_key = _parse_api_key(_get_header(headers, "api_key_user", "api-key"))
        city_uid = _parse_city_uid(queries.get("city_uid"))
        want_electric = _parse_electric_flag(
            queries.get("biketype_electric_yesno")
        )

        favourite_numbers = store.favourites_for_api_key(api_key)
        if favourite_numbers is None:
            return _bad_request("user does not exist")

        nextbike_client = nextbike_client or NextbikeClient()
        payload = nextbike_client.get_places(city_uid=city_uid)
        body = _bike_location_lists(
            payload,
            want_electric,
            favourite_numbers=set(map(str, favourite_numbers)),
        )
        return _ok(body)
    except (LookupError, TypeError, ValueError) as exc:
        return _bad_request(str(exc))
    except Exception as exc:
        return _bad_request(f"backend error: {exc}")
    finally:
        if close_store:
            store.close()


def userLogin(queries, *, user_store=None):
    """Authenticate a user and return a user API key.

    ``user_store`` must verify the plaintext password against a stored hash.

    Expected query keys:
        username
        passwort

    Expected success body:
        {"api_key": "generated-or-existing-user-api-key"}
    """
    store, close_store = _resolve_user_store(user_store)
    try:
        queries = _require_mapping(queries, "queries")
        username = _parse_username(queries.get("username"))
        password = _parse_password(queries.get("passwort"))

        if not store.authenticate(username, password):
            return _bad_request("wrong password/username")

        api_key = store.api_key_for(username)
        if not api_key:
            return _bad_request("user does not exist")
        return _ok({"api_key": api_key})
    except (LookupError, TypeError, ValueError) as exc:
        return _bad_request(str(exc))
    except Exception as exc:
        return _bad_request(f"backend error: {exc}")
    finally:
        if close_store:
            store.close()


def register_user(queries, *, user_store=None):
    """Register a new user.

    ``user_store`` must hash the password before writing the user to SQL.

    Expected query keys:
        username
        passwort
        email

    Expected success body:
        None
    """
    store, close_store = _resolve_user_store(user_store)
    try:
        queries = _require_mapping(queries, "queries")
        username = _parse_username(queries.get("username"))
        password = _parse_password(queries.get("passwort"))
        email = _parse_email(queries.get("email"))

        store.register(username, password, email)
        return _ok(None)
    except (LookupError, TypeError, ValueError) as exc:
        return _bad_request(str(exc))
    except Exception as exc:
        return _bad_request(f"backend error: {exc}")
    finally:
        if close_store:
            store.close()


def change_password(queries, *, user_store=None, mail_sender=None):
    """Trigger a password reset email for an existing user.

    Expected query keys:
        email

    Expected success body:
        None
    """
    store, close_store = _resolve_user_store(user_store)
    try:
        queries = _require_mapping(queries, "queries")
        email = _parse_email(queries.get("email"))

        token = store.request_password_reset(email)
        if not token:
            return _bad_request("user does not exist")

        if mail_sender is not None:
            mail_sender.send_password_reset(email=email, token=token)
        return _ok(None)
    except (LookupError, TypeError, ValueError) as exc:
        return _bad_request(str(exc))
    except Exception as exc:
        return _bad_request(f"backend error: {exc}")
    finally:
        if close_store:
            store.close()


def reset_password(queries, *, user_store=None):
    """Reset a user's password using a previously generated token.

    Expected query keys:
        token
        passwort

    Expected success body:
        None
    """
    store, close_store = _resolve_user_store(user_store)
    try:
        queries = _require_mapping(queries, "queries")
        token = _parse_token(queries.get("token"))
        password = _parse_password(queries.get("passwort"))

        if not store.reset_password(token, password):
            return _bad_request("invalid or expired token")
        return _ok(None)
    except (LookupError, TypeError, ValueError) as exc:
        return _bad_request(str(exc))
    except Exception as exc:
        return _bad_request(f"backend error: {exc}")
    finally:
        if close_store:
            store.close()


def markFav(headers, queries, *, user_store=None):
    """Add or remove a bike number as favourite for the authenticated user.

    Expected header keys:
        api-key or api_key_user

    Expected query keys:
        bike_number
        action (optional: add/remove)

    Expected success body:
        None
    """
    store, close_store = _resolve_user_store(user_store)
    try:
        headers = _require_mapping(headers, "headers")
        queries = _require_mapping(queries, "queries")
        api_key = _parse_api_key(_get_header(headers, "api-key", "api_key_user"))
        bike_number = _parse_bike_number(queries.get("bike_number"))
        action = _parse_favourite_action(queries.get("action"))

        if action == "remove":
            success = store.remove_favourite(api_key, bike_number)
        else:
            success = store.add_favourite(api_key, bike_number)

        if not success:
            return _bad_request("user does not exist")
        return _ok(None)
    except (LookupError, TypeError, ValueError) as exc:
        return _bad_request(str(exc))
    except Exception as exc:
        return _bad_request(f"backend error: {exc}")
    finally:
        if close_store:
            store.close()


def _ok(body=None):
    return OK, body


def _bad_request(message):
    return BAD_REQUEST, {"error": message or "input invalid"}


def _require_mapping(value, name):
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be a mapping")
    return value


def _get_header(headers, *names):
    for name in names:
        if name in headers:
            return headers[name]
    raise ValueError("missing api key")


def _parse_city_uid(value):
    if isinstance(value, bool):
        raise ValueError("city_uid invalid")
    if isinstance(value, int):
        if value <= 0:
            raise ValueError("city_uid invalid")
        return str(value)
    if isinstance(value, str) and value.isdigit() and int(value) > 0:
        return value
    raise ValueError("city_uid invalid")


def _parse_search_radius(value):
    if isinstance(value, bool):
        raise ValueError("search_radius_in_meter invalid")
    if isinstance(value, int):
        radius = value
    elif isinstance(value, str) and value.isdigit():
        radius = int(value)
    else:
        raise ValueError("search_radius_in_meter invalid")

    if not MIN_SEARCH_RADIUS_METERS <= radius <= MAX_SEARCH_RADIUS_METERS:
        raise ValueError("search_radius_in_meter invalid")
    return radius


def _parse_location(value):
    if isinstance(value, str):
        parts = value.split(",")
        if len(parts) != 2:
            raise ValueError("location_lat_lng invalid")
        raw_lat, raw_lng = parts
    elif isinstance(value, (list, tuple)) and len(value) == 2:
        raw_lat, raw_lng = value
    else:
        raise ValueError("location_lat_lng invalid")

    try:
        lat = float(raw_lat)
        lng = float(raw_lng)
    except (TypeError, ValueError) as exc:
        raise ValueError("location_lat_lng invalid") from exc

    if not math.isfinite(lat) or not math.isfinite(lng):
        raise ValueError("location_lat_lng invalid")
    if not -90 <= lat <= 90:
        raise ValueError("location_lat_lng invalid")
    if not -180 <= lng <= 180:
        raise ValueError("location_lat_lng invalid")
    return lat, lng


def _parse_electric_flag(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"yes", "true", "1", "electric", "e-bike", "ebike"}:
            return True
        if normalized in {"no", "false", "0", "normal", "bike"}:
            return False
    raise ValueError("biketype_electric_yesno invalid")


def _parse_username(value):
    if not isinstance(value, str) or not USERNAME_RE.fullmatch(value):
        raise ValueError("username invalid")
    return value


def _parse_password(value):
    if not isinstance(value, str) or not 8 <= len(value) <= 128:
        raise ValueError("passwort invalid")
    return value


def _parse_email(value):
    if not isinstance(value, str) or not EMAIL_RE.fullmatch(value):
        raise ValueError("email invalid")
    return value


def _parse_api_key(value):
    if not isinstance(value, str):
        raise ValueError("api key invalid")
    api_key = value.strip()
    if not api_key or any(character.isspace() for character in api_key):
        raise ValueError("api key invalid")
    return api_key


def _parse_bike_number(value):
    if isinstance(value, int) and not isinstance(value, bool):
        value = str(value)
    if not isinstance(value, str) or not BIKE_NUMBER_RE.fullmatch(value):
        raise ValueError("bike_number invalid")
    return value


def _parse_favourite_action(value):
    if value is None:
        return "add"
    if not isinstance(value, str):
        raise ValueError("action invalid")
    action = value.strip().lower()
    if action not in {"add", "remove"}:
        raise ValueError("action invalid")
    return action


def _parse_token(value):
    if not isinstance(value, str):
        raise ValueError("token invalid")
    token = value.strip()
    if not token or any(character.isspace() for character in token):
        raise ValueError("token invalid")
    return token


def _resolve_user_store(user_store):
    if user_store is not None:
        return user_store, False

    db_path = os.environ.get("BONNBIKE_DB_PATH", DEFAULT_DB_PATH)
    return SQLiteUserStore(db_path), True


def _default_ors_client():
    api_key = os.environ.get("ORS_API_KEY")
    if not api_key:
        raise ValueError("ORS_API_KEY is not configured")
    return OpenRouteServiceClient(api_key)


def _bike_candidates(payload, want_electric, user_location):
    candidates = []
    for bike, bike_location in _iter_matching_bikes(payload, want_electric):
        bike_number = bike.get("number")
        if bike_number is None:
            continue
        candidates.append(
            {
                "bike_number": str(bike_number),
                "location": bike_location,
                "air_distance": _haversine_meters(user_location, bike_location),
            }
        )
    return sorted(candidates, key=lambda candidate: candidate["air_distance"])


def _iter_matching_bikes(payload, want_electric):
    for item in _iter_places(payload):
        place = item["place"]
        location = item["location"]
        for bike in _as_list(place.get("bike_list")):
            if not isinstance(bike, dict):
                continue
            bike_type = _normalize_bike_type(bike.get("bike_type"))
            if _bike_type_matches(bike_type, want_electric):
                yield bike, location


def _bike_location_lists(payload, want_electric, favourite_numbers):
    bike_locations = []
    favourite_locations = []
    bikes = []

    for bike, bike_location in _iter_matching_bikes(payload, want_electric):
        bike_number = bike.get("number")
        if bike_number is None:
            continue
        normalized_number = str(bike_number)
        bike_type = _normalize_bike_type(bike.get("bike_type"))
        bikes.append(
            {
                "bike_number": normalized_number,
                "lat": bike_location[0],
                "lng": bike_location[1],
                "is_electric": bike_type == ELECTRIC_BIKE_TYPE,
                "is_favorite": normalized_number in favourite_numbers,
            }
        )

    for item in _iter_places(payload):
        place = item["place"]
        location = [item["location"][0], item["location"][1]]
        matching_bikes = _matching_bikes_for_place(place, want_electric)

        if matching_bikes:
            has_favourite = any(
                str(bike.get("number")) in favourite_numbers
                for bike in matching_bikes
                if bike.get("number") is not None
            )
            has_non_favourite = any(
                str(bike.get("number")) not in favourite_numbers
                for bike in matching_bikes
                if bike.get("number") is not None
            )
            if has_non_favourite:
                bike_locations.append(location)
            if has_favourite:
                favourite_locations.append(location)
            continue

        if _place_has_matching_bike_type_count(place, want_electric):
            bike_locations.append(location)

    return {
        "bike_locations": bike_locations,
        "favourites": favourite_locations,
        "bikes": bikes,
    }


def _matching_bikes_for_place(place, want_electric):
    matching_bikes = []
    for bike in _as_list(place.get("bike_list")):
        if not isinstance(bike, dict):
            continue
        bike_type = _normalize_bike_type(bike.get("bike_type"))
        if _bike_type_matches(bike_type, want_electric):
            matching_bikes.append(bike)
    return matching_bikes


def _place_has_matching_bike_type_count(place, want_electric):
    bike_types = place.get("bike_types")
    if not isinstance(bike_types, dict):
        return False
    wanted_type = ELECTRIC_BIKE_TYPE if want_electric else NORMAL_BIKE_TYPE
    try:
        return int(bike_types.get(str(wanted_type), 0)) > 0
    except (TypeError, ValueError):
        return False


def _bike_type_matches(bike_type, want_electric):
    wanted_type = ELECTRIC_BIKE_TYPE if want_electric else NORMAL_BIKE_TYPE
    return bike_type == wanted_type


def _normalize_bike_type(value):
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _iter_places(payload):
    if not isinstance(payload, dict):
        return
    for country in _as_api_objects(payload.get("countries"), object_key="cities"):
        if not isinstance(country, dict):
            continue
        for city in _as_api_objects(country.get("cities"), object_key="places"):
            if not isinstance(city, dict):
                continue
            for place in _as_api_objects(city.get("places"), object_key="lat"):
                if not isinstance(place, dict):
                    continue
                location = _place_location(place)
                if location is None:
                    continue
                yield {"place": place, "location": location}


def _as_api_objects(value, *, object_key):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, dict):
        if object_key in value:
            return [value]
        return list(value.values())
    return []


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return list(value.values())
    return []


def _place_location(place):
    try:
        lat = float(place["lat"])
        lng = float(place["lng"])
    except (KeyError, TypeError, ValueError):
        return None
    if not math.isfinite(lat) or not math.isfinite(lng):
        return None
    if not -90 <= lat <= 90 or not -180 <= lng <= 180:
        return None
    return lat, lng


def _extract_candidate_durations(matrix, expected_count):
    if not isinstance(matrix, dict):
        raise ValueError("ORS matrix response invalid")
    durations_by_source = matrix.get("durations")
    if not durations_by_source:
        raise ValueError("ORS matrix response invalid")
    try:
        durations = list(durations_by_source[0])
    except (IndexError, TypeError) as exc:
        raise ValueError("ORS matrix response invalid") from exc

    if len(durations) == expected_count + 1 and durations[0] == 0:
        durations = durations[1:]
    if len(durations) < expected_count:
        raise ValueError("ORS matrix response invalid")

    cleaned = []
    for duration in durations[:expected_count]:
        if duration is None:
            cleaned.append(math.inf)
            continue
        try:
            duration_float = float(duration)
        except (TypeError, ValueError) as exc:
            raise ValueError("ORS matrix response invalid") from exc
        if duration_float < 0:
            raise ValueError("ORS matrix response invalid")
        cleaned.append(duration_float)

    if all(math.isinf(duration) for duration in cleaned):
        return []
    return cleaned


def _haversine_meters(first, second):
    lat1, lng1 = first
    lat2, lng2 = second
    radius_meters = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(delta_lambda / 2) ** 2
    )
    return radius_meters * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
