# Soccer Prediction - Startup Guide

## Quick Start (2 minutes)

### 1. **Activate Virtual Environment**
```bash
source venv/bin/activate
```

### 2. **Start the API Server**
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### 3. **Open in Browser**
```
http://localhost:8000/
```

That's it! The application will load with full styling.

---

## What's Included

- **Frontend**: HTML with Tailwind CSS, responsive design
- **Backend API**: FastAPI with PostgreSQL/SQLite support
- **Database**: SQLite (dev) with sample data (6 leagues + 50 matches)
- **ML Model**: Trained prediction model ready to use

## Features Available

1. **Select League** - Choose from 6 sample leagues
2. **View Matches** - See available matches with stats
3. **Get Predictions** - AI-powered match outcome predictions
4. **Track History** - Save and monitor prediction accuracy
5. **View Odds** - Betting odds from multiple bookmakers

## API Endpoints

- `GET /api/leagues` - List all leagues
- `GET /api/leagues/{id}/matches` - Get matches for a league
- `GET /api/matches/{id}` - Get match details
- `POST /api/ml/predict/match/{id}` - Generate prediction
- `GET /api/ml/model/metrics` - Model performance stats

## Troubleshooting

### Styles Not Loading?
- Clear browser cache (Ctrl+Shift+Delete)
- Check that the API is running on port 8000
- Verify CSS file exists: `src/static/css/output.css`

### API Not Responding?
```bash
# Check if process is running
ps aux | grep uvicorn

# Kill and restart
pkill uvicorn
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### Database Issues?
```bash
# Reinitialize with sample data
source venv/bin/activate
python3 -m src.db.init_db --drop --force --seed
```

## File Structure

```
src/
├── static/
│   ├── index.html          # Main frontend
│   ├── js/app.js          # Frontend JavaScript
│   └── css/
│       ├── input.css       # Tailwind source
│       └── output.css      # Compiled CSS (14 KB)
├── api/
│   └── main.py            # FastAPI app
└── db/
    └── init_db.py         # Database setup
```

## Default Credentials

- **User ID**: 1 (hardcoded for demo)
- **Database**: SQLite at `data/soccer_prediction.db`
- **Port**: 8000

---

**Happy predicting!** ⚽🤖
