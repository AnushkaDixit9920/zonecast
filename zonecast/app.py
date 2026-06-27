from flask import Flask, request, jsonify, render_template
import joblib
import numpy as np
import json

app = Flask(__name__)

model = joblib.load('model/xgboost_zonecast.pkl')

ZONE_HOURLY_AVERAGES = {
    4: 23.4, 12: 0.7, 13: 31.6, 24: 9.9, 41: 42.1, 42: 59.5, 43: 8.1,
    45: 18.0, 48: 69.0, 50: 41.2, 68: 78.8, 74: 44.6, 75: 42.0, 79: 102.6,
    87: 42.5, 88: 16.3, 90: 49.2, 100: 41.0, 103: 0.1, 104: 0.1, 105: 0.1,
    107: 59.8, 113: 46.5, 114: 49.2, 116: 29.3, 120: 0.5, 125: 25.0,
    127: 22.5, 128: 1.6, 137: 40.4, 140: 42.2, 141: 47.8, 142: 47.6,
    143: 38.2, 144: 54.4, 148: 75.8, 151: 20.4, 152: 15.6, 153: 5.9,
    158: 44.0, 161: 87.2, 162: 56.2, 163: 58.9, 164: 74.8, 166: 31.3,
    170: 66.3, 186: 45.9, 194: 0.5, 202: 4.2, 209: 16.3, 211: 43.4,
    224: 16.7, 229: 44.8, 230: 86.6, 231: 86.1, 232: 31.3, 233: 42.4,
    234: 80.8, 236: 55.4, 237: 59.5, 238: 36.8, 239: 45.2, 243: 34.1,
    244: 48.9, 246: 75.9, 249: 71.3, 261: 24.5, 262: 27.8, 263: 39.2
}

HOUR_MULTIPLIER = {
    0: 0.3, 1: 0.2, 2: 0.15, 3: 0.1, 4: 0.15, 5: 0.3,
    6: 0.6, 7: 0.9, 8: 1.1, 9: 1.0, 10: 0.9, 11: 0.95,
    12: 1.0, 13: 0.95, 14: 0.9, 15: 0.95, 16: 1.1,
    17: 1.3, 18: 1.35, 19: 1.2, 20: 1.1, 21: 1.0,
    22: 0.9, 23: 0.6
}

def build_feature_row(zone_id, hour, dow=1):
    is_weekend = 1 if dow >= 5 else 0
    avg = ZONE_HOURLY_AVERAGES.get(zone_id, 20.0)
    base = avg * HOUR_MULTIPLIER.get(hour, 1.0)
    return [
        hour, dow, 3, is_weekend, 0,
        base * 0.95, base * 0.9, base * 1.0,
        base * 1.0, base * 0.98,
        base * 0.92, base * 1.0,
        zone_id
    ]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict')
def predict():
    zone_id = int(request.args.get('zone', 161))
    hour    = int(request.args.get('hour', 12))
    dow     = int(request.args.get('dow', 1))
    row = build_feature_row(zone_id, hour, dow)
    pred = float(model.predict([row])[0])
    return jsonify({'zone': zone_id, 'hour': hour, 'predicted_rides': max(0, round(pred))})

@app.route('/predict_all')
def predict_all():
    hour = int(request.args.get('hour', 12))
    dow  = int(request.args.get('dow', 1))
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
    zone_id = int(request.args.get('zone', 161))
    hour    = int(request.args.get('hour', 12))
    dow     = int(request.args.get('dow', 1))
    windows = []
    for i in range(8):
        h = (hour + i // 4) % 24
        row = build_feature_row(zone_id, h, dow)
        pred = float(model.predict([row])[0])
        minutes = (i * 15) % 60
        windows.append({'label': f"{h:02d}:{minutes:02d}", 'predicted_rides': max(0, round(pred))})
    return jsonify(windows)

@app.route('/zones')
def zones():
    with open('static/manhattan_zones.geojson') as f:
        return jsonify(json.load(f))

if __name__ == '__main__':
    app.run(debug=True)