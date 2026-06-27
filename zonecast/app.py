from flask import Flask, request, jsonify, render_template
import joblib
import pandas as pd
import numpy as np
import json
import os

app = Flask(__name__)

# Load model
model = joblib.load('model/xgboost_zonecast.pkl')

# Load zone max values for color scaling (precomputed from training)
# These are approximate P95 values per zone for the color scale
# We'll use a global fallback if per-zone not available
GLOBAL_MAX = 150  # approximate P95 ride count for high-volume Manhattan zones

# Feature order must match training
FEATURES = [
    'hour', 'dow', 'month', 'is_weekend', 'is_holiday',
    'lag_15min', 'lag_1hr', 'lag_24hr', 'lag_1week', 'lag_2week',
    'roll_mean_3hr', 'roll_mean_1day', 'PULocationID'
]

# Typical average rides per zone per hour (from training data patterns)
# Used to construct realistic demo feature rows
ZONE_HOURLY_AVERAGES = {
    # High volume zones (Midtown, etc)
    161: 120, 162: 115, 163: 110, 237: 95, 236: 90,
    142: 85, 170: 80, 230: 75, 48: 70, 246: 65,
}
DEFAULT_AVG = 30

def build_feature_row(zone_id: int, hour: int, dow: int = 1) -> list:
    """Build a realistic feature vector for demo predictions."""
    is_weekend = 1 if dow >= 5 else 0
    month = 3  # March (test month)

    # Use zone average to construct plausible lag values
    avg = ZONE_HOURLY_AVERAGES.get(zone_id, DEFAULT_AVG)

    # Scale lag values by hour-of-day pattern
    hour_multiplier = {
        0: 0.3, 1: 0.2, 2: 0.15, 3: 0.1, 4: 0.15, 5: 0.3,
        6: 0.6, 7: 0.9, 8: 1.1, 9: 1.0, 10: 0.9, 11: 0.95,
        12: 1.0, 13: 0.95, 14: 0.9, 15: 0.95, 16: 1.1,
        17: 1.3, 18: 1.35, 19: 1.2, 20: 1.1, 21: 1.0,
        22: 0.9, 23: 0.6
    }.get(hour, 1.0)

    base = avg * hour_multiplier  # per 15-min window

    row = [
        hour,                    # hour
        dow,                     # dow
        month,                   # month
        is_weekend,              # is_weekend
        0,                       # is_holiday
        base * 0.95,             # lag_15min
        base * 0.9,              # lag_1hr
        base * 1.0,              # lag_24hr
        base * 1.0,              # lag_1week
        base * 0.98,             # lag_2week
        base * 0.92,             # roll_mean_3hr
        base * 1.0,              # roll_mean_1day
        zone_id,                 # PULocationID
    ]
    return row


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/predict')
def predict():
    zone_id = int(request.args.get('zone', 161))
    hour    = int(request.args.get('hour', 12))
    dow     = int(request.args.get('dow', 1))

    features = build_feature_row(zone_id, hour, dow)
    pred = float(model.predict([features])[0])
    pred = max(0, round(pred))

    return jsonify({
        'zone': zone_id,
        'hour': hour,
        'predicted_rides': pred
    })


@app.route('/predict_all')
def predict_all():
    """Return predictions for all zones at a given hour (for map coloring)."""
    hour = int(request.args.get('hour', 12))
    dow  = int(request.args.get('dow', 1))

    # Load zone IDs from GeoJSON
    with open('static/manhattan_zones.geojson') as f:
        geojson = json.load(f)

    results = {}
    for feature in geojson['features']:
        zone_id = feature['properties'].get('LocationID') or feature['properties'].get('location_id')
        if zone_id:
            zone_id = int(zone_id)
            row = build_feature_row(zone_id, hour, dow)
            pred = float(model.predict([row])[0])
            results[zone_id] = max(0, round(pred))

    return jsonify(results)


@app.route('/forecast')
def forecast():
    """Return 2-hour forecast (8 windows) for a single zone."""
    zone_id = int(request.args.get('zone', 161))
    hour    = int(request.args.get('hour', 12))
    dow     = int(request.args.get('dow', 1))

    windows = []
    for i in range(8):
        h = (hour + i // 4) % 24
        row = build_feature_row(zone_id, h, dow)
        pred = float(model.predict([row])[0])
        minutes = (i * 15) % 60
        label = f"{h:02d}:{minutes:02d}"
        windows.append({'label': label, 'predicted_rides': max(0, round(pred))})

    return jsonify(windows)


@app.route('/zones')
def zones():
    with open('static/manhattan_zones.geojson') as f:
        return jsonify(json.load(f))


if __name__ == '__main__':
    app.run(debug=True)
