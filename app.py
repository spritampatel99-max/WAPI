import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import requests
from flask import Flask, jsonify, render_template, request
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)
log = logging.getLogger("skycast")
logging.basicConfig(level=logging.INFO)

GEO = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST = "https://api.open-meteo.com/v1/forecast"
AIR = "https://air-quality-api.open-meteo.com/v1/air-quality"

http = requests.Session()  # reused connection + automatic retry on flaky/overloaded responses
http.mount("https://", HTTPAdapter(max_retries=Retry(total=2, backoff_factor=0.4, status_forcelist=(429, 500, 502, 503, 504))))
pool = ThreadPoolExecutor(4)
_cache, TTL, MAX = {}, 600, 200  # key -> (timestamp, data); 10 min; max 200 entries
_hits = {}  # ip -> recent suggest-request times (rate limit)
COMPASS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def get(url, timeout=8, **params):
    r = http.get(url, params=params, timeout=timeout)  # params= handles URL encoding
    r.raise_for_status()
    return r.json()


def decode(code, day=1):
    """WMO weather code -> (description, emoji, scene)."""
    if code == 0:
        return "Clear sky", "☀️" if day else "🌙", "clear"
    if code in (1, 2):
        return "Partly cloudy", "⛅" if day else "☁️", "cloudy"
    if code == 3:
        return "Overcast", "☁️", "cloudy"
    if code in (45, 48):
        return "Fog", "🌫️", "fog"
    if 51 <= code <= 57:
        return "Drizzle", "🌦️", "rain"
    if 61 <= code <= 67 or 80 <= code <= 82:
        return "Rain", "🌧️", "rain"
    if 71 <= code <= 77 or code in (85, 86):
        return "Snow", "❄️", "snow"
    return "Thunderstorm", "⛈️", "storm"


def aqi_text(lat, lon):
    try:
        v = get(AIR, timeout=4, latitude=lat, longitude=lon, current="us_aqi")["current"]["us_aqi"]
        label = next(l for m, l in ((50, "Good"), (100, "Moderate"), (150, "Unhealthy for some"),
                                    (200, "Unhealthy"), (300, "Very unhealthy"), (999, "Hazardous")) if v <= m)
        return round(v), f"{round(v)} · {label}"
    except Exception:  # air quality is optional
        log.warning("AQI unavailable")
        return None, "N/A"


def moon(day):
    """(emoji, name) of the moon phase on an ISO date."""
    age = (date.fromisoformat(day) - date(2000, 1, 6)).days % 29.530588  # days since a known new moon
    i = int(age / 29.530588 * 8 + 0.5) % 8
    return "🌑🌒🌓🌔🌕🌖🌗🌘"[i], ("New moon", "Waxing crescent", "First quarter", "Waxing gibbous", "Full moon", "Waning gibbous", "Last quarter", "Waning crescent")[i]


def advice(t, scene, rain, uv, aqi):
    """One practical sentence + a level ('warn' / 'ok')."""
    if t >= 40: return "warn", "Extreme heat. Stay indoors in the afternoon and drink plenty of water."
    if scene == "storm": return "warn", "Thunderstorms nearby. Stay indoors and keep away from open areas."
    if aqi and aqi > 150: return "warn", "Air quality is poor. Limit time outdoors and consider a mask."
    if scene == "rain" or (rain or 0) >= 60: return "ok", "Rain is likely today. Take an umbrella."
    if uv is not None and uv >= 8: return "warn", "UV is very high. Use sunscreen and find shade around midday."
    if scene == "snow" or t <= 5: return "ok", "It's cold out. Wear warm layers."
    return "ok", "Conditions look comfortable. A good day to be outside."


def day_label(s):
    t = date.fromisoformat(s)
    return f"{t:%a} {t.day}"


def load(city, lat, lon):
    name, country = "Your location", ""
    if city:
        found = get(GEO, name=city, count=1, language="en").get("results")
        if not found:
            raise LookupError(city)
        f = found[0]
        lat, lon, name, country = f["latitude"], f["longitude"], f["name"], f.get("country", "")
    air = pool.submit(aqi_text, lat, lon)  # runs in parallel with the forecast call
    w = get(FORECAST, latitude=lat, longitude=lon, timezone="auto", wind_speed_unit="ms", forecast_days=6,
            current="temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,surface_pressure,is_day,cloud_cover,wind_direction_10m",
            hourly="temperature_2m,precipitation_probability",
            daily="weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,uv_index_max,precipitation_probability_max")
    c, d, h = w["current"], w["daily"], w["hourly"]
    if not city:
        country = w.get("timezone", "").split("/")[-1].replace("_", " ")
    i = h["time"].index(c["time"][:13] + ":00")  # current hour, in the city's own timezone
    desc, icon, scene = decode(c["weather_code"], c["is_day"])
    uv = d["uv_index_max"][0]
    aq, aqt = air.result()
    return {
        "city": name, "country": country, "desc": desc, "icon": decode(c["weather_code"], 1)[1], "nicon": decode(c["weather_code"], 0)[1], "scene": scene, "night": not c["is_day"],
        "temp": round(c["temperature_2m"]), "feels": round(c["apparent_temperature"]),
        "humidity": c["relative_humidity_2m"], "wind": round(c["wind_speed_10m"], 1),
        "pressure": round(c["surface_pressure"]), "uv": "–" if uv is None else round(uv),
        "sunrise": (d["sunrise"][0] or "–")[-5:], "sunset": (d["sunset"][0] or "–")[-5:], "aqi": aqt, "cloud": c["cloud_cover"], "dir": COMPASS[round(c["wind_direction_10m"] / 45) % 8],
        "hi": round(d["temperature_2m_max"][0]), "lo": round(d["temperature_2m_min"][0]), "moon": moon(c["time"][:10]),
        "tip": advice(c["temperature_2m"], scene, d["precipitation_probability_max"][0], uv, aq),
        "hours": [{"t": h["time"][j][-5:], "c": round(h["temperature_2m"][j]), "p": h["precipitation_probability"][j] or 0} for j in range(i, i + 24)],
        "days": [{"d": day_label(d["time"][k]), "icon": decode(d["weather_code"][k])[1],
                  "hi": round(d["temperature_2m_max"][k]), "lo": round(d["temperature_2m_min"][k]),
                  "rain": d["precipitation_probability_max"][k]} for k in range(1, 6)],
    }


def fetch(city, lat, lon):
    key = city.lower() if city else (round(lat, 2), round(lon, 2))
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    try:
        data = load(city, lat, lon)
    except LookupError:
        raise
    except Exception:
        if hit:  # serve slightly old data rather than an error page
            log.warning("upstream failed, serving stale data for %s", key)
            return hit[1]
        raise
    if len(_cache) >= MAX:  # keep memory bounded
        _cache.pop(next(iter(_cache)))
    _cache[key] = (time.time(), data)
    return data


@app.after_request
def secure(r):
    r.headers.update({
        "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'self'; style-src 'self' https://fonts.googleapis.com; "
                                   "font-src https://fonts.gstatic.com; script-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self'"})
    return r


@app.route("/")
def index():
    city = request.args.get("city", "").strip()[:80]
    lat, lon = request.args.get("lat", type=float), request.args.get("lon", type=float)
    status, weather, error = 200, None, None
    if not city and lat is None and lon is None:
        city = "Delhi"
    elif not city and not (lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180):
        status, error = 400, "That location isn't valid. Search by city name instead."
    if not error:
        try:
            weather = fetch(city, lat, lon)
        except LookupError:
            status, error = 404, f"We couldn't find “{city}”. Check the spelling or try a nearby city."
        except Exception:
            log.exception("weather fetch failed")
            status, error = 502, "The weather service isn't responding. Try again in a moment."
    return render_template("index.html", w=weather, error=error, city=city), status


@app.route("/api/suggest")
def suggest():
    now, ip = time.time(), request.remote_addr
    hits = [t for t in _hits.get(ip, []) if now - t < 60]
    if len(_hits) > 1000: _hits.clear()
    if len(hits) >= 40:  # max 40 lookups/minute per visitor
        return jsonify([]), 429
    _hits[ip] = hits + [now]
    q = request.args.get("q", "").strip()[:60]
    if len(q) < 2:
        return jsonify([])
    try:
        found = get(GEO, timeout=5, name=q, count=6, language="en").get("results") or []
    except Exception:
        return jsonify([])
    return jsonify([{"n": r["name"], "l": ", ".join(x for x in (r["name"], r.get("admin1"), r.get("country")) if x)} for r in found])


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", port=int(os.getenv("PORT", 5001)))  # 5001: macOS uses 5000
