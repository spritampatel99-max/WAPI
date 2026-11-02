# SkyCast

Weather app: live conditions, hour-by-hour graph, 5-day outlook, air quality, day/night themes.
Stack: Python + Flask, Jinja HTML, CSS, vanilla JavaScript + SVG. Data: Open-Meteo (free, no API key).

## Run
    python -m venv venv
    venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
    pip install -r requirements.txt
    python app.py                  # http://127.0.0.1:5001

Optional env vars: `PORT`, `FLASK_DEBUG=1` (development only). Production: `gunicorn app:app`.

## Structure
    app.py                 routes, Open-Meteo calls, cache, security headers, /api/suggest
    templates/index.html   page markup (HTML)
    static/css/style.css   all styling, themes and animation (CSS)
    static/js/chart.js     hourly graph + tooltip (JavaScript)
    static/js/app.js       day/night, units, particles, search helpers (JavaScript)

Shortcuts: `/` focus search, `D` flip day/night.
