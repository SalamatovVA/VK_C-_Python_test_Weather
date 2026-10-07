import subprocess
import json
import time
from urllib.parse import quote


def load_cities(filename):
    cities = []
    try:
        with open(filename, 'r', encoding='utf-8-sig') as f:
            for line in f:
                city = line.strip()
                if city:
                    cities.append(city)
    except FileNotFoundError:
        print(f"Файл {filename} не найден!")
        return []

    return list(dict.fromkeys(cities))


class WeatherData:
    def __init__(self, city, temp, country, order):
        self.city = city
        self.temp = temp
        self.country = country
        self.order = order  

    def __str__(self):
        sign = "+" if self.temp >= 0 else ""
        return f"{self.city}, {self.country} {sign}{self.temp} °C"


def fetch_weather_curl(city, max_retries=3, curl_timeout=30):
    safe_city = quote(city)
    url = f"https://wttr.in/{safe_city}?format=j1"
    print(F"Ожидаем данные по {safe_city}...")

    for attempt in range(1, max_retries + 1):
        try:
            result =  subprocess.run(
                [
                    "curl",
                    "-s",
                    "-S",
                    "-L",
                    "--ssl-no-revoke",
                    "--compressed",                           
                    "-H", "Accept: application/json",  
                    "-H", "Accept-Language: en-US,en;q=0.9",
                    "-H", "Connection: keep-alive",
                    "--max-time", str(curl_timeout),
                    "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36",   
                    url
                ],
                capture_output=True,          
            )

            stdout_bytes = result.stdout
            stderr_bytes = result.stderr

            if result.returncode != 0:
                err_text = _safe_decode(stderr_bytes).strip()
                raise RuntimeError(
                    f"{result.returncode}: {err_text}"
                )

            
            
            body = _safe_decode(stdout_bytes)

            if not body.strip():
                raise RuntimeError("пустое тело ответа")

            return json.loads(body)

        except Exception as e:
            print(f"  Попытка {attempt}/{max_retries} для {city}: {e}")

        if attempt < max_retries:
            time.sleep(3)

    return None


def _safe_decode(data: bytes) -> str:
    if data is None:
        return ""
    for enc in ("utf-8", "windows-1251", "cp866", "latin-1"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def main():
    cities = load_cities('Cities.txt')
    if not cities:
        print("Список городов пуст.")
        return


    weather_records = []

    for idx, city in enumerate(cities):
        data = fetch_weather_curl(city)

        if data is None:
            continue


        current_temp = int(data['current_condition'][0]['temp_C'])
        country = data['nearest_area'][0]['country'][0]['value']
        record = WeatherData(city, current_temp, country, order=idx)
        weather_records.append(record)
        print(f"[OK] {city}: {current_temp}°C, {country}\n")

        time.sleep(1.5) #Паузы, так-как я встречал информацию, что wttr может забанить за частые запросы


    print("\n--- Вывод по городам ---")
    for record in sorted(weather_records, key=lambda r: r.order):
        print(record)


    print("\n--- Статистика по странам ---")

    country_stats = {}
    for record in weather_records:
        country_stats.setdefault(record.country, []).append(record.temp)

    def fmt(t):
        return f"+{t}" if t >= 0 else str(t)

    for country, temps in sorted(country_stats.items()):
        count = len(temps)
        avg_temp = sum(temps) / count
        print(
            f"{country} — {count} cities, "
            f"avg: {fmt(round(avg_temp))} °C, "
            f"min: {fmt(min(temps))} °C, "
            f"max: {fmt(max(temps))} °C"
        )


if __name__ == "__main__":
    main()