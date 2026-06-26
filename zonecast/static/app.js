// ── State ────────────────────────────────────────────────────────────────────
let currentHour = 12;
let currentDow  = 1;
let selectedZone = null;
let geojsonLayer = null;
let zoneMap = {};        // zone_id -> { layer, pred }
let zoneNames = {};      // zone_id -> name
let forecastChart = null;
let allPreds = {};       // zone_id -> predicted_rides

// ── Map init ─────────────────────────────────────────────────────────────────
const map = L.map('map', {
  center: [40.754, -73.984],
  zoom: 12,
  zoomControl: true,
});

L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '© OpenStreetMap © CartoDB',
  maxZoom: 19,
}).addTo(map);

// ── Color scale ───────────────────────────────────────────────────────────────
function lerpColor(a, b, t) {
  const ah = parseInt(a.slice(1), 16);
  const bh = parseInt(b.slice(1), 16);
  const ar = (ah >> 16) & 0xff, ag = (ah >> 8) & 0xff, ab = ah & 0xff;
  const br = (bh >> 16) & 0xff, bg = (bh >> 8) & 0xff, bb = bh & 0xff;
  const r = Math.round(ar + (br - ar) * t);
  const g = Math.round(ag + (bg - ag) * t);
  const b2 = Math.round(ab + (bb - ab) * t);
  return `rgb(${r},${g},${b2})`;
}

function demandColor(pred, maxPred) {
  const ratio = Math.min(pred / Math.max(maxPred, 1), 1.0);
  if (ratio < 0.5) return lerpColor('#22c55e', '#eab308', ratio * 2);
  return lerpColor('#eab308', '#ef4444', (ratio - 0.5) * 2);
}

function getZoneMax() {
  const vals = Object.values(allPreds);
  return vals.length ? Math.max(...vals) : 100;
}

// ── Load zones & draw map ────────────────────────────────────────────────────
fetch('/zones')
  .then(r => r.json())
  .then(geojson => {
    // Build zone name lookup
    geojson.features.forEach(f => {
      const id = f.properties.LocationID || f.properties.location_id;
      const name = f.properties.zone || f.properties.Zone || `Zone ${id}`;
      if (id) zoneNames[parseInt(id)] = name;
    });

    geojsonLayer = L.geoJSON(geojson, {
      style: feature => {
        const id = parseInt(feature.properties.LocationID || feature.properties.location_id);
        const pred = allPreds[id] || 0;
        return {
          fillColor: demandColor(pred, getZoneMax()),
          fillOpacity: 0.65,
          weight: 1,
          color: '#1e2235',
          opacity: 0.8,
        };
      },
      onEachFeature: (feature, layer) => {
        const id = parseInt(feature.properties.LocationID || feature.properties.location_id);
        const name = zoneNames[id] || `Zone ${id}`;
        zoneMap[id] = { layer };

        layer.on('mouseover', function() {
          if (id !== selectedZone) {
            this.setStyle({ weight: 2, color: '#4f7cff', fillOpacity: 0.8 });
          }
          const pred = allPreds[id] || 0;
          this.bindTooltip(
            `<strong>${name}</strong><br>${pred} predicted rides`,
            { sticky: true, className: 'zone-tooltip' }
          ).openTooltip();
        });

        layer.on('mouseout', function() {
          if (id !== selectedZone) {
            geojsonLayer.resetStyle(this);
            refreshLayerStyle(id);
          }
          this.closeTooltip();
        });

        layer.on('click', () => showForecast(id, name));
      }
    }).addTo(map);

    // Initial prediction load
    loadAllPredictions();
  });

// ── Load predictions for all zones ───────────────────────────────────────────
function loadAllPredictions() {
  fetch(`/predict_all?hour=${currentHour}&dow=${currentDow}`)
    .then(r => r.json())
    .then(data => {
      allPreds = {};
      for (const [k, v] of Object.entries(data)) {
        allPreds[parseInt(k)] = v;
      }
      refreshAllStyles();
      // Refresh selected zone forecast if one is active
      if (selectedZone) {
        showForecast(selectedZone, zoneNames[selectedZone] || `Zone ${selectedZone}`);
      }
    });
}

function refreshAllStyles() {
  if (!geojsonLayer) return;
  const maxPred = getZoneMax();
  geojsonLayer.eachLayer(layer => {
    const id = parseInt(
      layer.feature.properties.LocationID || layer.feature.properties.location_id
    );
    const pred = allPreds[id] || 0;
    layer.setStyle({
      fillColor: demandColor(pred, maxPred),
      fillOpacity: id === selectedZone ? 0.9 : 0.65,
      weight: id === selectedZone ? 2.5 : 1,
      color: id === selectedZone ? '#4f7cff' : '#1e2235',
    });
  });
}

function refreshLayerStyle(id) {
  if (!geojsonLayer) return;
  const maxPred = getZoneMax();
  const pred = allPreds[id] || 0;
  const layer = zoneMap[id]?.layer;
  if (layer) {
    layer.setStyle({
      fillColor: demandColor(pred, maxPred),
      fillOpacity: 0.65,
      weight: 1,
      color: '#1e2235',
    });
  }
}

// ── Forecast chart ────────────────────────────────────────────────────────────
function showForecast(zoneId, zoneName) {
  selectedZone = zoneId;
  refreshAllStyles();

  fetch(`/forecast?zone=${zoneId}&hour=${currentHour}&dow=${currentDow}`)
    .then(r => r.json())
    .then(windows => {
      // Show chart container, hide placeholder
      document.querySelector('.zone-info.placeholder').style.display = 'none';
      const cc = document.getElementById('chart-container');
      cc.classList.remove('hidden');

      const currentPred = allPreds[zoneId] || windows[0]?.predicted_rides || 0;

      document.getElementById('zone-name').textContent = zoneName;
      document.getElementById('zone-rides').textContent = `${currentPred} rides predicted now`;
      document.getElementById('zone-badge').textContent = `Zone ${zoneId}`;

      const labels = windows.map(w => w.label);
      const values = windows.map(w => w.predicted_rides);

      if (forecastChart) forecastChart.destroy();

      const ctx = document.getElementById('forecast-chart').getContext('2d');
      forecastChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [{
            label: 'Predicted rides',
            data: values,
            borderColor: '#4f7cff',
            backgroundColor: 'rgba(79,124,255,0.12)',
            borderWidth: 2.5,
            pointBackgroundColor: '#4f7cff',
            pointRadius: 4,
            tension: 0.3,
            fill: true,
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: ctx => `${ctx.parsed.y} rides`
              }
            }
          },
          scales: {
            x: {
              ticks: { color: '#7b82a0', font: { size: 10 } },
              grid: { color: '#2e3248' }
            },
            y: {
              ticks: { color: '#7b82a0', font: { size: 10 } },
              grid: { color: '#2e3248' },
              beginAtZero: true,
            }
          }
        }
      });
    });
}

// ── Controls ──────────────────────────────────────────────────────────────────
const slider = document.getElementById('hour-slider');
const hourLabel = document.getElementById('hour-label');

slider.addEventListener('input', e => {
  currentHour = parseInt(e.target.value);
  hourLabel.textContent = `${String(currentHour).padStart(2, '0')}:00`;
  loadAllPredictions();
});

document.getElementById('dow-select').addEventListener('change', e => {
  currentDow = parseInt(e.target.value);
  loadAllPredictions();
});
