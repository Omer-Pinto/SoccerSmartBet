/**
 * SoccerSmartBet Tool Tester - Frontend JavaScript
 * Handles API calls and renders football-themed infographic data
 */

// DOM Elements
const homeTeamInput = document.getElementById('home-team');
const awayTeamInput = document.getElementById('away-team');
const fetchBtn = document.getElementById('fetch-btn');
const resultsSection = document.getElementById('results');
const errorMessage = document.getElementById('error-message');

// Event Listeners
fetchBtn.addEventListener('click', fetchMatchData);
homeTeamInput.addEventListener('keypress', (e) => e.key === 'Enter' && awayTeamInput.focus());
awayTeamInput.addEventListener('keypress', (e) => e.key === 'Enter' && fetchMatchData());

/**
 * Fetch match data from the API
 */
async function fetchMatchData() {
    const homeTeam = homeTeamInput.value.trim();
    const awayTeam = awayTeamInput.value.trim();

    if (!homeTeam || !awayTeam) {
        showError('Please enter both home and away team names');
        return;
    }

    setLoading(true);
    hideError();
    hideResults();

    try {
        const response = await fetch('/api/fetch-match-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                home_team: homeTeam,
                away_team: awayTeam
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to fetch match data');
        }

        const data = await response.json();
        renderMatchData(data);
        showResults();
    } catch (error) {
        showError(error.message);
    } finally {
        setLoading(false);
    }
}

/**
 * Render all match data
 */
function renderMatchData(data) {
    // Match Header
    document.getElementById('header-home-team').textContent = data.home_team;
    document.getElementById('header-away-team').textContent = data.away_team;
    document.getElementById('col-home-team').textContent = data.home_team;
    document.getElementById('col-away-team').textContent = data.away_team;
    document.getElementById('home-crest').textContent = data.home_team.charAt(0);
    document.getElementById('away-crest').textContent = data.away_team.charAt(0);

    // Match Date
    const matchDate = data.match_date || 'TBD';
    document.getElementById('match-date').textContent = formatDate(matchDate);

    // Render game tools
    renderOdds(findTool(data.game_tools, 'fetch_odds'));
    renderVenue(findTool(data.game_tools, 'fetch_venue'));
    renderWeather(findTool(data.game_tools, 'fetch_weather'));
    renderH2H(findTool(data.game_tools, 'fetch_h2h'));

    // Render home team tools
    renderForm('home', findTool(data.home_team_tools, 'fetch_form'));
    renderLeaguePosition('home', findTool(data.home_team_tools, 'fetch_league_position'));
    renderInjuries('home', findTool(data.home_team_tools, 'fetch_injuries'));
    renderRecovery('home', findTool(data.home_team_tools, 'calculate_recovery_time'));

    // Render away team tools
    renderForm('away', findTool(data.away_team_tools, 'fetch_form'));
    renderLeaguePosition('away', findTool(data.away_team_tools, 'fetch_league_position'));
    renderInjuries('away', findTool(data.away_team_tools, 'fetch_injuries'));
    renderRecovery('away', findTool(data.away_team_tools, 'calculate_recovery_time'));

    // Extract league name from league position
    const homeLeague = findTool(data.home_team_tools, 'fetch_league_position');
    if (homeLeague?.data?.league_name) {
        document.getElementById('league-name').textContent = homeLeague.data.league_name;
    }

    // Performance stats
    renderPerformance(data);
}

/**
 * Find a tool result by name
 */
function findTool(tools, name) {
    return tools.find(t => t.tool_name === name);
}

/**
 * Render betting odds
 */
function renderOdds(tool) {
    const homeOdds = document.getElementById('odds-home');
    const drawOdds = document.getElementById('odds-draw');
    const awayOdds = document.getElementById('odds-away');
    const bookmaker = document.getElementById('odds-bookmaker');

    if (!tool?.success || !tool.data) {
        homeOdds.textContent = '-';
        drawOdds.textContent = '-';
        awayOdds.textContent = '-';
        bookmaker.textContent = tool?.error || 'No odds data available';
        return;
    }

    const { odds_home, odds_draw, odds_away, bookmaker: bm } = tool.data;
    homeOdds.textContent = odds_home?.toFixed(2) || '-';
    drawOdds.textContent = odds_draw?.toFixed(2) || '-';
    awayOdds.textContent = odds_away?.toFixed(2) || '-';
    bookmaker.textContent = bm ? `Source: ${bm}` : '';
}

/**
 * Render venue information
 */
function renderVenue(tool) {
    const venueName = document.getElementById('venue-name');
    const venueCity = document.getElementById('venue-city');
    const venueCapacity = document.getElementById('venue-capacity');

    if (!tool?.success || !tool.data) {
        venueName.textContent = 'Unknown Venue';
        venueCity.textContent = tool?.error || 'No venue data';
        venueCapacity.textContent = '';
        return;
    }

    const { venue_name, venue_city, venue_capacity } = tool.data;
    venueName.textContent = venue_name || 'Unknown Venue';
    venueCity.textContent = venue_city || '';
    venueCapacity.textContent = venue_capacity ? `Capacity: ${venue_capacity.toLocaleString()}` : '';
}

/**
 * Render weather information
 */
function renderWeather(tool) {
    const weatherIcon = document.getElementById('weather-icon');
    const weatherTemp = document.getElementById('weather-temp');
    const weatherConditions = document.getElementById('weather-conditions');
    const weatherWind = document.getElementById('weather-wind');
    const weatherRain = document.getElementById('weather-rain');

    if (!tool?.success || !tool.data) {
        weatherIcon.textContent = '?';
        weatherTemp.textContent = '-';
        weatherConditions.textContent = tool?.error || 'No weather data';
        weatherWind.textContent = '';
        weatherRain.textContent = '';
        return;
    }

    const { temperature_celsius, conditions, wind_speed_kmh, precipitation_probability, precipitation_mm } = tool.data;

    // Weather icon based on conditions
    const icons = {
        'Clear': '\u2600\uFE0F',      // sunny
        'Partly Cloudy': '\u26C5',    // partly cloudy
        'Cloudy': '\u2601\uFE0F',     // cloudy
        'Rain': '\u{1F327}\uFE0F',    // rain
        'Heavy Rain': '\u26C8\uFE0F', // thunderstorm
        'Snow': '\u2744\uFE0F',       // snow
        'Fog': '\u{1F32B}\uFE0F'      // fog
    };
    weatherIcon.textContent = icons[conditions] || '\u{1F324}\uFE0F';

    weatherTemp.textContent = temperature_celsius !== null ? `${Math.round(temperature_celsius)}°C` : '-';
    weatherConditions.textContent = conditions || '';
    weatherWind.textContent = wind_speed_kmh !== null ? `Wind: ${Math.round(wind_speed_kmh)} km/h` : '';
    weatherRain.textContent = precipitation_probability !== null ? `Rain: ${precipitation_probability}%` : '';
}

/**
 * Render head-to-head data
 */
function renderH2H(tool) {
    const h2hSummary = document.getElementById('h2h-summary');
    const h2hMatches = document.getElementById('h2h-matches');

    if (!tool?.success || !tool.data) {
        h2hSummary.textContent = tool?.error || 'No H2H data available';
        h2hMatches.innerHTML = '';
        return;
    }

    const { h2h_matches, home_team, away_team, total_h2h } = tool.data;

    // Calculate summary
    let homeWins = 0, draws = 0, awayWins = 0;
    (h2h_matches || []).forEach(m => {
        if (m.winner === 'HOME_TEAM') homeWins++;
        else if (m.winner === 'AWAY_TEAM') awayWins++;
        else draws++;
    });

    h2hSummary.innerHTML = `
        <span style="color: var(--win-green)">${homeWins}W</span> -
        <span style="color: var(--draw-gray)">${draws}D</span> -
        <span style="color: var(--loss-red)">${awayWins}W</span>
        <br><small style="color: var(--text-muted)">Last ${h2h_matches?.length || 0} meetings</small>
    `;

    // Render match list
    h2hMatches.innerHTML = (h2h_matches || []).slice(0, 5).map(match => {
        const score = match.score_home !== null ? `${match.score_home} - ${match.score_away}` : 'N/A';
        const winnerColor = match.winner === 'HOME_TEAM' ? 'var(--win-green)' :
            match.winner === 'AWAY_TEAM' ? 'var(--loss-red)' : 'var(--draw-gray)';

        return `
            <div class="h2h-match">
                <span class="h2h-date">${formatDate(match.date)}</span>
                <span class="h2h-teams">${match.home_team} vs ${match.away_team}</span>
                <span class="h2h-score">${score}</span>
                <span class="h2h-winner" style="background: ${winnerColor}"></span>
            </div>
        `;
    }).join('');
}

/**
 * Render team form (W/D/L circles)
 */
function renderForm(side, tool) {
    const formCircles = document.getElementById(`${side}-form-circles`);
    const formRecord = document.getElementById(`${side}-form-record`);

    if (!tool?.success || !tool.data) {
        formCircles.innerHTML = '<span style="color: var(--text-muted)">No form data</span>';
        formRecord.textContent = tool?.error || '';
        return;
    }

    const { matches, record } = tool.data;

    // Render form circles
    formCircles.innerHTML = (matches || []).slice(0, 5).map(match => {
        const resultClass = match.result === 'W' ? 'win' : match.result === 'D' ? 'draw' : 'loss';
        const score = match.goals_for !== null ? `${match.goals_for}-${match.goals_against}` : match.result;
        return `<div class="form-circle ${resultClass}" title="${match.opponent} (${match.home_away}) ${score}">${match.result}</div>`;
    }).join('');

    // Render record
    if (record) {
        formRecord.textContent = `${record.wins}W - ${record.draws}D - ${record.losses}L`;
    }
}

/**
 * Render league position
 */
function renderLeaguePosition(side, tool) {
    const positionNum = document.getElementById(`${side}-position`);
    const positionStats = document.getElementById(`${side}-position-stats`);
    const leagueForm = document.getElementById(`${side}-league-form`);

    if (!tool?.success || !tool.data) {
        positionNum.textContent = '-';
        positionStats.textContent = tool?.error || 'No position data';
        leagueForm.innerHTML = '';
        return;
    }

    const { position, played, won, draw, lost, points, form } = tool.data;

    positionNum.textContent = position || '-';
    positionStats.textContent = `${points || 0} pts | ${played || 0}P ${won || 0}W ${draw || 0}D ${lost || 0}L`;

    // Render mini form circles from league data
    if (form) {
        leagueForm.innerHTML = form.split('').map(r => {
            const cls = r === 'W' ? 'win' : r === 'D' ? 'draw' : 'loss';
            const bg = r === 'W' ? 'var(--win-green)' : r === 'D' ? 'var(--draw-gray)' : 'var(--loss-red)';
            return `<div class="mini-circle" style="background: ${bg}">${r}</div>`;
        }).join('');
    }
}

/**
 * Render injuries list
 */
function renderInjuries(side, tool) {
    const injuriesList = document.getElementById(`${side}-injuries`);

    if (!tool?.success || !tool.data) {
        injuriesList.innerHTML = `<span style="color: var(--text-muted)">${tool?.error || 'No injury data'}</span>`;
        return;
    }

    const { injuries, total_injuries } = tool.data;

    if (!injuries || injuries.length === 0) {
        injuriesList.innerHTML = '<div class="no-injuries">\u2714 No injuries reported</div>';
        return;
    }

    injuriesList.innerHTML = injuries.slice(0, 5).map(injury => `
        <div class="injury-item">
            <span class="injury-player">${injury.player_name}</span>
            <span class="injury-type">${injury.injury_type || 'Unknown'}</span>
        </div>
    `).join('');

    if (total_injuries > 5) {
        injuriesList.innerHTML += `<div style="text-align: center; color: var(--text-muted); font-size: 0.8rem;">+${total_injuries - 5} more</div>`;
    }
}

/**
 * Render recovery time
 */
function renderRecovery(side, tool) {
    const recoveryDays = document.getElementById(`${side}-recovery-days`);
    const recoveryStatus = document.getElementById(`${side}-recovery-status`);

    if (!tool?.success || !tool.data) {
        recoveryDays.textContent = '-';
        recoveryStatus.textContent = tool?.error || 'No recovery data';
        recoveryStatus.className = 'recovery-status';
        return;
    }

    const { recovery_days, recovery_status } = tool.data;

    recoveryDays.textContent = recovery_days !== null ? recovery_days : '-';

    const statusClass = recovery_status?.toLowerCase() || '';
    recoveryStatus.textContent = recovery_status || 'Unknown';
    recoveryStatus.className = `recovery-status ${statusClass}`;

    // Color the days based on status
    if (recovery_status === 'Short') {
        recoveryDays.style.color = 'var(--loss-red)';
    } else if (recovery_status === 'Extended') {
        recoveryDays.style.color = 'var(--win-green)';
    } else {
        recoveryDays.style.color = 'var(--accent-gold)';
    }
}

/**
 * Render performance/debug stats
 */
function renderPerformance(data) {
    const allTools = [...data.game_tools, ...data.home_team_tools, ...data.away_team_tools];
    const successCount = allTools.filter(t => t.success).length;
    const failedCount = allTools.filter(t => !t.success).length;

    document.getElementById('total-time').textContent = `${Math.round(data.total_time_ms)}ms`;
    document.getElementById('tools-success').textContent = `${successCount}/12`;
    document.getElementById('tools-failed').textContent = failedCount;

    // Tool breakdown
    const breakdown = document.getElementById('tool-breakdown');
    breakdown.innerHTML = allTools.map(tool => {
        const statusClass = tool.success ? 'success' : 'error';
        const icon = tool.success ? '\u2714' : '\u2718';
        return `
            <div class="tool-badge ${statusClass}" title="${tool.error || 'OK'}">
                <span>${icon}</span>
                <span>${tool.tool_name}</span>
                <span class="time">${Math.round(tool.execution_time_ms)}ms</span>
            </div>
        `;
    }).join('');
}

/**
 * Format date string
 */
function formatDate(dateStr) {
    if (!dateStr || dateStr === 'TBD') return 'TBD';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-GB', {
            weekday: 'short',
            day: 'numeric',
            month: 'short',
            year: 'numeric'
        });
    } catch {
        return dateStr;
    }
}

/**
 * UI Helpers
 */
function setLoading(loading) {
    fetchBtn.classList.toggle('loading', loading);
    fetchBtn.disabled = loading;
}

function showError(message) {
    errorMessage.querySelector('.error-text').textContent = message;
    errorMessage.classList.remove('hidden');
}

function hideError() {
    errorMessage.classList.add('hidden');
}

function showResults() {
    resultsSection.classList.remove('hidden');
}

function hideResults() {
    resultsSection.classList.add('hidden');
}
