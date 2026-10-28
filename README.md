# Zadanie rekrutacyjne, AGH Space Systems Rocket Software jesień 2026

**Autor:** Piotr Herbuś

## Opis projektu
Skrypt realizujący pełną, zautomatyzowaną sekwencję lotu rakiety w symulatorze TCP. a

* **Maszyna Stanów:** 
  Logika lotu oparta jest na enumerowanych stanach misji (`MissionState`).
  
* **Asynchroniczna Telemetria (Wzorzec Callback):** 
  Odczyty z czujników (`FEED`) są nasłuchiwane w tle za pomocą zarejestrowanych callbacków (`sensors_feed`).
  
* **Aktywna weryfikacja operacji (ACK/NACK):** 
  Każda komenda sprzętowa (`SERVICE`) sterująca serwomechanizmami lub przekaźnikami wykorzystuje autorską funkcję `send_and_verify()`, oczekując na potwierdzenie `ACK` od maszyny.

* **Zarządzanie Awariami:** 
  W przypadku otrzymania sygnału `NACK` od sprzętu lub wystąpienia przekroczenia czasu (timeout sieciowy), program natychmiast przerywa misję, odcina krytyczne systemy (np. zamyka główne zawory i wyłącza zapalnik) oraz przechodzi w stan `ABORT`. 

## Przebieg misji
1. `IDLE` -> Otwarcie zaworu wlotowego utleniacza.
2. `FILLING_OXIDIZER` -> Oczekiwanie na pełen zbiornik, przełączenie zaworów na paliwo.
3. `FILLING_FUEL` -> Oczekiwanie na zatankowanie paliwa, aktywacja grzałki utleniacza.
4. `HEATING_OXYGEN` -> Oczekiwanie na ciśnienie (> 55 bar) i dezaktywacja grzałki.
5. `LAUNCH_SEQUENCE` -> Otwarcie zaworów głównych i aktywacja zapalnika. Wymaga potwierdzenia `ACK` ze wszystkich trzech urządzeń, aby dopuścić do lotu.
6. `FLIGHT` -> Ciągłe monitorowanie wektora wysokości. Wykrycie apogeum matematycznym spadkiem wartości, odcięcie układu napędowego i zrzut spadochronu.
7. `LANDING` / `ABORT` -> Oczekiwanie na bezpieczne przyziemienie.
