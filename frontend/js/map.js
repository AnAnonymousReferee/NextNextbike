let map;

let userLat = null;
let userLng = null;

let userMarker = null;
let radiusCircle = null;
let routeLayer = null;

let currentRadius = 500;

let bikeMarkers = [];
let allBikes = [];
let currentBikeView = "all";

// Später an euer echtes Backend anpassen
const API_BASE_URL = "/api";

// true = benutzt Testdaten
// false = versucht echtes Backend zu benutzen
const USE_FAKE_DATA = false;

// Beispiel API-Key. Später setzt Person B hier den echten API-Key nach Login.
let apiKeyUser = "";


// 1. Karte starten
function initMap() {
  map = L.map("map").setView([50.7374, 7.0982], 13);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors"
  }).addTo(map);
}


// 2. Browser-GPS abfragen
function showUserLocation() {
  if (!navigator.geolocation) {
    alert("Dein Browser unterstützt keine Standortfunktion.");
    return;
  }

  navigator.geolocation.getCurrentPosition(
    function (position) {
      userLat = position.coords.latitude;
      userLng = position.coords.longitude;

      showUserMarker();
      drawRadiusCircle();

      map.setView([userLat, userLng], 15);

      updateBikeVisibilityByRadius();
    },
    function (error) {
      alert("Standort konnte nicht ermittelt werden. Bitte Berechtigung prüfen.");
      console.error(error);
    }
  );
}


// 3. Nutzer-Marker anzeigen
function showUserMarker() {
  if (userMarker !== null) {
    map.removeLayer(userMarker);
  }

  const userIcon = L.divIcon({
    html: `<div style="
      width: 18px;
      height: 18px;
      background: #3b82f6;
      border: 3px solid white;
      border-radius: 50%;
      box-shadow: 0 0 0 3px #3b82f6, 0 2px 8px rgba(0,0,0,0.4);
    "></div>`,
    className: "",
    iconSize: [18, 18],
    iconAnchor: [9, 9]
  });

  userMarker = L.marker([userLat, userLng], { icon: userIcon })
    .addTo(map)
    .bindPopup("<strong>📍 Du bist hier</strong>")
    .openPopup();
}


// 4. Radius-Kreis zeichnen
function drawRadiusCircle() {
  if (userLat === null || userLng === null) {
    return;
  }

  if (radiusCircle !== null) {
    map.removeLayer(radiusCircle);
  }

  radiusCircle = L.circle([userLat, userLng], {
    radius: currentRadius,
    color: '#3b82f6',
    weight: 2,
    opacity: 0.8,
    fillColor: '#3b82f6',
    fillOpacity: 0.1
  }).addTo(map);
}


// 5. Radius ändern
function setSearchRadius(newRadius) {
  currentRadius = newRadius;
  drawRadiusCircle();
  updateBikeVisibilityByRadius();
}


// 6. Fahrräder anzeigen
async function showAllBikes() {
  const cityUid = document.getElementById("citySelect").value;
  const electricOnly = document.getElementById("electricCheckbox").checked;

  try {
    let bikes;

    if (USE_FAKE_DATA) {
      bikes = getFakeBikes();
    } else {
      if (!apiKeyUser) {
        alert("Bitte zuerst einloggen, um Fahrräder zu laden.");
        return;
      }

      const url =
        `${API_BASE_URL}/bikes?city_uid=${cityUid}&biketype_electric_yesno=${electricOnly ? "yes" : "no"}`;

      const response = await fetch(url, {
        method: "GET",
        headers: {
          "api_key_user": apiKeyUser
        }
      });

      if (!response.ok) {
        throw new Error("Fehler beim Laden der Fahrräder.");
      }

      const data = await response.json();
      if (Array.isArray(data.bikes)) {
        bikes = data.bikes;
      } else {
        const favSet = new Set(
          (data.favourites || []).map(function (f) { return `${f[0]},${f[1]}`; })
        );
        bikes = (data.bike_locations || []).map(function (loc, i) {
          return {
            bike_number: String(i + 1),
            lat: loc[0],
            lng: loc[1],
            is_electric: false,
            is_favorite: favSet.has(`${loc[0]},${loc[1]}`)
          };
        });
      }
    }

    allBikes = bikes;
    allBikes = filterBikesByElectricPreference(allBikes);
    renderBikesForCurrentView();
  } catch (error) {
    console.error(error);
    alert("Fahrräder konnten nicht geladen werden.");
  }
}


function filterBikesByElectricPreference(bikes) {
  const electricOnly = document.getElementById("electricCheckbox").checked;

  if (!electricOnly) {
    return bikes;
  }

  return bikes.filter(function (bike) {
    return bike.is_electric;
  });
}


function renderBikesForCurrentView() {
  const bikesToRender = currentBikeView === "favorites"
    ? allBikes.filter(function (bike) {
        return bike.is_favorite;
      })
    : allBikes;

  renderBikeMarkers(filterBikesByElectricPreference(bikesToRender));
}


// 7. Fahrrad-Marker auf Karte malen
function renderBikeMarkers(bikes) {
  clearBikeMarkers();

  bikes.forEach(function (bike) {
    const marker = L.marker([bike.lat, bike.lng], {
      icon: getBikeIcon(bike)
    }).addTo(map);

    marker.bikeData = bike;

    marker.bindPopup(createBikePopupContent(bike));

    bikeMarkers.push(marker);
  });

  updateBikeVisibilityByRadius();
}


// 8. Popup für Fahrrad
function createBikePopupContent(bike) {
  const bikeType = bike.is_electric ? "E-Bike" : "Normales Fahrrad";
  const buttonLabel = bike.is_favorite
    ? "Aus Favoriten entfernen"
    : "Als Favorit markieren";

  return `
    <strong>Bike ${bike.bike_number}</strong><br>
    ${bikeType}<br>
    <button onclick="toggleFavorite('${bike.bike_number}', ${bike.is_favorite ? "true" : "false"})">
      ${buttonLabel}
    </button>
  `;
}


// 9. Marker löschen
function clearBikeMarkers() {
  bikeMarkers.forEach(function (marker) {
    map.removeLayer(marker);
  });

  bikeMarkers = [];
}


// 10. Icon für normale Bikes, E-Bikes, Favoriten und graue Bikes
function getBikeIcon(bike, options = {}) {
  let iconText = "🚲";
  let iconClass = "";

  if (bike.is_electric) {
    iconText = "⚡";
    iconClass = "bike-icon--electric";
  }

  if (bike.is_favorite) {
    iconText = "⭐";
    iconClass = "bike-icon--favorite";
  }

  if (options.greyedOut) {
    iconText = "⚪";
    iconClass = "bike-icon--grey";
  }

  return L.divIcon({
    html: `<div class="bike-icon ${iconClass}">${iconText}</div>`,
    className: "",
    iconSize: [30, 30],
    iconAnchor: [15, 15]
  });
}


// 11. Favoriten anzeigen
async function showFavoriteBikes() {
  try {
    if (!apiKeyUser) {
      alert("Bitte zuerst einloggen, um Favoriten anzuzeigen.");
      return;
    }

    currentBikeView = "favorites";

    if (USE_FAKE_DATA) {
      const favoriteBikeNumbers = ["1002", "1004"];
      markFavoritesOnMap(favoriteBikeNumbers);
      return;
    }

    // Re-load bikes so the favourites-only view always uses current data.
    await showAllBikes();
  } catch (error) {
    console.error(error);
    alert("Favoriten konnten nicht geladen werden.");
  }
}


// 12. Favoriten auf der Karte markieren
function markFavoritesOnMap(favoriteBikeNumbers) {
  allBikes = allBikes.map(function (bike) {
    return {
      ...bike,
      is_favorite: favoriteBikeNumbers.includes(bike.bike_number)
    };
  });

  renderBikesForCurrentView();
}


// 13. Fahrrad als Favorit markieren
async function toggleFavorite(bikeNumber, isFavorite) {
  try {
    if (USE_FAKE_DATA) {
      allBikes = allBikes.map(function (bike) {
        if (bike.bike_number !== bikeNumber) {
          return bike;
        }

        return {
          ...bike,
          is_favorite: !isFavorite
        };
      });
      renderBikesForCurrentView();
      return;
    }

    const response = await fetch(`${API_BASE_URL}/favourite`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "api-key": apiKeyUser
      },
      body: JSON.stringify({
        bike_number: bikeNumber,
        action: isFavorite ? "remove" : "add"
      })
    });

    if (!response.ok) {
      throw new Error("Fehler beim Aktualisieren des Favoriten.");
    }

    await showAllBikes();
    if (currentBikeView === "favorites") {
      renderBikesForCurrentView();
    }
  } catch (error) {
    console.error(error);
    alert("Favorit konnte nicht aktualisiert werden.");
  }
}


// 14. Nächstes Bike finden und Route anzeigen
async function findNextNextbike() {
  if (userLat === null || userLng === null) {
    alert("Bitte zuerst deinen Standort anzeigen.");
    return;
  }

  const cityUid = document.getElementById("citySelect").value;
  const electricOnly = document.getElementById("electricCheckbox").checked;

  try {
    let result;

    if (USE_FAKE_DATA) {
      result = getFakeNearestBikeResult();
    } else {
      const params = new URLSearchParams({
        city_uid: cityUid,
        location_lat_lng: `${userLat},${userLng}`,
        search_radius_in_meter: currentRadius,
        biketype_electric_yesno: electricOnly ? "yes" : "no"
      });
      const response = await fetch(`${API_BASE_URL}/nextbike?${params}`, {
        method: "GET"
      });

      if (!response.ok) {
        throw new Error("Fehler beim Finden des nächsten Fahrrads.");
      }

      result = await response.json();
    }

    const route = result.shortest_path || result.route_geojson;
    const bikeNumber = result.bikenumber || result.bike_number;

    if (route) {
      showRoute(route);
    }

    if (bikeNumber) {
      highlightSelectedBike(bikeNumber);
      alert(`Nächstes Bike: ${bikeNumber}`);
    } else {
      alert("Kein passendes Fahrrad im aktuellen Radius gefunden.");
    }
  } catch (error) {
    console.error(error);
    alert("Nächstes Fahrrad konnte nicht gefunden werden.");
  }
}


// 15. Route als GeoJSON anzeigen
function showRoute(routeGeoJson) {
  if (routeLayer !== null) {
    map.removeLayer(routeLayer);
  }

  routeLayer = L.geoJSON(routeGeoJson).addTo(map);
  map.fitBounds(routeLayer.getBounds());
}


// 16. Route entfernen
function clearRoute() {
  if (routeLayer !== null) {
    map.removeLayer(routeLayer);
    routeLayer = null;
  }
}


// 17. Ausgewähltes Bike hervorheben, andere ausgrauen
function highlightSelectedBike(selectedBikeNumber) {
  bikeMarkers.forEach(function (marker) {
    const bike = marker.bikeData;

    if (bike.bike_number === selectedBikeNumber) {
      if (!map.hasLayer(marker)) {
        marker.addTo(map);
      }
      marker.setIcon(getBikeIcon(bike));
      marker.openPopup();
    } else {
      marker.setIcon(getBikeIcon(bike, { greyedOut: true }));
    }
  });
}


// 18. Nur Bikes innerhalb des Radius anzeigen
function updateBikeVisibilityByRadius() {
  if (userLat === null || userLng === null) {
    return;
  }

  bikeMarkers.forEach(function (marker) {
    const bike = marker.bikeData;

    const distance = map.distance(
      [userLat, userLng],
      [bike.lat, bike.lng]
    );

    if (distance <= currentRadius) {
      if (!map.hasLayer(marker)) {
        marker.addTo(map);
      }
      marker.setIcon(getBikeIcon(bike));
    } else if (map.hasLayer(marker)) {
      map.removeLayer(marker);
    }
  });
}


// 19. Buttons und Slider verbinden
function setupEventListeners() {
  const locateBtn = document.getElementById("locateBtn");
  const radiusSlider = document.getElementById("radiusSlider");
  const radiusValue = document.getElementById("radiusValue");
  const loadBikesBtn = document.getElementById("loadBikesBtn");
  const favoriteBikesBtn = document.getElementById("favoriteBikesBtn");
  const nearestBikeBtn = document.getElementById("nearestBikeBtn");
  const clearRouteBtn = document.getElementById("clearRouteBtn");

  locateBtn.addEventListener("click", function () {
    showUserLocation();
  });

  radiusSlider.addEventListener("input", function () {
    const newRadius = Number(radiusSlider.value);

    radiusValue.textContent = newRadius;

    // If no GPS yet, draw circle on Bonn centre so slider is always visible
    if (userLat === null || userLng === null) {
      userLat = 50.7374;
      userLng = 7.0982;
    }

    setSearchRadius(newRadius);
  });

  loadBikesBtn.addEventListener("click", function () {
    currentBikeView = "all";
    showAllBikes();
  });

  favoriteBikesBtn.addEventListener("click", function () {
    showFavoriteBikes();
  });

  nearestBikeBtn.addEventListener("click", function () {
    findNextNextbike();
  });

  clearRouteBtn.addEventListener("click", function () {
  clearRoute();
});
}


// 20. Fake-Fahrräder zum Testen
function getFakeBikes() {
  return [
    {
      bike_number: "1001",
      lat: 50.7378,
      lng: 7.1000,
      is_electric: false
    },
    {
      bike_number: "1002",
      lat: 50.7355,
      lng: 7.0965,
      is_electric: true
    },
    {
      bike_number: "1003",
      lat: 50.7410,
      lng: 7.1050,
      is_electric: false
    },
    {
      bike_number: "1004",
      lat: 50.7320,
      lng: 7.0920,
      is_electric: true
    }
  ];
}


// 21. Fake-Route zum Testen
function getFakeNearestBikeResult() {
  return {
    bike_number: "1002",
    route_geojson: {
      type: "Feature",
      geometry: {
        type: "LineString",
        coordinates: [
          [userLng, userLat],
          [7.0965, 50.7355]
        ]
      },
      properties: {}
    }
  };
}


// 22. App starten
initMap();
setupEventListeners();