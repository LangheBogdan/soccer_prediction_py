Soccer Prediction App - To-Do List

This list is based on the project description and workflow diagram, structured for incremental development.

Phase 1: Project Setup & Environment

[ ] Define Project Structure: Map out the directory structure (e.g., /src, /data, /models, /docker, /tests).

[ ] Docker Configuration:

[ ] Create Dockerfile for the main Python application.

[ ] Create Docker compose.yml (using the compose spec, not legacy docker-compose) to orchestrate the services (Python app, Database).

[ ] Database Setup:

[ ] Choose Database: Select a database (e.g., PostgreSQL, MySQL, or MongoDB) suitable for storing match data, stats, and predictions.

[ ] Configure Database: Add the chosen database service to the Docker compose.yml.

[ ] Environment & Secrets:

[ ] Create a .env.template file to list required environment variables (API keys, DB credentials).

[ ] Implement a Python module (e.g., using python-dotenv) to securely load variables from the .env file.

[ ] Python Environment:

[ ] Create a pyproject.toml (or requirements.txt) listing initial dependencies (e.g., Flask/FastAPI, requests, beautifulsoup4, pandas, scikit-learn, psycopg2-binary/pymongo).

[ ] Frontend Setup:

[ ] Create a directory for frontend assets (e.g., /src/static or /ui).

[ ] Set up the Tailwind CSS build process (install via npm/yarn, create tailwind.config.js, and set up a build script) as requested, not using the CDN.

Phase 2: Data Acquisition

[ ] Database Schema: Design and implement the database schema (tables/collections) for:

[ ] Leagues, Teams, Matches

[ ] Historical Stats (from fbref)

[ ] Odds (from Odds API)

[ ] Predictions & Results

[ ] Web Scraper (fbref.com):

[ ] Develop a Python module (e.g., using requests and BeautifulSoup4 or Scrapy) to scrape data from the 6 specified fbref.com URLs.

[ ] Implement functions to parse and clean the scraped data.

[ ] API Client (External Data):

[ ] Create a Python module for football-data.org API calls.

[ ] Create a Python module for api-football.com API calls.

[ ] Data Ingestion Pipeline:

[ ] Create a main script (ingest.py?) that uses the scraper and API clients to fetch data.

[ ] Write the logic to format and save this data into the database.

[ ] Implement error handling for failed data retrieval.

Phase 3: Backend Development (API)

[ ] Choose Framework: Select a Python web framework (e.g., FastAPI or Flask).

[ ] Create API Endpoints (based on diagram):

[ ] GET /api/matches: Fetches matches for a selected league and period.

Corresponds to: "Selectează Liga & Perioada" -> "Afișare Listă Meciuri"

[ ] GET /api/match/{match_id}/details: Gets advanced metrics for a selected match.

Corresponds to: "Selectează un Meci" -> "Afișare Analiză Detaliată"

[ ] POST /api/match/{match_id}/predict: Triggers the ML prediction.

Corresponds to: "Apasă Generează Predicție" -> "Afișare Predicție Finală"

[ ] POST /api/prediction/{prediction_id}/save: Saves a generated prediction to the DB.

Corresponds to: "Salvare Predicție în Bază"

[ ] GET /api/history: Retrieves all saved predictions and calculates performance.

Corresponds to: "Apasă Vezi Istoric" -> "Afișare Tablou de Bord Istoric"

[ ] GET /api/match/{match_id}/odds: Fetches betting odds (button click).

Corresponds to: "Get Betting Odds" (from text)

[ ] Error Handling: Implement API-level error responses for:

[ ] "Nu S-au Găsit Meciuri" (No Matches Found)

[ ] "Metricile/Cotele Indisponibile" (Metrics/Odds Unavailable)

[ ] "Script Predicție Eșuat" (Prediction Script Failed)

[ ] "Eroare Salvare" (Save Error)

[ ] "Istoric Indisponibil" (History Unavailable)

Phase 4: Machine Learning Model

[ ] Data Preprocessing: Develop scripts to clean, transform, and feature-engineer the data from the database.

[ ] Model Selection: Research, prototype, and select a suitable ML model (e.g., Logistic Regression, Random Forest, XGBoost).

[ ] Model Training: Write a script to train the selected model on historical data.

[ ] Model Evaluation: Write a script to evaluate the model's performance (accuracy, precision, recall).

[ ] Save Model: Serialize and save the trained model (e.g., as a .pkl or .joblib file).

[ ] Prediction Script: Create the Python function (Script ML: Analiză & Generare Predicție) that loads the trained model, takes match data as input, and returns a prediction.

[ ] Integrate Model: Ensure the POST /api/match/{match_id}/predict endpoint correctly calls this prediction script.

Phase 5: Frontend (UI) Development

[ ] Base Template: Create the main index.html file linked to the compiled Tailwind CSS.

[ ] JavaScript Logic: Create a main app.js file to handle frontend logic (API calls, DOM updates).

[ ] UI Components:

[ ] League/Period Selection: Build the dropdowns and date pickers.

[ ] Match List: Build the view to display the list of matches (Afișare Listă Meciuri).

[ ] Detailed Analysis View: Build the modal/page to show metrics and the "Get Odds" button (Afișare Analiză Detaliată).

[ ] Prediction View: Build the UI to display the final prediction (Afișare Predicție Finală) and "Save" button.

[ ] History Dashboard: Build the page to display historical predictions, accuracy, and profit/loss (Afișare Tablou de Bord Istoric).

[ ] Interactivity:

[ ] Wire the "Vezi Meciuri" button to call GET /api/matches.

[ ] Make matches in the list clickable to call GET /api/match/{match_id}/details.

[ ] Wire the "Get Odds" button to call GET /api/match/{match_id}/odds.

[ ] Wire the "Generează Predicție" button to call POST /api/match/{match_id}/predict.

[ ] Wire the "Save" button to call POST /api/prediction/{prediction_id}/save.

[ ] Wire the "Vezi Istoric" button to call GET /api/history.

[ ] UI Feedback: Implement loading spinners and display all error/success messages from the API.

Phase 6: Testing & Documentation

[ ] Unit Tests (Backend):

[ ] Write pytest tests for the data scraper module.

[ ] Write pytest tests for the external API client modules.

[ ] Write pytest tests for the API endpoints (mocking DB and ML model).

[ ] Unit Tests (ML):

[ ] Write pytest tests for the prediction script.

[ ] Integration Tests:

[ ] Test the full flow: API call -> ML prediction -> DB save.

[ ] Frontend Testing:

[ ] Manually test all UI interactions and error states.

[ ] (Optional) Set up frontend testing (e.g., with Jest or Cypress).

[ ] Documentation:

[ ] Create/update README.md with setup and run instructions.

[ ] Document the API endpoints.

[ ] Maintain the CLAUDE.md file as per your methodology.
