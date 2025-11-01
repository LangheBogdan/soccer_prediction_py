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
     * Fetch and display betting odds
     */
    if (!state.currentMatch) {
        showError('No match selected');
        return;
    }

    try {
        const odds = await apiCall(`/odds/matches/${state.currentMatch.id}`);
        displayOdds(odds);
        document.getElementById('oddsDisplay').classList.remove('hidden');
    } catch (error) {
        showError('Failed to load odds');
    }
}

function displayOdds(odds) {
    /**
     * Display odds in the UI
     */
    const oddsList = document.getElementById('oddsList');
    oddsList.innerHTML = '';

    if (!odds || odds.length === 0) {
        oddsList.innerHTML = '<p class="text-gray-500">No odds available</p>';
        return;
    }

    odds.forEach(odd => {
        const oddElement = document.createElement('div');
        oddElement.className = 'border border-gray-200 rounded-lg p-3 flex justify-between';
        oddElement.innerHTML = `
            <span class="font-semibold text-gray-800">${odd.bookmaker}</span>
            <div class="space-x-4">
                <span class="text-sm">Home: <span class="font-semibold">${parseFloat(odd.home_win_odds).toFixed(2)}</span></span>
                <span class="text-sm">Draw: <span class="font-semibold">${parseFloat(odd.draw_odds).toFixed(2)}</span></span>
                <span class="text-sm">Away: <span class="font-semibold">${parseFloat(odd.away_win_odds).toFixed(2)}</span></span>
            </div>
        `;
        oddsList.appendChild(oddElement);
    });
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
    document.getElementById('generatePredictionBtn').addEventListener('click', generatePrediction);
    document.getElementById('savePredictionBtn').addEventListener('click', savePrediction);

    // Initialize
    loadLeagues();
    showView('home');
});
