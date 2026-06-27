from flask import Flask, request, jsonify, render_template
import joblib
import numpy as np
import json

app = Flask(__name__)

model = joblib.load('model/xgboost_zonecast.pkl')

# Real lag values from test set, per zone per hour
with open('static/zone_hour_lags.json') as f:
    ZONE_HOUR_LAGS = json.load(f)

def build_feature_row(zone_id, hour, dow=1):
    is_weekend = 1 if dow >= 5 else 0
    month = 3

    # Look up real lag values
    zone_data = ZONE_HOUR_LAGS.get(str(zone_id), {})
    hour_data = zone_data.get(str(hour), {})

    # Fallback if missing
    lag_15min     = hour_data.get('lag_15min', 20.0)
    lag_1hr       = hour_data.get('lag_1hr', 20.0)
    lag_24hr      = hour_data.get('lag_24hr', 20.0)
    lag_1week     = hour_data.get('lag_1week', 20.0)
    lag_2week     = hour_data.get('lag_2week', 20.0)
    roll_mean_3hr = hour_data.get('roll_mean_3hr', 20.0)
    roll_mean_1day= hour_data.get('roll_mean_1day', 20.0)

    return [
        hour, dow, month, is_weekend, 0,
        lag_15min, lag_1hr, lag_24hr,
        lag_1week, lag_2week,
        roll_mean_3hr, roll_mean_1day,
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
