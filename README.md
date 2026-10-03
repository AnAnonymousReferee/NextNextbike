## Backend-Frontend Integration

Der Backend-Server bietet sowohl die REST-API als auch die statischen Frontend-Dateien an.

### Server starten

```powershell
cd c:\Users\carl\Documents\POOSE
.venv\Scripts\python.exe backend/server.py
```

Dann im Browser öffnen:

```text
http://127.0.0.1:8000/
```

### Wichtige Umgebungsvariablen

- `ORS_API_KEY` — notwendig für die OpenRouteService-Routinganfragen
- `BONNBIKE_DB_PATH` — optionaler Pfad zur SQLite-Datenbank (Standard: `bonnbike.sqlite3`)
- `SMTP_HOST` — optional, falls E-Mail-Versand aktiviert werden soll
- `SMTP_PORT` — optional, Standard: `587`
- `SMTP_USERNAME` / `SMTP_PASSWORD` — optional für SMTP-Authentifizierung
- `MAIL_FROM` — Absenderadresse für Passwort-Reset-E-Mails
- `PASSWORD_RESET_URL_TEMPLATE` — Link-Template für Passwort-Reset-E-Mails

### Frontend-Verbindung

Die Frontend-Dateien befinden sich in `frontend/`.
Das Backend dient die Dateien direkt aus, sodass keine separate Frontend-Serverkonfiguration nötig ist.

### Funktionen

- `GET /api/nextbike` — nächstes Bike finden
- `GET /api/bikes` — verfügbare Bikes und Favoriten laden
- `POST /api/login` — Login per Benutzername und Passwort
- `POST /api/register` — Registrierung
- `POST /api/password-reset` — Passwort-Zurücksetzen anstoßen
- `POST /api/password-reset/confirm` — neues Passwort setzen
- `POST /api/favourite` — Bike als Favorit speichern

Wenn du weitere Anpassungen für das Frontend brauchst, helfe ich dir beim Erstellen der API-Requests oder der Darstellung auf der Karte.
