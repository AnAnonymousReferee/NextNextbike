# BACKEND API:

## Sicherheit

- Userdaten werden in SQL gespeichert.
- Passwoerter werden nur als Salted Hash (`password_hash`) gespeichert, nie im Klartext.
- Externe APIs werden ausschliesslich ueber HTTPS angesprochen.

## GET
calling `getNextNextbike()` with 
```
    queries = {city_uid, location_lat_lng, search_radius_in_meter, biketype_electric_yesno}
``` 
returns json in format:
```
    {
        "shortest_path": geoJSON,
        "bikenumber": xxxxxxx
    }
```
returns `200: ok, 400: input invalid`

calling `getAllBikes()` with
``` 
    header = {api_key_user}
    queries = {city_uid, biketype_electric_yesno}
``` 
returns json in format:
```
    {
        "bike_locations": [[lat,lng],...],
        "favourites":  [[lat,lng], ...]
    }
```
returns `200: ok, 400: input invalid`

## POST

calling `userLogin()` with 
```
    queries = {username, passwort}
```
returns json
```
    {
        "api_key": xxxxxx
    }
```
returns `200: ok, 400: wrong password/username`

calling `register_user()` with
```
    queries = {username, passwort, email}
```
returns no json.
returns `200: ok, 400: internal server error`

calling `change_password()` with
```
    queries = {email}
```
returns no json
returns `200: ok, 400: user does not exist`

calling `markFav()` with
```
    header = {api-key}
    queries = {bike_number}
```
returns no json
returns `200: ok, 400: user does not exist`
