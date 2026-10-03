# Backend-planning:

Das Backend hat die folgenden Aufgaben: 

## Nutzeranfrage nach nächstem bike (GET)

benötigter input: Stadt (als UID), location (in lat & lng), Radius (in meter), biketype (ob auch elektrisch).
Diese funktion fragt dann in die [nextbike API](../API_Documentation/Nextbike API.md) an und soll die in luftlinie nächsten 5? bikes liefern. Dann wird der kürzeste Weg mit [ORS](../API_Documentation/ORS API.md) zu dem nächsten ausgesucht, und der wird zurück an das Frontend geschickt, als geoJSON. Soll auch die bike nummer mitschicken.

## Alle bikes (GET)

benötigter input: Stadt (als UID), biketype (ob auch elektrisch), api-key von nutzer.
Soll mit der [nextbike API](../API_Documentation/Nextbike API.md) alle möglichen bike locations (electirc ja/nein nach input) zurück an das frontend schicken, als json liste mit locations, ohne favs. Die muss das Backend also einmal raussortieren. Die favourites sollen in separater liste geschickt werden für markierung.

## Nutzer login (POST)

benötigter Input: username, passwort. Returns: api_key. Soll checken ob es den nutzer gibt natürlich, und dann einen API-key genereieren um ihn zu identifizieren, sonst fehler zurück

## Nutzer registration (POST)

benötigter input: username, email, passwort. Soll neuen Eintrag in der Tabelle kreiren für login

## passwort ändern (POST)

benötigter input: username, email. Soll email an user schicken mit link zum Passwort ändern (TODO, wie geht das???)

## bike als fav markieren (POST)

benötigter input: bike nummer, api_key. soll in der Nutzertabelle die bikenummer unter favorites speichern

---

## Daten die der Server/BE speichert

Die Nutzerdaten werden in einer SQL-Datenbank gespeichert. Passwoerter werden nie
im Klartext gespeichert, sondern nur als Salted Hash, z.B. in einer Spalte
`password_hash`.

Eine Tabelle der Form:
| API-key       | Username      | password_hash | email  | favourites  |
| ------------- |:-------------:| -------------:|-------:|------------:|

mit den offensichtlichen Einträgen, favourites als array. Abgesehen davon, der API-key von ORS, aber der ist vermutlich hard-gecoded. 

Alle Verbindungen zu externen APIs (Nextbike und ORS) sollen ueber HTTPS laufen.
