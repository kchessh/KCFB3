// static/js/draft.js
const socket = io();
const rowsPerPage = 10;
let countdownInterval = null;
let currentNominationId = CURRENT_NOMINATION;
let currentPage = 1;
let filteredRows = [];

// ─── Connection ───────────────────────────────────────────────
socket.on('connect', () => {
    socket.emit('join_draft', { league_id: ROOM_ID });
    console.log('Connected to draft room:', ROOM_ID);
});

// ─── Incoming Events ──────────────────────────────────────────
socket.on('nomination_started', (data) => {
    currentNominationId = data.nomination_id;
    document.getElementById('current-team').textContent = data.team_name;
    document.getElementById('current-bid').textContent = `Current Bid: $${data.current_bid}`;
    document.getElementById('current-winner').textContent = `Leader: ${data.current_winner_name}`;
    setBidControlsEnabled(true);

    addLogEntry(`🏷️ ${data.team_name} nominated! Starting at $${data.current_bid}`);
    startBiddingCountdown(data.seconds_remaining);
});

socket.on('bid_placed', (data) => {
    document.getElementById('current-bid').textContent = `Current Bid: $${data.amount}`;
    document.getElementById('current-winner').textContent = `Leader: ${data.username}`;
    addLogEntry(`💰 ${data.username} bid $${data.amount}`);
});

socket.on('timer_update', (data) => {
    if (data.nomination_id === currentNominationId) {
        startBiddingCountdown(data.seconds_remaining);
    }
});

socket.on('bidding_ended', (data) => {
    console.log('bidding_ended payload:', data);
    currentNominationId = null;
    clearInterval(countdownInterval);
    document.getElementById('timer-display').textContent = 'SOLD!';
    document.getElementById('timer-display').style.color = 'inherit'; //reset color on sold
    setBidControlsEnabled(false);

    const msg = data.winner_id
        ? `✅ ${data.team_name} sold to ${data.winner_name} for $${data.final_price}!`
        : `❌ No bids — nomination cancelled.`;

    document.getElementById('current-team').textContent = msg;
    document.getElementById('current-bid').textContent = `Previous winner: ${data.winner_name}`;
    document.getElementById('current-winner').textContent = `Previous team: ${data.team_name}`;
    addLogEntry(msg);

    updateBudgetDisplay(data.winner_id, data.final_price);
    updateAvailableTeams(data.team_id);

    if (data.winner_id && data.team_slot) {
        const slotEl = document.getElementById(`user-${data.winner_id}-team-${data.team_slot}`);
        console.log('looking for:', `user-${data.winner_id}-team-${data.team_slot}`, '-> found:', slotEl);
        if (slotEl) {
            slotEl.textContent = `Team ${data.team_slot}: ${data.team_name}`;
        }
    }
});

socket.on('nomination_started', (data) => {
    console.log('nomination_started payload:', data);
    currentNominationId = data.nomination_id;
    document.getElementById('timer-display').style.color = 'inherit';
    document.getElementById('current-team').textContent = data.team_name;
    document.getElementById('current-bid').textContent = `Current Bid: $${data.current_bid}`;
    document.getElementById('current-winner').textContent = `Leader: ${data.current_winner_name}`;
    addLogEntry(`📢 ${data.team_name} nominated by ${data.nominated_by_name}`);
    setBidControlsEnabled(true);
    document.getElementById('bid-input').value = '';
    clearInterval(countdownInterval);
    if (data.seconds_remaining !== undefined) {
        startBiddingCountdown(data.seconds_remaining);
    }
});

socket.on('nomination_window_started', (data) => {
    console.log('nomination_window_started payload:', data);
    document.getElementById('current-team').textContent = 'Waiting for nomination...';
    setBidControlsEnabled(false);
    highlightCurrentNominator(data.current_nominator_id);
    updateNominateButton(data.current_nominator_id);
    if (data.seconds_remaining !== undefined) {
        startNominationCountdown(data.seconds_remaining);
    }
});

socket.on('user_joined', (data) => {
    const el = document.getElementById(`user-${data.user_id}`);
    if (el) el.classList.add('connected');
});

socket.on('user_left', (data) => {
    const el = document.getElementById(`user-${data.user_id}`);
    if (el) el.classList.remove('connected');
});

socket.on('error', (data) => {
    alert(`⚠️ ${data.message}`);
});

function randomizeOrder() {
    socket.emit('randomize_order', { league_id: ROOM_ID });
}

function rejoinNomination() {
    socket.emit('rejoin_nomination', { league_id: ROOM_ID });
}

function updateNominateButton(currentNominatorId) {
    const btn = document.getElementById('nominate-btn');
    if (!btn) return;
    if (currentNominatorId === USER_ID) {
        btn.disabled = false;
        btn.textContent = 'Nominate';
    } else {
        btn.disabled = true;
        btn.textContent = 'Waiting for your turn...';
    }
}

socket.on('order_randomized', (data) => {
    console.log('order_randomized payload:', data);
    const list = document.getElementById('participants-list');
    data.order.forEach(entry => {
        const card = document.getElementById(`user-${entry.user_id}`);
        if (card) list.appendChild(card);
    });
    highlightCurrentNominator(data.current_nominator_id);
    updateNominateButton(data.current_nominator_id);
});

socket.on('draft_paused', () => {
    console.log('draft_paused');
    clearInterval(countdownInterval);
    document.getElementById('timer-display').textContent = '⏸ Paused';
    document.getElementById('timer-display').style.color = 'inherit';
    setBidControlsEnabled(false);

    const nominateBtn = document.getElementById('nominate-btn');
    if (nominateBtn) {
        nominateBtn.disabled = true;
        nominateBtn.dataset.pausedOverride = 'true'; // remember this was disabled by pause, not by turn order
        nominateBtn.textContent = 'Draft paused';
    }

    const pauseBtn = document.getElementById('pause-draft-btn');
    if (pauseBtn) {
        pauseBtn.textContent = '▶ Resume Draft';
        pauseBtn.classList.add('paused');
    }
});

socket.on('draft_resumed', () => {
    console.log('draft_resumed');
    const pauseBtn = document.getElementById('pause-draft-btn');
    if (pauseBtn) {
        pauseBtn.textContent = '⏸ Pause Draft';
        pauseBtn.classList.remove('paused');
    }

    const nominateBtn = document.getElementById('nominate-btn');
    if (nominateBtn && nominateBtn.dataset.pausedOverride === 'true') {
        delete nominateBtn.dataset.pausedOverride;
        // Restore correct state based on whose turn it actually is,
        // rather than assuming this user can nominate
        updateNominateButton(data.current_nominator_id);
    }

    // The backend will follow this up with a timer_update or nomination_window_started
    // event carrying the correct timer_end, which restarts the visible countdown.
});

socket.on('draft_reset', () => {
    console.log('draft_reset received');
    location.reload();
});

function highlightCurrentNominator(userId) {
    document.querySelectorAll('.participant').forEach(el => el.classList.remove('current-nominator'));
    const activeCard = document.getElementById(`user-${userId}`);
    if (activeCard) activeCard.classList.add('current-nominator');
}

function togglePause() {
    socket.emit('toggle_pause', { league_id: ROOM_ID });
}

socket.on('nominator_skipped', (data) => {
    console.log('nominator_skipped payload:', data);
    addLogEntry(`⏭ ${data.name} was skipped for not nominating in time.`);
    if (data.user_id === USER_ID) {
        document.getElementById('rejoin-nomination-btn').style.display = 'inline-block';
    }
});

socket.on('rejoined_nomination', (data) => {
    if (data.user_id === USER_ID) {
        document.getElementById('rejoin-nomination-btn').style.display = 'none';
    }
});

// ─── User Actions ─────────────────────────────────────────────
function nominateTeam() {
    const teamId = document.getElementById('team-select').value;
    const startingBid = parseInt(document.getElementById('starting-bid').value);
    console.log('Nominating team:', teamId, 'Starting bid:', startingBid);
    socket.emit('nominate_team', {
        league_id: ROOM_ID,
        team_id: teamId,
        starting_bid: startingBid,
        user_id: USER_ID,
    });
}

function placeBid() {
    const amount = parseInt(document.getElementById('bid-input').value);
    if (!currentNominationId) return alert('No active nomination.');
    if (!amount || amount < 1) return alert('Enter a valid bid.');
    socket.emit('place_bid', {
        room_id: ROOM_ID,
        nomination_id: currentNominationId,
        amount: amount
    });
}


function quickBid(increment) {
    const currentBidText = document.getElementById('current-bid').textContent;
    const currentBid = parseInt(currentBidText.replace(/\D/g, '')) || 0;
    document.getElementById('bid-input').value = currentBid + increment;
}

function selectTeam(id, name) {
    // Remove highlight from all rows
    document.querySelectorAll('.team-row').forEach(row => row.classList.remove('selected'));

    // Highlight the clicked row
    const selectedRow = document.querySelector(`.team-row[data-id="${id}"]`);
    if (selectedRow) selectedRow.classList.add('selected');

    const teamSelectEl = document.getElementById('team-select');
    if (teamSelectEl) teamSelectEl.value = id;

    const nameDisplayEl = document.getElementById('selected-team-name');
    if (nameDisplayEl) {
        nameDisplayEl.textContent = name;
    } else {
        console.warn('Element #selected-team-name not found in DOM.');
    }
}

function resetDraft() {
    if (!confirm("Are you sure you want to reset the draft? This will clear all bids, nominations, and reset all budgets.")) {
        return;
    }

    fetch(`/draft/${ROOM_ID}/reset`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert("Draft has been reset.");
            location.reload();
        } else {
            alert("Error resetting draft: " + data.error);
        }
    })
    .catch(err => {
        console.error("Reset failed:", err);
        alert("Something went wrong.");
    });
}

function randomizeOrder() {
    socket.emit('randomize_order', { league_id: ROOM_ID });
}

function highlightCurrentNominator(userId) {
    document.querySelectorAll('.participant').forEach(el => el.classList.remove('current-nominator'));
    const activeCard = document.getElementById(`user-${userId}`);
    if (activeCard) {
        activeCard.classList.add('current-nominator');
    }
}


// ─── Helpers ──────────────────────────────────────────────────
function startCountdown(timerEndISO) {
    clearInterval(countdownInterval);
    const timerEnd = new Date(timerEndISO); // Ensure UTC parsing

    countdownInterval = setInterval(() => {
        const now = new Date();
        const secondsLeft = Math.max(0, Math.floor((timerEnd - now) / 1000));
        document.getElementById('timer-display').textContent = `⏱ ${secondsLeft}s`;

        if (secondsLeft <= 5) {
            document.getElementById('timer-display').style.color = 'red';
        } else {
            document.getElementById('timer-display').style.color = 'inherit';
        }

        if (secondsLeft <= 0) clearInterval(countdownInterval);
    }, 500);
}

// Countdown for "waiting for someone to nominate a team" (60s, no anti-snipe extension)
function startNominationCountdown(secondsRemaining) {
    clearInterval(countdownInterval);
    const timerEnd = new Date(Date.now() + secondsRemaining * 1000);
    countdownInterval = setInterval(() => {
        const now = new Date();
        const secondsLeft = Math.max(0, Math.floor((timerEnd - now) / 1000));
        document.getElementById('timer-display').textContent = `⏱ ${secondsLeft}s`;
        document.getElementById('timer-display').style.color =
            secondsLeft <= 5 ? 'red' : 'inherit';
        if (secondsLeft <= 0) clearInterval(countdownInterval);
    }, 500);
}

// Countdown for active bidding (anti-snipe: refreshes to 7s if it drops below 7s)
function startBiddingCountdown(secondsRemaining) {
    clearInterval(countdownInterval);
    const timerEnd = new Date(Date.now() + secondsRemaining * 1000);
    countdownInterval = setInterval(() => {
        const now = new Date();
        const secondsLeft = Math.max(0, Math.floor((timerEnd - now) / 1000));
        document.getElementById('timer-display').textContent = `⏱ ${secondsLeft}s`;
        document.getElementById('timer-display').style.color =
            secondsLeft <= 5 ? 'red' : 'inherit';
        if (secondsLeft <= 0) clearInterval(countdownInterval);
    }, 500);
}

function addLogEntry(message) {
    const list = document.getElementById('log-list');
    const li = document.createElement('li');
    li.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    list.append(li); // newest on bottom

    // Auto-scroll the container to the bottom
    const bidLog = document.getElementById('bid-log'); // or 'bid-log-container' if you use the wrapper
    bidLog.scrollBottom = bidLog.scrollHeight;
}

function updateBudgetDisplay(userId, amountSpent) {
    const nameEl = document.querySelector(`#user-${userId} .participant-name`);
    if (nameEl) {
        const match = nameEl.textContent.match(/\$(\d+)/);
        if (match) {
            const newBudget = parseInt(match[1]) - amountSpent;
            nameEl.textContent = nameEl.textContent.replace(/\$\d+/, `$${newBudget}`);
        }
    }
}

function setBidControlsEnabled(enabled) {
    const bidControls = document.getElementById('bid-controls');
    if (!bidControls) return;

    // Disable/enable every input and button inside bid-controls
    bidControls.querySelectorAll('input, button').forEach(el => {
        el.disabled = !enabled;
    });

    // Optional: visually grey it out when disabled
    bidControls.style.opacity = enabled ? '1' : '0.5';

    // Reset bid text box to 1 once a team is won
    if (!enabled) {
        const bidInput = document.getElementById('bid-input');
        if (bidInput) bidInput.value = 1;
    }
}

function updateAvailableTeams(teamWonId) {
    if (!teamWonId) return;

    const teamRow = document.querySelector('.team-row[data-id="' + teamWonId + '"]');
    if (teamRow) {
      teamRow.remove();
    }

    const teamOption = document.querySelector('#team-select option[value="' + teamWonId + '"]');
    if (teamOption) {
      teamOption.remove();
    }

    const teamSelectEl = document.getElementById('team-select');
    const nameDisplayEl = document.getElementById('selected-team-name');
    if (teamSelectEl && teamSelectEl.value === String(teamWonId)) {
      teamSelectEl.value = '';
      if (nameDisplayEl) nameDisplayEl.textContent = '';
    }
}
