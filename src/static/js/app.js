/**
 * Soccer Prediction Frontend Application
 *
 * Handles all UI interactions, API calls, and data display
 */

// Global state
const state = {
    currentMatch: null,
    currentPrediction: null,
    leagues: [],
    matches: [],
    userPredictions: []
};

// ===== Utility Functions =====

function showLoading(show = true) {
    const spinner = document.getElementById('loadingSpinner');
    if (show) {
        spinner.classList.remove('hidden');
    } else {
        spinner.classList.add('hidden');
    }
}

function showError(message) {
    alert(`Error: ${message}`);
    showLoading(false);
}

function showSuccess(message) {
    console.log(`Success: ${message}`);
    // Could be enhanced with a toast notification
}

async function apiCall(endpoint, options = {}) {
    /**
     * Make an API call to the backend
     */
    try {
        showLoading(true);
        const url = `${API_BASE_URL}${endpoint}`;
        const response = await fetch(url, {
            method: options.method || 'GET',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            body: options.body ? JSON.stringify(options.body) : undefined
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `API Error: ${response.status}`);
        }

        const data = await response.json();
        showLoading(false);
        return data;
    } catch (error) {
        showError(error.message);
        throw error;
    }
}

// ===== View Management =====

function showView(viewName) {
    /**
     * Show a specific view and hide others
     */
    document.getElementById('homeView').classList.add('hidden');
    document.getElementById('historyView').classList.add('hidden');
    document.getElementById('aboutView').classList.add('hidden');

    if (viewName === 'home') {
        document.getElementById('homeView').classList.remove('hidden');
    } else if (viewName === 'history') {
        document.getElementById('historyView').classList.remove('hidden');
        loadPredictionHistory();
    } else if (viewName === 'about') {
        document.getElementById('aboutView').classList.remove('hidden');
    }
}

// ===== League Functions =====

async function loadLeagues() {
    /**
     * Fetch and populate league dropdown
     */
    try {
        const leagues = await apiCall('/leagues');
        state.leagues = leagues;

        const select = document.getElementById('leagueSelect');
        select.innerHTML = '<option value="">Select a league...</option>';

        leagues.forEach(league => {
            const option = document.createElement('option');
            option.value = league.id;
            option.textContent = `${league.name} (${league.country})`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading leagues:', error);
    }
}

// ===== Match Functions =====

async function loadMatches() {
    /**
     * Load matches for selected league and status
     */
    const leagueId = document.getElementById('leagueSelect').value;
    const status = document.getElementById('statusSelect').value;

    if (!leagueId) {
        showError('Please select a league');
        return;
    }

    try {
        let endpoint = `/leagues/${leagueId}/matches`;
        if (status) {
            endpoint += `?status=${status}`;
        }

        const matches = await apiCall(endpoint);
        state.matches = matches;

        displayMatchList(matches);
        document.getElementById('matchListSection').classList.remove('hidden');
    } catch (error) {
        console.error('Error loading matches:', error);
    }
}

function displayMatchList(matches) {
    /**
     * Display match list in the UI
     */
    const matchList = document.getElementById('matchList');
    matchList.innerHTML = '';

    if (matches.length === 0) {
        matchList.innerHTML = '<p class="text-gray-500">No matches found</p>';
        return;
    }

    matches.forEach(match => {
        const matchDate = new Date(match.match_date).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

        const status = match.status.charAt(0).toUpperCase() + match.status.slice(1);
        const statusColor = getStatusColor(match.status);

        const matchElement = document.createElement('div');
        matchElement.className = 'border border-gray-200 rounded-lg p-4 hover:shadow-md cursor-pointer transition';
        matchElement.innerHTML = `
            <div class="flex justify-between items-center">
                <div class="flex-1">
                    <p class="font-semibold text-gray-800">${match.home_team.name} vs ${match.away_team.name}</p>
                    <p class="text-sm text-gray-600">${matchDate}</p>
                </div>
                <div class="text-right">
                    ${match.home_goals !== null ?
                        `<p class="text-xl font-bold">${match.home_goals} - ${match.away_goals}</p>`
                        : ''
                    }
                    <span class="inline-block px-3 py-1 rounded text-sm font-semibold ${statusColor}">
                        ${status}
                    </span>
                </div>
            </div>
        `;

        matchElement.addEventListener('click', () => showMatchDetails(match));
        matchList.appendChild(matchElement);
    });
}

function getStatusColor(status) {
    /**
     * Get color class for match status badge
     */
    const colors = {
        scheduled: 'bg-blue-100 text-blue-800',
        live: 'bg-red-100 text-red-800 animate-pulse',
        finished: 'bg-green-100 text-green-800',
        postponed: 'bg-yellow-100 text-yellow-800',
        cancelled: 'bg-gray-100 text-gray-800'
    };
    return colors[status] || colors.scheduled;
}

// ===== Match Details Functions =====

function showMatchDetails(match) {
    /**
     * Display match details in modal
     */
    state.currentMatch = match;

    // Update team info
    document.querySelector('#homeTeamDetail p').textContent = match.home_team.name;
    document.querySelector('#awayTeamDetail p').textContent = match.away_team.name;

    // Update scores
    document.getElementById('homeGoalsDetail').textContent =
        match.home_goals !== null ? match.home_goals : '-';
    document.getElementById('awayGoalsDetail').textContent =
        match.away_goals !== null ? match.away_goals : '-';

    // Update statistics
    const stats = [
        { id: 'homeShotsDetail', value: match.home_shots },
        { id: 'awayShotsDetail', value: match.away_shots },
        { id: 'homePossessionDetail', value: match.home_possession },
        { id: 'awayPossessionDetail', value: match.away_possession }
    ];

    stats.forEach(stat => {
        const element = document.getElementById(stat.id);
        if (element) {
            element.textContent = stat.value !== null ?
                (stat.value % 1 === 0 ? stat.value : stat.value.toFixed(1)) : '-';
        }
    });

    // Reset prediction and odds displays
    document.getElementById('oddsDisplay').classList.add('hidden');
    document.getElementById('predictionDisplay').classList.add('hidden');

    // Show modal
    document.getElementById('matchModal').classList.remove('hidden');
}

function closeMatchModal() {
    /**
     * Close match details modal
     */
    document.getElementById('matchModal').classList.add('hidden');
    state.currentMatch = null;
}

// ===== Odds Functions =====

async function getMatchOdds() {
    /**
     * Fetch and display betting odds from database
     */
    if (!state.currentMatch) {
        showError('No match selected');
        return;
    }

    try {
        const odds = await apiCall(`/odds/match/${state.currentMatch.id}`);
        displayOdds(odds);
        document.getElementById('oddsDisplay').classList.remove('hidden');
    } catch (error) {
        showError('Failed to load odds');
    }
}

async function fetchLiveOdds() {
    /**
     * Fetch live odds from the Odds API
     */
    if (!state.currentMatch) {
        showError('No match selected');
        return;
    }

    try {
        showLoading(true);
        const result = await apiCall(`/odds/match/${state.currentMatch.id}/fetch`, {
            method: 'POST'
        });

        showLoading(false);

        if (result.success) {
            showSuccess(`Fetched ${result.odds_stored} odds from ${result.odds_fetched} sources`);
            // Refresh the odds display
            await getMatchOdds();
        } else {
            if (result.errors && result.errors.length > 0) {
                showError(`Failed to fetch live odds: ${result.errors[0]}`);
            } else {
                showError('No odds available from API');
            }
        }
    } catch (error) {
        showError(error.message || 'Failed to fetch live odds');
    }
}

async function getBestOdds() {
    /**
     * Get and display best odds across all bookmakers
     */
    if (!state.currentMatch) {
        showError('No match selected');
        return;
    }

    try {
        const bestOdds = await apiCall(`/odds/match/${state.currentMatch.id}/best`);
        displayBestOdds(bestOdds);
    } catch (error) {
        showError('Failed to load best odds');
    }
}

function displayOdds(odds) {
    /**
     * Display odds in the UI
     */
    const oddsList = document.getElementById('oddsList');
    const oddsComparison = document.getElementById('oddsComparison');
    oddsList.innerHTML = '';
    oddsComparison.classList.add('hidden');

    if (!odds || odds.length === 0) {
        oddsList.innerHTML = '<p class="text-gray-500">No odds available. Click "Fetch Live Odds" to get the latest odds.</p>';
        return;
    }

    // Show odds list by default
    odds.forEach(odd => {
        const oddElement = document.createElement('div');
        oddElement.className = 'border border-gray-200 rounded-lg p-3 flex justify-between items-center hover:bg-gray-50';
        oddElement.innerHTML = `
            <span class="font-semibold text-gray-800">${odd.bookmaker}</span>
            <div class="space-x-4">
                <span class="text-sm">Home: <span class="font-semibold text-green-600">${parseFloat(odd.home_win_odds).toFixed(2)}</span></span>
                <span class="text-sm">Draw: <span class="font-semibold text-gray-600">${parseFloat(odd.draw_odds).toFixed(2)}</span></span>
                <span class="text-sm">Away: <span class="font-semibold text-blue-600">${parseFloat(odd.away_win_odds).toFixed(2)}</span></span>
            </div>
        `;
        oddsList.appendChild(oddElement);
    });

    // Add timestamp if available
    if (odds.length > 0 && odds[0].retrieved_at) {
        const timestamp = document.createElement('p');
        timestamp.className = 'text-xs text-gray-500 text-right';
        const date = new Date(odds[0].retrieved_at);
        timestamp.textContent = `Last updated: ${date.toLocaleString()}`;
        oddsList.appendChild(timestamp);
    }
}

function displayBestOdds(bestOdds) {
    /**
     * Display best odds in a comparison format
     */
    const oddsList = document.getElementById('oddsList');
    oddsList.innerHTML = '';

    const comparisonTable = document.createElement('div');
    comparisonTable.className = 'bg-gradient-to-r from-green-50 to-blue-50 border-2 border-green-300 rounded-lg p-4';
    comparisonTable.innerHTML = `
        <h4 class="font-bold text-gray-800 mb-3 flex items-center">
            <svg class="w-5 h-5 mr-2 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
            </svg>
            Best Odds Across All Bookmakers
        </h4>
        <div class="grid grid-cols-3 gap-3">
            <div class="bg-white rounded-lg p-3 shadow-sm">
                <p class="text-xs text-gray-600 mb-1">Home Win</p>
                <p class="text-2xl font-bold text-green-600">${parseFloat(bestOdds.home_win.odds).toFixed(2)}</p>
                <p class="text-xs text-gray-500 mt-1">${bestOdds.home_win.bookmaker}</p>
            </div>
            <div class="bg-white rounded-lg p-3 shadow-sm">
                <p class="text-xs text-gray-600 mb-1">Draw</p>
                <p class="text-2xl font-bold text-gray-600">${parseFloat(bestOdds.draw.odds).toFixed(2)}</p>
                <p class="text-xs text-gray-500 mt-1">${bestOdds.draw.bookmaker}</p>
            </div>
            <div class="bg-white rounded-lg p-3 shadow-sm">
                <p class="text-xs text-gray-600 mb-1">Away Win</p>
                <p class="text-2xl font-bold text-blue-600">${parseFloat(bestOdds.away_win.odds).toFixed(2)}</p>
                <p class="text-xs text-gray-500 mt-1">${bestOdds.away_win.bookmaker}</p>
            </div>
        </div>
    `;
    oddsList.appendChild(comparisonTable);
}

// ===== Prediction Functions =====

async function generatePrediction() {
    /**
     * Generate ML prediction for current match
     */
    if (!state.currentMatch) {
        showError('No match selected');
        return;
    }

    try {
        const prediction = await apiCall(`/ml/predict/match/${state.currentMatch.id}`, {
            method: 'POST'
        });

        state.currentPrediction = prediction;
        displayPrediction(prediction);
        document.getElementById('predictionDisplay').classList.remove('hidden');
    } catch (error) {
        showError('Failed to generate prediction');
    }
}

function displayPrediction(prediction) {
    /**
     * Display prediction results
     */
    const probabilities = prediction.probabilities;

    // Update probability displays
    const probs = {
        'home_win': probabilities.home_win || 0,
        'draw': probabilities.draw || 0,
        'away_win': probabilities.away_win || 0
    };

    document.getElementById('homeWinProbValue').textContent =
        `${(probs.home_win * 100).toFixed(1)}%`;
    document.getElementById('drawProbValue').textContent =
        `${(probs.draw * 100).toFixed(1)}%`;
    document.getElementById('awayWinProbValue').textContent =
        `${(probs.away_win * 100).toFixed(1)}%`;

    // Update prediction outcome
    const outcomeText = prediction.predicted_outcome
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());

    document.getElementById('predictionOutcome').textContent = outcomeText;
    document.getElementById('confidenceValue').textContent =
        `${(prediction.confidence * 100).toFixed(1)}%`;
}

async function savePrediction() {
    /**
     * Save prediction to database
     */
    if (!state.currentMatch || !state.currentPrediction) {
        showError('No prediction to save');
        return;
    }

    try {
        const predictionData = {
            user_id: CURRENT_USER_ID,
            match_id: state.currentMatch.id,
            predicted_outcome: state.currentPrediction.predicted_outcome,
            confidence: state.currentPrediction.confidence
        };

        const result = await apiCall('/predictions', {
            method: 'POST',
            body: predictionData
        });

        showSuccess('Prediction saved successfully!');
        closeMatchModal();
    } catch (error) {
        showError('Failed to save prediction');
    }
}

// ===== History Functions =====

async function loadPredictionHistory() {
    /**
     * Load user prediction history
     */
    try {
        const predictions = await apiCall(`/predictions/user/${CURRENT_USER_ID}`);
        state.userPredictions = predictions;

        // Load user statistics
        const stats = await apiCall(`/predictions/user/${CURRENT_USER_ID}/stats`);
        displayUserStats(stats);

        // Display predictions table
        displayPredictionsTable(predictions);
    } catch (error) {
        console.error('Error loading prediction history:', error);
    }
}

function displayUserStats(stats) {
    /**
     * Display user statistics
     */
    document.getElementById('totalPredictions').textContent = stats.total_predictions || 0;
    document.getElementById('correctPredictions').textContent = stats.correct_predictions || 0;

    const accuracy = stats.total_predictions > 0
        ? ((stats.correct_predictions / stats.total_predictions) * 100).toFixed(1)
        : 0;
    document.getElementById('accuracyValue').textContent = `${accuracy}%`;

    const profitLoss = stats.total_profit_loss !== null
        ? (stats.total_profit_loss >= 0 ? '+' : '') + stats.total_profit_loss.toFixed(2)
        : '-';
    document.getElementById('profitLoss').textContent = profitLoss;
}

function displayPredictionsTable(predictions) {
    /**
     * Display predictions in table format
     */
    const table = document.getElementById('predictionsTable');
    table.innerHTML = '';

    if (!predictions || predictions.length === 0) {
        table.innerHTML = '<tr><td colspan="5" class="py-4 text-center text-gray-500">No predictions yet</td></tr>';
        return;
    }

    predictions.forEach(prediction => {
        const date = new Date(prediction.created_at).toLocaleDateString();
        const outcome = prediction.predicted_outcome.replace(/_/g, ' ').toUpperCase();
        const confidence = (prediction.confidence * 100).toFixed(1);

        const result = prediction.result ? prediction.result.actual_outcome.replace(/_/g, ' ').toUpperCase() : 'Pending';
        const status = prediction.result
            ? (prediction.result.is_correct ? '✓ Correct' : '✗ Incorrect')
            : 'Pending';
        const statusClass = prediction.result
            ? (prediction.result.is_correct ? 'text-green-600' : 'text-red-600')
            : 'text-gray-600';

        const row = document.createElement('tr');
        row.className = 'border-b border-gray-200';
        row.innerHTML = `
            <td class="py-3 px-4 text-gray-700">${prediction.match.home_team.name} vs ${prediction.match.away_team.name}</td>
            <td class="py-3 px-4 text-gray-700">${outcome}</td>
            <td class="py-3 px-4 text-gray-700">${result}</td>
            <td class="py-3 px-4 ${statusClass} font-semibold">${status}</td>
            <td class="py-3 px-4 text-gray-700">${confidence}%</td>
        `;
        table.appendChild(row);
    });
}

// ===== Event Listeners =====

document.addEventListener('DOMContentLoaded', function() {
    // Navigation
    document.getElementById('navHome').addEventListener('click', () => showView('home'));
    document.getElementById('navHistory').addEventListener('click', () => showView('history'));
    document.getElementById('navAbout').addEventListener('click', () => showView('about'));

    // Match selection
    document.getElementById('loadMatchesBtn').addEventListener('click', loadMatches);

    // Match details modal
    document.getElementById('closeMatchModal').addEventListener('click', closeMatchModal);
    document.getElementById('matchModal').addEventListener('click', (e) => {
        if (e.target === document.getElementById('matchModal')) {
            closeMatchModal();
        }
    });

    // Match details actions
    document.getElementById('getOddsBtn').addEventListener('click', getMatchOdds);
    document.getElementById('fetchLiveOddsBtn').addEventListener('click', fetchLiveOdds);
    document.getElementById('getBestOddsBtn').addEventListener('click', getBestOdds);
    document.getElementById('generatePredictionBtn').addEventListener('click', generatePrediction);
    document.getElementById('savePredictionBtn').addEventListener('click', savePrediction);

    // Initialize
    loadLeagues();
    showView('home');
});
