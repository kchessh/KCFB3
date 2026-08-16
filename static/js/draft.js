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
    startCountdown(data.timer_end);
});

socket.on('bid_placed', (data) => {
    document.getElementById('current-bid').textContent = `Current Bid: $${data.amount}`;
    document.getElementById('current-winner').textContent = `Leader: ${data.username}`;
    addLogEntry(`💰 ${data.username} bid $${data.amount}`);
});

socket.on('timer_update', (data) => {
    if (data.nomination_id === currentNominationId) {
        startCountdown(data.timer_end);
    }
});

socket.on('nomination_sold', (data) => {
    console.log('nomination_sold payload:', data);
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

socket.on('user_joined', (data) => {
    const el = document.getElementById(`user-${data.user_id}`);
    if (el) el.classList.add('connected');
});

socket.on('error', (data) => {
    alert(`⚠️ ${data.message}`);
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
    const el = document.getElementById(`user-${userId}`);
    if (el) {
        const match = el.textContent.match(/\$(\d+)/);
        if (match) {
            const newBudget = parseInt(match[1]) - amountSpent;
            el.textContent = el.textContent.replace(/\$\d+/, `$${newBudget}`);
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
