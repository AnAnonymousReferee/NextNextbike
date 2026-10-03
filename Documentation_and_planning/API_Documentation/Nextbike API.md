## ** So funktioniert die API von Nextbike **

um das json zu getten, verwende einfach: 
```
{
    https://maps2.nextbike.net/maps/nextbike-{scope}.{format}
}
``` 
Dabei ist scope entweder "live" (alle Plätze) oder "official" (keine floating bikes). Ferner haben wir die folgenden Queries:

1. `"city" : uid` (für Bonn: 1170, man kann auch mehrere mit , trennen. MAchen wir nur Bonn? sonst wird das nervig herauszufinden...)
2. (`"countries": alpha-2-code` (zum beispiel Deutschland = DE)) brauchen wir eventuell nicht, stört aber nicht.
3. `"lat"` und `"lng"` latidude und longitude. die sind nörig für das nächste: 
4. `bike_distance : meter` distanz in meter die von lat, long weg sind
5. `search : bike number` für die favorite bikes 

Als Beispiel: Bonn, Münsterplatz, 250 m radius
```
{
    https://maps2.nextbike.net/maps/nextbike-live.json?city=1170&lat=50.733334&lng=7.100000&bike_distance=250
}
``` 

das returned eine json in folgendem format:
```
{
    {
        "countries:
        {
            "lat": 50.7147
            "lng": 7.12875
            .
            .
            "cities":
            {
                uid: 1170,
                "lat": 50.7147,
                "lng": 7.12875,
                .
                .
                places:
                {
                    {
                        "uid": 10044348, 
                        "lat": 50.70068,
                        "lng": 7.100987,
                        .
                        .
                        "bikes_available_to_rent": 11,
                        .
                        .
                        "bike_list": {
                            {"number": "535218", "bike_type": 196, ...},
                            .
                            .
                        },
                        .
                        .
                        "bike_types":  {"196" : 8, "349": 3},
                        .
                        .
                    },
                    .
                    .
                }
            }

        } 
    
    }
}
``` 
Das heißt für uns relevant sind: die lat und long in places, sowie der biketype (196 sind normal sowie 349 elektrisch glaub ich)

## 