# SkyCast - Flask Weather App

A responsive weather interface built with HTML, CSS, Flask, and the OpenWeatherMap Current Weather API.

## 1. Get an API key
1. Create an account at https://openweathermap.org/
2. Generate an API key from your account dashboard.
3. Keep the key private. Do not paste it into your HTML or commit it to GitHub.

## 2. Install dependencies
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

## 3. Set your API key

Windows PowerShell:
```powershell
$env:OPENWEATHER_API_KEY="YOUR_API_KEY"
```

macOS/Linux:
```bash
export OPENWEATHER_API_KEY="YOUR_API_KEY"
```

## 4. Run the project
```bash
python app.py
```
Open http://127.0.0.1:5000 in your browser.

The default city is Delhi. Search for another city using the search box.
