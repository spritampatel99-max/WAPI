import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# OpenWeatherMap API key (from environment variable or default)
API_KEY = os.getenv("OPENWEATHER_API_KEY", "").strip() or "38507cdaabcd185f6e5030946d69c48b"

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

WMO_MAP = {
    0: ("Clear sky", "01d"),
    1: ("Mainly clear", "02d"),
    2: ("Partly cloudy", "03d"),
    3: ("Overcast", "04d"),
    45: ("Fog", "50d"),
    48: ("Depositing rime fog", "50d"),
    51: ("Light drizzle", "09d"),
    53: ("Moderate drizzle", "09d"),
    55: ("Dense drizzle", "09d"),
    61: ("Slight rain", "10d"),
    63: ("Moderate rain", "10d"),
    65: ("Heavy rain", "10d"),
    71: ("Slight snow", "13d"),
    73: ("Moderate snow", "13d"),
    75: ("Heavy snow", "13d"),
    80: ("Light rain showers", "09d"),
    81: ("Moderate rain showers", "09d"),
    82: ("Heavy rain showers", "09d"),
    95: ("Thunderstorm", "11d"),
    96: ("Thunderstorm with hail", "11d"),
    99: ("Severe thunderstorm", "11d"),
}


def fetch_open_meteo_weather(city_name):
    """Fallback weather provider using Open-Meteo (requires no API key)."""
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=en&format=json"
    geo_res = requests.get(geo_url, timeout=10).json()

    if not geo_res.get("results"):
        return None, "City not found. Please enter a valid city."

    result = geo_res["results"][0]
    lat = result["latitude"]
    lon = result["longitude"]
    city = result.get("name", city_name.title())
    country = result.get("country_code", "")

    weather_url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
    )
    w_res = requests.get(weather_url, timeout=10).json()
    curr = w_res.get("current", {})

    code = curr.get("weather_code", 0)
    desc, icon = WMO_MAP.get(code, ("Clear sky", "01d"))

    weather = {
        "city": city,
        "country": country,
        "temperature": round(curr.get("temperature_2m", 0)),
        "feels_like": round(curr.get("apparent_temperature", 0)),
        "humidity": curr.get("relative_humidity_2m", 0),
        "wind": round(curr.get("wind_speed_10m", 0), 1),
        "description": desc,
        "icon": icon,
        "source": "Open-Meteo (Live Weather)"
    }
    return weather, None


@app.route("/", methods=["GET", "POST"])
def index():
    weather = None
    error = None
    city = "Delhi"

    if request.method == "POST":
        city = request.form.get("city", "").strip()

    if not city:
        error = "Please enter a city name."
        return render_template("index.html", weather=weather, error=error, city=city)

    # Try OpenWeatherMap first if API_KEY is present
    if API_KEY:
        try:
            response = requests.get(
                OPENWEATHER_URL,
                params={
                    "q": city,
                    "appid": API_KEY,
                    "units": "metric"
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                weather = {
                    "city": data["name"],
                    "country": data["sys"]["country"],
                    "temperature": round(data["main"]["temp"]),
                    "feels_like": round(data["main"]["feels_like"]),
                    "humidity": data["main"]["humidity"],
                    "wind": round(data["wind"]["speed"], 1),
                    "description": data["weather"][0]["description"].title(),
                    "icon": data["weather"][0]["icon"],
                    "source": "OpenWeatherMap"
                }
                return render_template("index.html", weather=weather, error=None, city=city)

            elif response.status_code == 404:
                error = "City not found. Please enter a valid city."
                return render_template("index.html", weather=None, error=error, city=city)

        except requests.RequestException:
            pass

    # Fallback to Open-Meteo so the app always works smoothly without missing/inactive key errors
    try:
        weather, error = fetch_open_meteo_weather(city)
    except Exception:
        error = "Unable to connect to weather service."

    return render_template(
        "index.html",
        weather=weather,
        error=error,
        city=city
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    print(f"API Key configured: {bool(API_KEY)}")
    print(f"Running on http://127.0.0.1:{port}")
    app.run(debug=True, port=port)

