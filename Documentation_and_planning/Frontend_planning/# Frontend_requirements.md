# Frontend_requirements

Das Frontend hat die folgenden Aufgaben: 

## Karte:

Der hauptteil der Website is die Karte. 

### Standorte anzeigen

#### Fahrräder

`showAllBikes()` 

mit der backend-api (siehe [hier](../API_Documentation/Backend API.md)) soll eine liste aller fahrräder geholt werden. Dann soll für jedes das nextbike-symbol platziert werden, je nachdem ob elektrisch angeklickt ist oder nicht dementsprechend auch elektrische mit anderm symbol. 

#### Favorite Fahrräder

`showFavoriteBikes(api_key_user)`

soll die favorites auf Karte malen mit sternchen dran.

#### als favorite markieren

`markAsFavorite(api_key_user, bike_number)`

soll dem Backend das favorite schicken. Dafür soll man beim hovern oder klicken auf das Fahrradsymbol auf der Karte einen Button bereitgestellt bekommen.

#### Nutzer

`showUserLocation()` 

Es soll geschaut werden, on javascript erlaubnis hat auf das built-in gps vom browser zuzugreifen. Dann wird das gemacht oder der Nutzer um erlaubnis gefragt. Dann soll das auf der Karte angezeigt werden 

### nächstens nextbike und Weg anzeigen

`findNextNextbike()`

Sobald der Nutzer auf "find next nextbike" klickt, soll die aktuelle location des users sowie alle nötigen daten (siehe [hier](../API_Documentation/Backend API.md)) an das Backend weitergeleitet werden. Dann schickt das BE eine geoJSON mit dem Weg zurück. die sollten wir dann mit folium und leaflet einbinden. Alle Fahrradsymbole außer das ausgewählte sollten ausgegraut werden. 

OPTIONAL: Falls wir noch booking implementieren, soll ein button erscheiben über dem Fahrrad mit book drauf, sowie


### Einstellungen

1. `setSearchRadius()`: Es soll eine Einstellung für den Suchradius geben, mit einem slider. Auf der Karte soll der Kreis mit dem Radius um den Nutzer angezeigt werden, die Räder nicht im Radius sollen grau sein

2. `setCity()` Es soll eine Einstellung für den Standort geben, bei dem man die Stadt ändern kann. Die Städte soll das fontend am besten

3. `setSearchForElectricBikes()` Es soll eine tickbox für elektrische Fahrräder oder nicht geben.

4. `setBookingTrue()` OPTIONAL falls wir booking implementieren soll es einen tick geben für automatisch bookeing, aber nur wenn man angebemldet ist.

## Anmeldung

`login(email, password)`

soll den user beim Backend anmelden. Returned einen API-key für den user.

`register(email. password)`

soll den user beim Backend registrieren.