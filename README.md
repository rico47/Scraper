<img width="1192" height="615" alt="image" src="https://github.com/user-attachments/assets/4bc46b9b-1e6a-4fe2-aa86-623184a6a681" />

# Scraper
Program służy do przeszukiwania stron internetowych jak i twitter'a w celu poszukiwannia interesujących nas informacji. Dzięki integracji z zaawansowanymi modelami LLM (Gemini), narzędzie nie tylko pobiera dane, ale również analizuje je i generuje raporty zgodnie z wytycznymi użytkownika.

## Funkcje
* **Dynamiczne źródła:** Możliwość dodawania i usuwania adresów URL w czasie rzeczywistym.
* **Analiza Treści:** Wykorzystanie AI do filtrowania szumu informacyjnego i wyciągania sedna.
* **Obsługa stron dynamicznych:** Wykorzystanie Playwright do renderowania JavaScript.
* **Twitter Scraper:** Przeszukiwanie wpisów w poszukiwaniu trendów i konkretnych wzmianek.

## Wymagania
* Python 3.10+
* Klucz API Google Gemini ewentualnie własny llm
* Zainstalowane przeglądarki Playwright

## Uruchomienie

Aby uruchomić aplikację w przygotowanym środowisku wirtualnym, wykonaj poniższe komendy:

```bash
source ~/.venv/bin/activate
python main.py