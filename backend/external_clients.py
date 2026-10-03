"""HTTPS clients for Nextbike and openrouteservice."""

import json
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


NEXTBIKE_LIVE_URL = "https://maps2.nextbike.net/maps/nextbike-live.json"
ORS_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/foot-walking"
ORS_MATRIX_URL = "https://api.openrouteservice.org/v2/matrix/foot-walking"


def require_https(url):
    """Raise ValueError unless ``url`` uses HTTPS."""
    if urlparse(url).scheme != "https":
        raise ValueError("external API URLs must use https")
    return url


def read_json_url(url, *, headers=None, body=None, timeout=10):
    """Read JSON from an HTTPS URL."""
    require_https(url)
    data = None
    request_headers = dict(headers or {})
    request_headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    request = Request(url, data=data, headers=request_headers)
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class NextbikeClient:
    """Small Nextbike client using the documented live endpoint."""

    def __init__(self, base_url=NEXTBIKE_LIVE_URL):
        self.base_url = require_https(base_url)

    def build_places_url(self, *, city_uid, lat=None, lng=None, bike_distance=None):
        query = {"city": city_uid}
        if lat is not None:
            query["lat"] = lat
        if lng is not None:
            query["lng"] = lng
        if bike_distance is not None:
            query["bike_distance"] = bike_distance
        return f"{self.base_url}?{urlencode(query)}"

    def get_places(self, *, city_uid, lat=None, lng=None, bike_distance=None):
        url = self.build_places_url(
            city_uid=city_uid,
            lat=lat,
            lng=lng,
            bike_distance=bike_distance,
        )
        return read_json_url(url)


class OpenRouteServiceClient:
    """openrouteservice client for the walking endpoints used by the backend."""

    def __init__(
        self,
        api_key,
        *,
        directions_url=ORS_DIRECTIONS_URL,
        matrix_url=ORS_MATRIX_URL,
    ):
        self.api_key = api_key
        self.directions_url = require_https(directions_url)
        self.matrix_url = require_https(matrix_url)

    def walking_directions(self, *, start, end):
        query = urlencode(
            {
                "start": _ors_coordinate(start),
                "end": _ors_coordinate(end),
            }
        )
        return read_json_url(
            f"{self.directions_url}?{query}",
            headers={"Authorization": self.api_key},
        )

    def walking_matrix(self, *, locations, sources, destinations):
        return read_json_url(
            self.matrix_url,
            headers={"Authorization": self.api_key},
            body={
                "locations": [_ors_location(location) for location in locations],
                "sources": sources,
                "destinations": destinations,
            },
        )


def _ors_coordinate(location):
    lng, lat = _ors_location(location)
    return f"{lng},{lat}"


def _ors_location(location):
    lat, lng = location
    return [lng, lat]

