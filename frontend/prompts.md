hier eine liste von den prompts die benutzt wurden 
# gpt 5.4
Prompt 1: Favoriten-Header im Frontend anpassen
Ich arbeite an einer Web-Applikation namens BonnBike. Mein Python-Backend erwartet für authentifizierte Anfragen den API-Key im HTTP-Header als "X-API-KEY". Im Frontend (in der Datei `map.js`) werden Favoriten-Fahrräder mit folgendem Fetch-Aufruf geladen und gespeichert:

favoriteBikesBtn.addEventListener("click", function () {
    showFavoriteBikes();
});

Und die Funktion sieht so aus (Auszug):
async function showFavoriteBikes() {
    // ... fetch zu /api/favourite ...
}


Prompt 2: Registrierungs-Modal im Frontend aktivieren
Zeige mir bitte, wie ich die Fetch-Aufrufe in `map.js` für das Erstellen, Löschen und Anzeigen von Favoriten anpassen muss, damit der Header "X-API-KEY" mit dem Wert von `apiKeyUser` korrekt mitgeschickt wird.


In meiner `index.html` gibt es ein funktionierendes Registrierungs-Modal mit der ID `#register-modal` und ein Login-Modal mit der ID `#login-modal`. Der Button für die Registrierung im Login-Modal sieht aktuell so aus:

<button onclick="window.alert('Registrierung folgt via Backend!')" class="border-2 border-black hover:bg-slate-100 font-bold py-2 text-sm uppercase">Register</button>

Schreibe mir den kurzen JavaScript-Code oder die HTML-Anpassung, damit bei einem Klick auf diesen Button das Login-Modal geschlossen (Klasse 'hidden' hinzufügen) und das Registrierungs-Modal geöffnet (Klasse 'hidden' entfernen) wird.

Prompt 3 : JSON-Body an den WSGI-Server anpassen

"Mein Python-WSGI-Server erwartet beim Login-Endpoint (/api/login) einen JSON-Body mit den exakten Keys { "username": "...", "password": "..." }. Mein JavaScript-Frontend sendet aktuell noch { username: user, passwort: pass }. Bitte korrigiere den Fetch-Aufruf in meiner auth.js und stelle gleichzeitig sicher, dass der Port von 8080 auf 8000 geändert wird, da der Python-Server dort läuft."

Prompt 4 : Nextbike 403-Fehler (User-Agent) beheben

"In meiner Python-Datei backend/external_clients.py wirft die Nextbike-Live-API einen HTTP 403 Forbidden Fehler. Das liegt daran, dass Pythons Standard-urllib keinen Browser-Header sendet und als Bot blockiert wird. Bitte passe die Funktion read_json_url so an, dass ein gefälschter Chrome-Browser User-Agent in den request_headers mitgesendet wird, um die Blockade zu umgehen.


prompt 5:Marker-Klassen für E-Bikes und Favoriten
Ich benutze Leaflet L.divIcon, um Fahrrad-Marker auf der Karte anzuzeigen. Ich möchte die Marker optisch unterscheiden. Generiere mir CSS-Klassen für .bike-icon--electric (blauer Look), .bike-icon--favorite (kräftiger roter Look) und .bike-icon--grey (grauer Look für normale/andere Fahrräder), damit sie modern aussehen und sich farblich abheben 

prompt 6: Login-Status beim Neuladen der Seite prüfen
Ergänze ein Skript für meine auth.js, das beim Laden der Seite (Page Refresh) sofort überprüft, ob bereits ein gültiges Token im localStorage existiert. Wenn ja, soll die globale Variable apiKeyUser automatisch mit diesem Token belegt werden und die UI direkt auf 'Logout' umgestellt werden, ohne dass der User sich neu anmelden muss."