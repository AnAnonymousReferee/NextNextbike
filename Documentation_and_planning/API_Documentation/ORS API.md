## ORS APIS

# Kürzester Weg
siehe auch hier[https://openrouteservice.org/dev/#/api-docs/v2/directions/{profile}/get]
So funktioniert die ORS API: Um den Kürzesten Weg zu getten, nutze GET:
``` 
    https://api.openrouteservice.org/v2/directions/foot-walking/
```
mit den folgenden queries/headers: 
``` 
    headers = {"Authorization": "DEIN_API_KEY"},
    queries = {"start": "8.660,49.415", "end": "8.678,49.406"}
``` 
(den api key müssen wir bereitstellen: dafür macht man einen account, dann haben wir 2500 freie requests für daily use von directions, 500 für matrix (s.u.), hier[https://staging.openrouteservice.org/plans/] die Quelle)

Das returned ein json im geoJSON format: das ist standard, und da die gängigen Varianten der python-libs das direkt verarbeiten können, gibt es keinen Grund, hier reinzuschauen. 


# Das nächstegelegene Fahrrad
siehe auch hier[https://giscience.github.io/openrouteservice/api-reference/endpoints/matrix/]
Um zwischen den sagen wir 3 oder so nächsten bikes zu entscheiden: nutze den Matrix dienst, dh.
``` 
    https://api.openrouteservice.org/v2/matrix/foot-walking/
```

mit den queries: 
``` 
    {"locations":[[lat_1,lng_1],[lat_2,lng_2],[lat_3,lng_3],[lat_4,lng_4]], "sources":[0], "destinations": [1,2,3]}
```
wobei wir uns darauf festlegen dass hier der erste angegebene ort der Startpunkt der Person ist. Diese Daten liefert uns die nextbike api (in luflinie die nächsten 5 positionen z.b.)

das returned ein json im format:

```
    {"durations:[0 sec, xxxx.xx, ..., xxxx.xx], ...}
```

Die Einträge sind in seconds. Uns interessiert nur das erste array, das sind die Distanzen von dem ersten angegebenen Punkt aus.
Dann können wir den actually kürzesten aussuchen, z.B. um zu verhindern dass man über den Fluss muss oder so.