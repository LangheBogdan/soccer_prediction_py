# Database Schema

## Overview

The Soccer Prediction application uses PostgreSQL (production) or SQLite (development/testing) with SQLAlchemy ORM. The schema is designed to support match prediction with comprehensive historical data and prediction tracking.

## Entity Relationship Diagram

```
Leagues
├── Teams (many-to-one)
│   ├── TeamStats (one-to-many)
│   └── Matches (one-to-many, home/away)
├── Matches (one-to-many)
│   ├── MatchStats (one-to-many)
│   ├── Odds (one-to-many)
│   └── Predictions (one-to-many)
        ├── Users (many-to-one)
        └── PredictionResults (one-to-one)
│
ModelMetrics (independent, for model performance tracking)
```

## Tables

### 1. **leagues**
Stores football league information (e.g., Premier League, La Liga).

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| id | INTEGER | PRIMARY KEY | Unique league identifier |
| name | VARCHAR(255) | NOT NULL, UNIQUE | League name |
| country | VARCHAR(100) | NOT NULL | Country of league |
| season | VARCHAR(9) | NOT NULL | Season (e.g., "2024-25") |
| league_type | ENUM | DEFAULT 'domestic' | Type: domestic, international, cup |
| external_id | VARCHAR(100) | UNIQUE, NULLABLE | ID from external API |
| created_at | DATETIME | DEFAULT NOW() | Record creation timestamp |
| updated_at | DATETIME | DEFAULT NOW() | Last update timestamp |

**Indexes:**
- `league_country_season` (country, season)

---

### 2. **teams**
Football team information belonging to a league.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| id | INTEGER | PRIMARY KEY | Unique team identifier |
| name | VARCHAR(255) | NOT NULL | Team name |
| country | VARCHAR(100) | NOT NULL | Country |
| league_id | INTEGER | NOT NULL, FK(leagues.id) | Home league |
| founded_year | INTEGER | NULLABLE | Year team was founded |
| external_id | VARCHAR(100) | NULLABLE | ID from external API |
| created_at | DATETIME | DEFAULT NOW() | Record creation timestamp |
| updated_at | DATETIME | DEFAULT NOW() | Last update timestamp |

**Indexes:**
- `team_league_id` (league_id)
- `team_name` (name)

**Cascade:** Delete teams when league is deleted

---

### 3. **matches**
Individual match data including results and performance metrics.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| id | INTEGER | PRIMARY KEY | Unique match identifier |
| league_id | INTEGER | NOT NULL, FK(leagues.id) | Associated league |
| home_team_id | INTEGER | NOT NULL, FK(teams.id) | Home team |
| away_team_id | INTEGER | NOT NULL, FK(teams.id) | Away team |
| match_date | DATETIME | NOT NULL | Match date and time |
| home_goals | INTEGER | NULLABLE | Goals scored by home team |
| away_goals | INTEGER | NULLABLE | Goals scored by away team |
| status | ENUM | DEFAULT 'scheduled' | scheduled, live, finished, postponed, cancelled |
| home_shots | INTEGER | NULLABLE | Home team shot count |
| away_shots | INTEGER | NULLABLE | Away team shot count |
| home_shots_on_target | INTEGER | NULLABLE | Home team shots on target |
| away_shots_on_target | INTEGER | NULLABLE | Away team shots on target |
| home_possession | FLOAT | NULLABLE | Home team possession % |
| away_possession | FLOAT | NULLABLE | Away team possession % |
| home_passes | INTEGER | NULLABLE | Home team pass count |
| away_passes | INTEGER | NULLABLE | Away team pass count |
| home_pass_accuracy | FLOAT | NULLABLE | Home team pass accuracy % |
| away_pass_accuracy | FLOAT | NULLABLE | Away team pass accuracy % |
| home_fouls | INTEGER | NULLABLE | Home team fouls |
| away_fouls | INTEGER | NULLABLE | Away team fouls |
| home_yellow_cards | INTEGER | NULLABLE | Home team yellow cards |
| away_yellow_cards | INTEGER | NULLABLE | Away team yellow cards |
| home_red_cards | INTEGER | NULLABLE | Home team red cards |
| away_red_cards | INTEGER | NULLABLE | Away team red cards |
| external_id | VARCHAR(100) | UNIQUE, NULLABLE | ID from external API |
| created_at | DATETIME | DEFAULT NOW() | Record creation timestamp |
| updated_at | DATETIME | DEFAULT NOW() | Last update timestamp |

**Indexes:**
- `match_league_date` (league_id, match_date)
- `match_status` (status)
- `match_external_id` (external_id)

**Cascade:** Delete related odds and predictions when match is deleted

---

### 4. **team_stats**
Aggregated season statistics for teams.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| id | INTEGER | PRIMARY KEY | Unique record identifier |
| team_id | INTEGER | NOT NULL, FK(teams.id) | Associated team |
| season | VARCHAR(9) | NOT NULL | Season identifier |
| matches_played | INTEGER | DEFAULT 0 | Total matches played |
| wins | INTEGER | DEFAULT 0 | Total wins |
| draws | INTEGER | DEFAULT 0 | Total draws |
| losses | INTEGER | DEFAULT 0 | Total losses |
| goals_for | INTEGER | DEFAULT 0 | Total goals scored |
| goals_against | INTEGER | DEFAULT 0 | Total goals conceded |
| goal_difference | INTEGER | DEFAULT 0 | GF - GA |
| points | INTEGER | DEFAULT 0 | Total points (3 for win, 1 for draw) |
| avg_possession | FLOAT | NULLABLE | Average possession percentage |
| avg_shots | FLOAT | NULLABLE | Average shots per match |
| avg_shots_on_target | FLOAT | NULLABLE | Average shots on target per match |
| created_at | DATETIME | DEFAULT NOW() | Record creation timestamp |
| updated_at | DATETIME | DEFAULT NOW() | Last update timestamp |

**Indexes:**
- `team_stats_team_season` (team_id, season)

**Cascade:** Delete stats when team is deleted

---

### 5. **match_stats**
Detailed statistics from various sources for a match.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| id | INTEGER | PRIMARY KEY | Unique record identifier |
| match_id | INTEGER | NOT NULL, FK(matches.id) | Associated match |
| source | VARCHAR(50) | NOT NULL | Data source (fbref, api_football, etc.) |
| data_json | TEXT | NULLABLE | Raw JSON data from source |
| created_at | DATETIME | DEFAULT NOW() | Record creation timestamp |
| updated_at | DATETIME | DEFAULT NOW() | Last update timestamp |

**Indexes:**
- `match_stats_match_id` (match_id)
- `match_stats_source` (source)

**Cascade:** Delete stats when match is deleted

---

### 6. **odds**
Betting odds for matches from various bookmakers.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| id | INTEGER | PRIMARY KEY | Unique record identifier |
| match_id | INTEGER | NOT NULL, FK(matches.id) | Associated match |
| bookmaker | VARCHAR(100) | NOT NULL | Bookmaker name |
| home_win_odds | NUMERIC(6,2) | NOT NULL | Odds for home win |
| draw_odds | NUMERIC(6,2) | NOT NULL | Odds for draw |
| away_win_odds | NUMERIC(6,2) | NOT NULL | Odds for away win |
| over_2_5_odds | NUMERIC(6,2) | NULLABLE | Over 2.5 goals odds |
| under_2_5_odds | NUMERIC(6,2) | NULLABLE | Under 2.5 goals odds |
| retrieved_at | DATETIME | NOT NULL | When odds were retrieved |
| created_at | DATETIME | DEFAULT NOW() | Record creation timestamp |
| updated_at | DATETIME | DEFAULT NOW() | Last update timestamp |

**Indexes:**
- `odds_match_bookmaker` (match_id, bookmaker)
- `odds_retrieved_at` (retrieved_at)

**Cascade:** Delete odds when match is deleted

---

### 7. **users**
User accounts for prediction tracking and history.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| id | INTEGER | PRIMARY KEY | Unique user identifier |
| username | VARCHAR(100) | NOT NULL, UNIQUE | Username |
| email | VARCHAR(255) | NOT NULL, UNIQUE | User email |
| password_hash | VARCHAR(255) | NOT NULL | Hashed password |
| is_active | BOOLEAN | DEFAULT TRUE | Account active status |
| created_at | DATETIME | DEFAULT NOW() | Account creation timestamp |
| updated_at | DATETIME | DEFAULT NOW() | Last update timestamp |

**Indexes:**
- `user_username` (username)
- `user_email` (email)

**Cascade:** Delete user's predictions when user is deleted

---

### 8. **predictions**
User predictions for matches.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| id | INTEGER | PRIMARY KEY | Unique prediction identifier |
| user_id | INTEGER | NOT NULL, FK(users.id) | User who made prediction |
| match_id | INTEGER | NOT NULL, FK(matches.id) | Match being predicted |
| predicted_outcome | ENUM | NOT NULL | home_win, draw, away_win |
| confidence | FLOAT | NOT NULL | Confidence score (0.0 to 1.0) |
| stake | NUMERIC(10,2) | NULLABLE | Betting stake amount |
| odds_used | NUMERIC(6,2) | NULLABLE | Odds at time of prediction |
| notes | TEXT | NULLABLE | User notes |
| created_at | DATETIME | DEFAULT NOW() | Prediction creation timestamp |
| updated_at | DATETIME | DEFAULT NOW() | Last update timestamp |

**Indexes:**
- `prediction_user_id` (user_id)
- `prediction_match_id` (match_id)
- `prediction_created_at` (created_at)

**Cascade:** Delete result when prediction is deleted

---

### 9. **prediction_results**
Evaluation of predictions after match results.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| id | INTEGER | PRIMARY KEY | Unique record identifier |
| prediction_id | INTEGER | NOT NULL, FK(predictions.id), UNIQUE | Associated prediction |
| actual_outcome | ENUM | NOT NULL | home_win, draw, away_win |
| is_correct | BOOLEAN | NOT NULL | Whether prediction was correct |
| profit_loss | NUMERIC(10,2) | NULLABLE | Profit or loss if stake recorded |
| return_rate | FLOAT | NULLABLE | Return on investment % |
| evaluated_at | DATETIME | NOT NULL | When result was evaluated |

**Indexes:**
- `prediction_result_prediction_id` (prediction_id)
- `prediction_result_is_correct` (is_correct)

**Cascade:** Delete result when prediction is deleted

---

### 10. **model_metrics**
ML model performance metrics for historical tracking.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| id | INTEGER | PRIMARY KEY | Unique record identifier |
| model_version | VARCHAR(50) | NOT NULL | Model version string |
| training_date | DATETIME | NOT NULL | Date model was trained |
| accuracy | FLOAT | NOT NULL | Model accuracy (0.0 to 1.0) |
| precision | FLOAT | NOT NULL | Model precision |
| recall | FLOAT | NOT NULL | Model recall |
| f1_score | FLOAT | NOT NULL | F1 score |
| auc_score | FLOAT | NULLABLE | AUC-ROC score |
| samples_used | INTEGER | NOT NULL | Number of training samples |
| created_at | DATETIME | DEFAULT NOW() | Record creation timestamp |

**Indexes:**
- `model_metrics_version` (model_version)
- `model_metrics_training_date` (training_date)

---

## Enums

### MatchStatus
- `scheduled` - Match not yet played
- `live` - Match currently in progress
- `finished` - Match completed
- `postponed` - Match delayed
- `cancelled` - Match cancelled

### PredictionOutcome
- `home_win` - Home team victory
- `draw` - Equal result
- `away_win` - Away team victory

### LeagueType
- `domestic` - Domestic league
- `international` - International/continental competition
- `cup` - Cup/knockout tournament

---

## Key Constraints

### Foreign Keys
All foreign key relationships use cascade delete for data integrity:
- League → Teams
- League → Matches
- Teams → Matches (home/away)
- Teams → TeamStats
- Matches → MatchStats
- Matches → Odds
- Matches → Predictions
- Users → Predictions
- Predictions → PredictionResults

### Unique Constraints
- `leagues.name` - League names must be unique
- `leagues.external_id` - External API IDs must be unique
- `teams.external_id` - External team IDs must be unique
- `matches.external_id` - External match IDs must be unique
- `users.username` - Usernames must be unique
- `users.email` - Emails must be unique
- `prediction_results.prediction_id` - One result per prediction

---

## Database Initialization

### Creating Tables

```python
from src.db import init_db
init_db()
```

### Seeding Initial Data

```bash
python -m src.db.init_db --seed
```

### Dropping Tables (Development Only)

```bash
python -m src.db.init_db --drop --force
```

---

## Connection Configuration

Database connection is configured via environment variables:

```env
# PostgreSQL (production)
DB_ENGINE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=soccer_prediction
DB_USER=postgres
DB_PASSWORD=your_password

# Or SQLite (development)
DB_ENGINE=sqlite
DB_PATH=data/soccer_prediction.db

# Or explicit URL
DATABASE_URL=postgresql://user:password@localhost/dbname
```

---

## Performance Considerations

1. **Indexes** are placed on frequently queried columns:
   - League/date combinations for match queries
   - Team IDs for relationships
   - User IDs for prediction queries
   - Status for filtering matches

2. **Connection Pooling** is enabled with:
   - Pool pre-ping to verify live connections
   - Connection recycling every 1 hour

3. **Foreign Key Constraints** ensure data integrity with cascade deletes

4. **JSON Storage** in `match_stats` allows flexible data from different sources
