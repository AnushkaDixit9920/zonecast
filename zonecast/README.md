# ZoneCast — NYC Ride Demand Forecasting

Predicts ride pickups per Manhattan taxi zone in 15-minute windows using XGBoost trained on 23M NYC TLC trips.

## Results
| Model | RMSE | MAE |
|---|---|---|
| Baseline 1 (last week) | 14.59 | 9.04 |
| Baseline 2 (slot average) | 10.95 | 6.91 |
| **XGBoost** | **8.65** | **5.66** |
| LSTM | 17.41 | 11.33 |

**21% RMSE improvement over best baseline.**

## Stack
- Data: NYC TLC FHV High Volume (Jan–Mar 2023)
- Features: lag features, calendar features, spatial adjacency
- Model: XGBoost (gradient boosting)
- Backend: Flask
- Frontend: Leaflet.js + Chart.js

## Run locally
```bash
pip install -r requirements.txt
python app.py
```
Open http://localhost:5000

## Deploy
Push to GitHub → connect to Render → set start command: `gunicorn app:app`
