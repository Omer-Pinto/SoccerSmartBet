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

/**
 * Create an element with safe text content (XSS-safe)
 */
function createElement(tag, className, textContent, styles = {}) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (textContent !== undefined && textContent !== null) el.textContent = textContent;
    Object.assign(el.style, styles);
    return el;
}

// Event Listeners
fetchBtn.addEventListener('click', fetchMatchData);
homeTeamInput.addEventListener('keypress', (e) => e.key === 'Enter' && awayTeamInput.focus());
awayTeamInput.addEventListener('keypress', (e) => e.key === 'Enter' && fetchMatchData());

/**
 * Reset all result sections to loading/placeholder state
 */
function resetResults() {
    // Match header
    document.getElementById('header-home-team').textContent = homeTeamInput.value.trim();
    document.getElementById('header-away-team').textContent = awayTeamInput.value.trim();
    document.getElementById('col-home-team').textContent = homeTeamInput.value.trim();
    document.getElementById('col-away-team').textContent = awayTeamInput.value.trim();
    document.getElementById('home-crest').textContent = homeTeamInput.value.trim().charAt(0);
    document.getElementById('away-crest').textContent = awayTeamInput.value.trim().charAt(0);
    document.getElementById('match-date').textContent = '...';
    document.getElementById('league-name').textContent = '-';

    // Odds
    document.getElementById('odds-home').textContent = '...';
    document.getElementById('odds-draw').textContent = '...';
    document.getElementById('odds-away').textContent = '...';
    document.getElementById('odds-bookmaker').textContent = 'Loading...';
    document.getElementById('winner-odds-home').textContent = '...';
    document.getElementById('winner-odds-draw').textContent = '...';
    document.getElementById('winner-odds-away').textContent = '...';
    document.getElementById('winner-league').textContent = '';
    document.getElementById('winner-odds-meta').textContent = 'Loading...';

    // Game tools
    document.getElementById('h2h-summary').textContent = 'Loading...';
    document.getElementById('h2h-matches').textContent = '';
    document.getElementById('venue-name').textContent = 'Loading...';
    document.getElementById('venue-city').textContent = '';
    document.getElementById('venue-capacity').textContent = '';
    document.getElementById('weather-icon').textContent = '...';
    document.getElementById('weather-temp').textContent = '...';
    document.getElementById('weather-conditions').textContent = 'Loading...';
    document.getElementById('weather-wind').textContent = '';
    document.getElementById('weather-rain').textContent = '';

    // Team tools
    for (const side of ['home', 'away']) {
        document.getElementById(`${side}-form-circles`).textContent = '';
        document.getElementById(`${side}-form-record`).textContent = 'Loading...';
        document.getElementById(`${side}-position`).textContent = '...';
        document.getElementById(`${side}-position-stats`).textContent = 'Loading...';
        document.getElementById(`${side}-league-form`).textContent = '';
        document.getElementById(`${side}-injuries`).textContent = 'Loading...';
        document.getElementById(`${side}-news`).textContent = 'Loading...';
        document.getElementById(`${side}-recovery-days`).textContent = '...';
        document.getElementById(`${side}-recovery-status`).textContent = 'Loading...';
    }

    // Performance
    document.getElementById('total-time').textContent = '...';
    document.getElementById('tools-success').textContent = '0/15';
    document.getElementById('tools-failed').textContent = '0';
    document.getElementById('tool-breakdown').textContent = '';
}

// Track completed tools for performance section
let _toolResults = [];

/**
 * Render a single tool result as it arrives via SSE
 */
function renderToolResult(category, result) {
    _toolResults.push(result);

    switch (result.tool_name) {
        case 'fetch_odds':      renderOdds(result); break;
        case 'fetch_winner_odds': renderWinnerOdds(result); break;
        case 'fetch_venue':     renderVenue(result); break;
        case 'fetch_weather':   renderWeather(result); break;
        case 'fetch_h2h':
            renderH2H(result);
            // Update match date when H2H arrives
            if (result.success && result.data && result.data.upcoming_match_date) {
                document.getElementById('match-date').textContent = formatDate(result.data.upcoming_match_date);
            }
            break;
        case 'fetch_form':
            renderForm(category, result);
            break;
        case 'fetch_league_position':
            renderLeaguePosition(category, result);
            if (category === 'home' && result.success && result.data && result.data.league_name) {
                document.getElementById('league-name').textContent = result.data.league_name;
            }
            break;
        case 'fetch_injuries':
            renderInjuries(category, result);
            break;
        case 'fetch_team_news':
            renderTeamNews(category, result);
            break;
        case 'calculate_recovery_time':
            renderRecovery(category, result);
            break;
    }

    // Update live performance counter
    const success = _toolResults.filter(t => t.success).length;
    const failed = _toolResults.filter(t => !t.success).length;
    document.getElementById('tools-success').textContent = `${success}/${_toolResults.length}`;
    document.getElementById('tools-failed').textContent = failed;
    updateToolBreakdown();
}

/**
 * Update the tool breakdown badges
 */
function updateToolBreakdown() {
    const breakdown = document.getElementById('tool-breakdown');
    breakdown.textContent = '';
    _toolResults.forEach(tool => {
        const statusClass = tool.success ? 'success' : 'error';
        const icon = tool.success ? '\u2714' : '\u2718';
        const badge = createElement('div', `tool-badge ${statusClass}`);
        badge.title = tool.error || 'OK';
        badge.appendChild(createElement('span', null, icon));
        badge.appendChild(createElement('span', null, tool.tool_name));
        badge.appendChild(createElement('span', 'time', `${Math.round(tool.execution_time_ms)}ms`));
        breakdown.appendChild(badge);
    });
}

/**
 * Fetch match data from the API using SSE streaming
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
    _toolResults = [];
    resetResults();
    showResults();

    const startTime = Date.now();

    try {
        const response = await fetch('/api/stream-match-data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ home_team: homeTeam, away_team: awayTeam })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to fetch match data');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop(); // keep any incomplete trailing chunk

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                let data;
                try {
                    data = JSON.parse(line.slice(6));
                } catch {
                    continue;
                }
                if (data.done) {
                    const elapsed = Date.now() - startTime;
                    document.getElementById('total-time').textContent = `${elapsed}ms`;
                    setLoading(false);
                    return;
                }
                renderToolResult(data.category, data.result);
            }
        }
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
    renderWinnerOdds(findTool(data.game_tools, 'fetch_winner_odds'));
    renderVenue(findTool(data.game_tools, 'fetch_venue'));
    renderWeather(findTool(data.game_tools, 'fetch_weather'));
    renderH2H(findTool(data.game_tools, 'fetch_h2h'));

    // Render home team tools
    renderForm('home', findTool(data.home_team_tools, 'fetch_form'));
    renderLeaguePosition('home', findTool(data.home_team_tools, 'fetch_league_position'));
    renderInjuries('home', findTool(data.home_team_tools, 'fetch_injuries'));
    renderTeamNews('home', findTool(data.home_team_tools, 'fetch_team_news'));
    renderRecovery('home', findTool(data.home_team_tools, 'calculate_recovery_time'));

    // Render away team tools
    renderForm('away', findTool(data.away_team_tools, 'fetch_form'));
    renderLeaguePosition('away', findTool(data.away_team_tools, 'fetch_league_position'));
    renderInjuries('away', findTool(data.away_team_tools, 'fetch_injuries'));
    renderTeamNews('away', findTool(data.away_team_tools, 'fetch_team_news'));
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
        h2hMatches.textContent = '';
        return;
    }

    const { h2h_matches, home_team, away_team, total_h2h } = tool.data;

    // Calculate summary — winner is now the user's input team name (or "DRAW")
    let homeWins = 0, draws = 0, awayWins = 0;
    (h2h_matches || []).forEach(m => {
        if (m.winner === home_team) homeWins++;
        else if (m.winner === away_team) awayWins++;
        else draws++;
    });

    // Build summary using DOM (XSS-safe)
    h2hSummary.textContent = '';
    h2hSummary.appendChild(createElement('span', null, `${homeWins}W`, { color: 'var(--win-green)' }));
    h2hSummary.appendChild(document.createTextNode(' - '));
    h2hSummary.appendChild(createElement('span', null, `${draws}D`, { color: 'var(--draw-gray)' }));
    h2hSummary.appendChild(document.createTextNode(' - '));
    h2hSummary.appendChild(createElement('span', null, `${awayWins}W`, { color: 'var(--loss-red)' }));
    h2hSummary.appendChild(document.createElement('br'));
    h2hSummary.appendChild(createElement('small', null, `Last ${h2h_matches?.length || 0} meetings`, { color: 'var(--text-muted)' }));

    // Render match list using DOM (XSS-safe)
    h2hMatches.textContent = '';
    (h2h_matches || []).slice(0, 5).forEach(match => {
        const score = match.score_home !== null ? `${match.score_home} - ${match.score_away}` : 'N/A';
        const winnerColor = match.winner === home_team ? 'var(--win-green)' :
            match.winner === away_team ? 'var(--loss-red)' : 'var(--draw-gray)';

        const matchDiv = createElement('div', 'h2h-match');
        matchDiv.appendChild(createElement('span', 'h2h-date', formatDate(match.date)));
        matchDiv.appendChild(createElement('span', 'h2h-teams', `${match.home_team} vs ${match.away_team}`));
        matchDiv.appendChild(createElement('span', 'h2h-score', score));
        matchDiv.appendChild(createElement('span', 'h2h-winner', null, { background: winnerColor }));
        h2hMatches.appendChild(matchDiv);
    });
}

/**
 * Render team form (W/D/L circles)
 */
function renderForm(side, tool) {
    const formCircles = document.getElementById(`${side}-form-circles`);
    const formRecord = document.getElementById(`${side}-form-record`);

    if (!tool?.success || !tool.data) {
        formCircles.textContent = '';
        formCircles.appendChild(createElement('span', null, 'No form data', { color: 'var(--text-muted)' }));
        formRecord.textContent = tool?.error || '';
        return;
    }

    const { matches, record } = tool.data;

    // Render form circles using DOM (XSS-safe)
    formCircles.textContent = '';
    (matches || []).slice(0, 5).forEach(match => {
        const resultClass = match.result === 'W' ? 'win' : match.result === 'D' ? 'draw' : 'loss';
        const score = match.goals_for !== null ? `${match.goals_for}-${match.goals_against}` : match.result;
        const circle = createElement('div', `form-circle ${resultClass}`, match.result);
        circle.title = `${match.opponent} (${match.home_away}) ${score}`;
        formCircles.appendChild(circle);
    });

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
        leagueForm.textContent = '';
        return;
    }

    const { position, played, won, draw, lost, points, form } = tool.data;

    positionNum.textContent = position || '-';
    positionStats.textContent = `${points || 0} pts | ${played || 0}P ${won || 0}W ${draw || 0}D ${lost || 0}L`;

    // Render mini form circles from league data using DOM (XSS-safe)
    leagueForm.textContent = '';
    if (form) {
        form.split('').forEach(r => {
            const bg = r === 'W' ? 'var(--win-green)' : r === 'D' ? 'var(--draw-gray)' : 'var(--loss-red)';
            leagueForm.appendChild(createElement('div', 'mini-circle', r, { background: bg }));
        });
    }
}

/**
 * Render injuries list
 */
function renderInjuries(side, tool) {
    const injuriesList = document.getElementById(`${side}-injuries`);

    if (!tool?.success || !tool.data) {
        injuriesList.textContent = '';
        injuriesList.appendChild(createElement('span', null, tool?.error || 'No injury data', { color: 'var(--text-muted)' }));
        return;
    }

    const { injuries, total_injuries } = tool.data;

    if (!injuries || injuries.length === 0) {
        injuriesList.textContent = '';
        injuriesList.appendChild(createElement('div', 'no-injuries', '\u2714 No injuries reported'));
        return;
    }

    // Render injuries using DOM (XSS-safe)
    injuriesList.textContent = '';
    injuries.slice(0, 5).forEach(injury => {
        const item = createElement('div', 'injury-item');
        item.appendChild(createElement('span', 'injury-player', injury.player_name));
        item.appendChild(createElement('span', 'injury-type', injury.injury_type || 'Unknown'));
        injuriesList.appendChild(item);
    });

    if (total_injuries > 5) {
        injuriesList.appendChild(createElement('div', null, `+${total_injuries - 5} more`, {
            textAlign: 'center',
            color: 'var(--text-muted)',
            fontSize: '0.8rem'
        }));
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
 * Render winner.co.il Israeli Toto odds
 */
function renderWinnerOdds(tool) {
    const homeOdds = document.getElementById('winner-odds-home');
    const drawOdds = document.getElementById('winner-odds-draw');
    const awayOdds = document.getElementById('winner-odds-away');
    const leagueEl = document.getElementById('winner-league');
    const metaEl = document.getElementById('winner-odds-meta');

    if (!tool?.success || !tool.data) {
        homeOdds.textContent = '-';
        drawOdds.textContent = '-';
        awayOdds.textContent = '-';
        leagueEl.textContent = '';
        metaEl.textContent = tool?.error || 'No winner.co.il data';
        return;
    }

    const { odds_home, odds_draw, odds_away, league, home_name_he, away_name_he } = tool.data;
    homeOdds.textContent = odds_home?.toFixed(2) || '-';
    drawOdds.textContent = odds_draw?.toFixed(2) || '-';
    awayOdds.textContent = odds_away?.toFixed(2) || '-';
    leagueEl.textContent = league || '';

    if (home_name_he && away_name_he) {
        metaEl.textContent = `${home_name_he} vs ${away_name_he}`;
    } else if (tool.error) {
        metaEl.textContent = tool.error;
    } else {
        metaEl.textContent = '';
    }
}

/**
 * Render team news articles
 */
function renderTeamNews(side, tool) {
    const newsList = document.getElementById(`${side}-news`);

    if (!tool?.success || !tool.data) {
        newsList.textContent = '';
        newsList.appendChild(createElement('span', null, tool?.error || 'No news data', { color: 'var(--text-muted)' }));
        return;
    }

    const { articles, total_available } = tool.data;

    if (!articles || articles.length === 0) {
        newsList.textContent = '';
        newsList.appendChild(createElement('div', 'no-news', 'No recent news'));
        return;
    }

    newsList.textContent = '';
    articles.slice(0, 5).forEach(article => {
        const item = createElement('div', 'news-item');
        const title = createElement('div', 'news-title', article.title);
        const meta = createElement('div', 'news-meta');
        if (article.source) {
            meta.appendChild(createElement('span', 'news-source', article.source));
        }
        if (article.published) {
            const pubDate = formatDate(article.published);
            meta.appendChild(createElement('span', 'news-date', pubDate));
        }
        item.appendChild(title);
        item.appendChild(meta);
        newsList.appendChild(item);
    });

    if (total_available > 5) {
        newsList.appendChild(createElement('div', null, `+${total_available - 5} more articles`, {
            textAlign: 'center',
            color: 'var(--text-muted)',
            fontSize: '0.8rem',
            marginTop: '4px'
        }));
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
    document.getElementById('tools-success').textContent = `${successCount}/${allTools.length}`;
    document.getElementById('tools-failed').textContent = failedCount;

    // Tool breakdown using DOM (XSS-safe)
    const breakdown = document.getElementById('tool-breakdown');
    breakdown.textContent = '';
    allTools.forEach(tool => {
        const statusClass = tool.success ? 'success' : 'error';
        const icon = tool.success ? '\u2714' : '\u2718';

        const badge = createElement('div', `tool-badge ${statusClass}`);
        badge.title = tool.error || 'OK';
        badge.appendChild(createElement('span', null, icon));
        badge.appendChild(createElement('span', null, tool.tool_name));
        badge.appendChild(createElement('span', 'time', `${Math.round(tool.execution_time_ms)}ms`));
        breakdown.appendChild(badge);
    });
}

/**
 * Format date string
 */
function formatDate(dateStr) {
    if (!dateStr || dateStr === 'TBD') return 'TBD';
    try {
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return dateStr;
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
