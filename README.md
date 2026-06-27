# ZoneCast — NYC Ride Demand Forecasting

🔴 **Live Demo:** [zonecast.onrender.com](https://zonecast.onrender.com)

## What is this?
ZoneCast predicts how many ride pickups will happen in each of Manhattan's 69 taxi zones in the next 15 minutes. It's built on 23 million real NYC TLC trips using XGBoost — the same approach used by Uber and Lyft for driver positioning.

## The Problem
At any given moment, drivers are spread randomly across Manhattan with no idea where demand will spike next. A driver finishing a trip in Harlem at 4:30pm doesn't know whether to stay or head to Midtown. ZoneCast solves this by predicting demand 15 minutes ahead — so drivers can reposition *before* the surge, not after.

## How to Use the Demo
1. Open [zonecast.onrender.com](https://zonecast.onrender.com)
2. Drag the **hour slider** to explore demand at different times
3. Change the **day of week** — notice how weekend patterns differ from weekdays
4. **Click any zone** on the map to see a 2-hour demand forecast
5. Try **5pm Friday** → Midtown lights up red (evening rush)
6. Try **2am Saturday** → Downtown/Meatpacking area surges (nightlife)

## Results
| Model | RMSE | MAE |
|---|---|---|
| Baseline 1 — same time last week | 14.59 | 9.04 |
| Baseline 2 — historical slot average | 10.95 | 6.91 |
| **XGBoost** | **8.65** | **5.66** |
| LSTM (PyTorch) | 17.41 | 11.33 |

**XGBoost beat both baselines by 21% on RMSE.**

## Technical Stack
- **Data:** NYC TLC FHV High Volume trips (Jan–Mar 2023), 23M rows
- **Features:** Lag features (15min → 2 weeks), calendar features, rolling averages
- **Models:** XGBoost (winner), LSTM (comparison)
- **Backend:** Flask (Python)
- **Frontend:** Leaflet.js (map) + Chart.js (forecast chart)
- **Deployment:** Render

## Project Structure
```
zonecast/
├── app.py                          # Flask backend + prediction API
├── model/
│   └── xgboost_zonecast.pkl        # Trained XGBoost model
├── static/
│   ├── app.js                      # Map + chart logic
│   ├── style.css                   # Dark theme UI
│   ├── manhattan_zones.geojson     # Zone boundaries for Leaflet
│   └── zone_hour_lags.json         # Real lag values per zone per hour
└── templates/
    └── index.html                  # Main page
```

## Run Locally
```bash
pip install flask joblib xgboost scikit-learn
python app.py
# Open http://localhost:5000
```
