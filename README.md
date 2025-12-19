# codex_test_yellow_pages

Prompt, od którego zacząłem:
Chcę napisać aplikację w Pythonie i poniżej Ci wrzucę taki pierwszy pomysł, który mam, natomiast to, żebyś mi pomógł dopracować dobry prompt, który wrzucę do kodeksu. Także dopytaj mnie o wiele rzeczy, wypytaj się o szczegóły, tak żebyśmy razem zapisali wszystkie założenia. A poniżej wklejam to, co już mam. Chciałbym mieć napisaną w Pytonie aplikację, którą będę wykorzystywać do brainstormingu. Chcę, żeby była maksymalnie prosta i żeby też kod był maksymalnie prosty i maksymalnie przejrzysty. Chcę, żebyś napisał backend w Pytonie. Ono ma robić coś takiego, że różni uczestniczy dostają link do tej aplikacji, wprowadzają swoje imię, a potem, tak jak podczas brzmu mózgów, mają żółte karteczki, powiedzmy delikatnie różny odcień, żółte, pomarańczowe, tego typu jasne, jasno-zielone karteczki o różnych odcieniach, każdy uczestnik. No i może takie pomysły przyklejać na tablicy. Czyli ma karteczkę, na tej kartece wpisuje jakiś pomysł, gdzieś go może umieścić. I mamy taką fazę generowania pomysłów, a jak zakończymy fazę generowania pomysłów, to możemy oceniać te pomysły. I tylko tyle. I chcę, żeby nic więcej ta aplikacja dodatkowo nie robiła.

Prompt, na którym zakończyliśmy po około 1h pracy:
PROMPT 0 — Reguły pracy (wklej jako pierwszy, jednorazowo)

Masz budować aplikację webową do brainstormingu w Pythonie. Pracujemy iteracyjnie w etapach. Zasady:

Implementuj wyłącznie to, co jest opisane w bieżącym etapie. Nie dodawaj funkcji z kolejnych etapów.

Kod ma być maksymalnie prosty i czytelny. Unikaj “enterprise patterns”.

Wszystkie komponenty aplikacji muszą być open-source.

Brak bazy danych: stan w RAM.

Brak cookies/localStorage/sesji użytkownika.

Udostępnienie na zewnątrz: wyłącznie Cloudflare Tunnel (free) – będzie dopiero w ostatnim etapie.

W każdym etapie podaj listę plików do utworzenia/zmiany i ich pełną zawartość.

Potwierdź krótko zrozumienie zasad i czekaj na Etap 1.

PROMPT 1 — Etap 1: Rdzeń domeny + pytest (bez Flask, bez UI)

Zaimplementuj wyłącznie rdzeń domeny (logika aplikacji) w czystym Pythonie + unit testy w pytest. Nie używaj Flask ani żadnego HTTP. Nie twórz frontendu.

Wymagania domenowe

Aplikacja ma jedną stałą tablicę (board) z fazami: GENERATING (start), VOTING, FINISHED.

Uczestnicy:

Dołączenie: name (unikalne), is_organizer (bool).

Przy dołączeniu przypisz uczestnikowi jasny kolor z predefiniowanej puli (żółte/pomarańczowe/jasnozielone). Kolor jest stały dla uczestnika.

Jeżeli name już istnieje, operacja ma się nie udać.

Karteczki:

Karteczka zawiera: id (string/uuid), text, author_name, color, x, y, created_at.

Dodawanie karteczek tylko w GENERATING.

Edycja treści po utworzeniu: brak (nie implementuj).

Przesuwanie: każdy może przesunąć dowolną karteczkę, ale nie w FINISHED.

Usuwanie: tylko autor może usunąć swoją karteczkę; nie w FINISHED.

Fazy:

Zmiana fazy: tylko organizator.

Dozwolony przebieg: GENERATING -> VOTING -> FINISHED.

W FINISHED wszystko jest read-only (brak zmian karteczek i głosów).

Głosowanie:

Aktywne tylko w VOTING.

Każdy uczestnik ma 5 punktów.

Uczestnik może przydzielić wiele punktów jednej karteczce.

Operacja “ustaw punkty” działa jak: ustaw liczbę punktów użytkownika dla konkretnej karteczki na wartość 0..5.

Walidacja: suma punktów użytkownika po tej operacji nie może przekroczyć 5.

Uczestnik może dowolnie zmieniać alokację aż do FINISHED.

Wynik karteczki = suma punktów od wszystkich uczestników.

RESET:

Tylko organizator.

Reset czyści: uczestników, karteczki, głosy.

Reset przywraca fazę GENERATING.

Kod dostępu (tylko domenowo, bez HTTP)

W domenie przechowuj access_code generowany przy inicjalizacji boardu.

Reset generuje nowy access_code.

Generowanie kodu i losowanie kolorów musi być testowalne/deterministyczne: wstrzyknij RNG (np. random.Random) do obiektu domenowego.

Architektura plików

Utwórz:

brainstorm/domain.py – logika domenowa (klasy, wyjątki, funkcje)

tests/test_domain.py – testy pytest

pyproject.toml lub requirements.txt (minimalnie) – zależnie od preferencji, ale nie dodawaj nadmiarowych narzędzi

Wymagania jakościowe

Proste, czytelne wyjątki domenowe (np. NameAlreadyExists, NotOrganizer, InvalidPhaseTransition, ForbiddenInPhase, VoteLimitExceeded, NotAuthor, NotFound).

Żadnych frameworków.

Testy mają pokrywać: unikalność imion, uprawnienia organizatora, przełączanie faz, blokady w FINISHED, zasady dodawania/przesuwania/usuwania, zasady 5 punktów, możliwość zmiany punktów, reset + nowy kod.

Na końcu podaj komendy jak uruchomić testy.

PROMPT 2 — Etap 2: Flask REST API + testy API (bez frontendu)

Zaimplementuj warstwę HTTP w Flask nad istniejącą domeną z Etapu 1. Nie twórz frontendu. Nie zmieniaj logiki domenowej poza minimalnymi poprawkami, jeśli testy wymuszą.

Wymagania

Flask app w app.py.

Stan trzymany globalnie w pamięci w procesie (jedna instancja boardu).

Każdy request do /api/* musi zawierać poprawny kod dostępu:

preferuj header: X-Access-Code.

Jeśli kod jest błędny lub brak: zwróć 401.

Użytkownik identyfikowany jest wyłącznie przez name przesyłane w body/parametrach (brak sesji).

Endpointy (JSON)

Zaimplementuj minimalnie:

GET / – prosta strona tekstowa lub JSON, która pokazuje, że serwer działa oraz obecny access_code (to będzie do rzutnika; pełny UI dopiero etap 3).

GET /api/status – zwraca fazę oraz podstawowe liczniki.

POST /api/join – body: {name, is_organizer} -> zwraca {name, is_organizer, color}; 409 gdy name zajęte.

GET /api/board – zwraca: fazę, uczestników, karteczki, wyniki głosów per karteczka, oraz dla każdej karteczki sumę punktów.

POST /api/stickies – body: {name, text, x, y} -> dodaje karteczkę.

POST /api/stickies/<id>/move – body: {name, x, y} -> przesuwa.

DELETE /api/stickies/<id> – body: {name} -> usuwa.

POST /api/phase – body: {name, phase} -> phase w {GENERATING,VOTING,FINISHED} i musi być poprawnym przejściem.

POST /api/votes – body: {name, sticky_id, points} -> ustawia punkty użytkownika dla karteczki.

POST /api/reset – body: {name} -> reset.

Mapowanie błędów

Walidacja payload: 400

Błędny access code: 401

Brak uprawnień: 403

Konflikt (name zajęte): 409

Not found: 404

Testy

Dodaj tests/test_api.py używając Flask test client:

test brak kodu → 401

test poprawny kod → 200

join/konflikt name

dodanie karteczki w GENERATING działa, w VOTING nie

phase change tylko organizer

vote limit

reset

Pliki

app.py

tests/test_api.py

ewentualnie aktualizacja requirements.txt

Na końcu podaj komendy uruchomienia serwera i testów.

PROMPT 3 — Etap 3: Minimalny frontend (HTML/CSS/JS) + polling + drag&drop

Zbuduj minimalny frontend bez frameworków. Backend API z Etapu 2 ma pozostać kompatybilny. UI ma być możliwie proste.

Widoki

Strona startowa /

pokazuje aktualny access_code (do rzutnika),

formularz: access code (wpisywane przez uczestnika), name, checkbox organizer,

po submit przechodzi do /board.

Uwaga: mimo że backend wymaga X-Access-Code, UI ma pobierać kod od użytkownika i dołączać go do każdego requestu. Nie używaj localStorage/cookies. Po odświeżeniu użytkownik znów wpisuje dane.

Widok /board

wyświetla aktualną fazę (GENERATING/VOTING/FINISHED),

renderuje karteczki na płótnie (pełna szerokość okna):

karteczki jako absolutnie pozycjonowane div,

tekst, autor, (opcjonalnie liczba punktów),

drag&drop:

po upuszczeniu wyślij move endpoint,

polling:

co 2–3 sekundy pobierz /api/board i odśwież UI.

dodawanie karteczki:

w fazie GENERATING: prosty input tekstu + przycisk “Add”,

po dodaniu ustaw domyślne x/y (np. losowo w obrębie canvas albo stały offset), bez komplikowania klikaniem w canvas.

Tryb VOTING

przy każdej karteczce kontrolka do ustawienia punktów 0..5 dla tej karteczki (np. input number lub +/-),

pokazuj “pozostałe punkty” dla zalogowanego użytkownika (wynik z sumy jego przydziałów; jeśli API nie zwraca per-user, policz z danych w UI lub dodaj minimalne pole w /api/board).

FINISHED

read-only,

pokaż sumy punktów.

Kontrole organizatora

Jeśli is_organizer=true, pokaż przyciski:

“Start Voting” (GENERATING->VOTING),

“Finish” (VOTING->FINISHED),

“Reset”.

Dla nie-organizatora ukryj te przyciski.

Minimalny CSS

jasne “karteczki” (tło = kolor uczestnika),

bez wodotrysków.

Pliki

użyj Flask templates (templates/index.html, templates/board.html) i statics (static/app.js, static/styles.css)

dopisz routing w app.py do renderowania szablonów, ale nie psuj endpointów API.

Na końcu podaj instrukcję lokalnego uruchomienia i szybki sanity check.

PROMPT 4 — Etap 4: Hardening “warsztatowy” (minimalne limity + lepsze błędy)

Dodaj tylko minimalne usprawnienia stabilności, bez rozbudowy funkcji.

Wymagania:

limit długości tekstu karteczki (np. 200 znaków) – walidacja 400.

limit liczby karteczek na uczestnika (np. 50) – walidacja 400.

w UI czytelne komunikaty błędów (na górze strony).

dopilnuj, że w FINISHED UI nie wysyła move/vote/add/delete (i backend też blokuje).

upewnij się, że Flask działa z debug=False w instrukcji.

Dodaj/zmień testy, jeśli to konieczne. Nie dodawaj żadnych nowych “ficzerów”.

## Uruchomienie lokalne (debug=False)

```
python app.py
```

Flask działa bez trybu debug (`debug=False`).

PROMPT 5 — Etap 5: Deployment instrukcja (tylko Cloudflare Tunnel free) + porządkowanie repo

Dodaj pliki i instrukcje, aby uruchomienie było powtarzalne:

requirements.txt kompletne i minimalne.

README.md:

uruchomienie lokalne,

uruchomienie testów,

uruchomienie Cloudflare Tunnel (wyłącznie):

instalacja cloudflared,

komenda wystawienia: cloudflared tunnel --url http://127.0.0.1:PORT

co uczestnicy wpisują w przeglądarce,

jak zatrzymać tunel.

Nie dodawaj alternatyw (ngrok, port forwarding, itp.).

Nie zmieniaj domeny ani API poza kosmetyką (np. opisy). Skup się na dokumentacji.
