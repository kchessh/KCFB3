// static/js/draft.js
const socket = io();
let countdownInterval = null;
let currentNominationId = CURRENT_NOMINATION;

// ─── Connection ───────────────────────────────────────────────
socket.on('connect', () => {
    socket.emit('join_draft', { room_id: ROOM_ID });
    console.log('Connected to draft room:', ROOM_ID);
});

// ─── Incoming Events ──────────────────────────────────────────
socket.on('nomination_started', (data) => {
    currentNominationId = data.nomination_id;
    document.getElementById('current-team').textContent = `Team ID: ${data.team_id}`;
    document.getElementById('current-bid').textContent = `Current Bid: $${data.current_bid}`;
    document.getElementById('current-winner').textContent = `Leader: User ${data.current_winner}`;
    document.getElementById('bid-controls').style.display = 'block';

    addLogEntry(`🏷️ Team ${data.team_id} nominated! Starting at $${data.current_bid}`);
    startCountdown(data.timer_end);
});

socket.on('bid_placed', (data) => {
    document.getElementById('current-bid').textContent = `Current Bid: $${data.amount}`;
    document.getElementById('current-winner').textContent = `Leader: User ${data.user_id}`;
    addLogEntry(`💰 User ${data.user_id} bid $${data.amount}`);
});

socket.on('timer_update', (data) => {
    if (data.nomination_id === currentNominationId) {
        startCountdown(data.timer_end);
    }
});

socket.on('nomination_sold', (data) => {
    currentNominationId = null;
    clearInterval(countdownInterval);
    document.getElementById('timer-display').textContent = 'SOLD!';
    document.getElementById('bid-controls').style.display = 'none';

    const msg = data.winner_id
        ? `✅ Team ${data.team_id} sold to User ${data.winner_id} for $${data.final_price}!`
        : `❌ No bids — nomination cancelled.`;

    document.getElementById('current-team').textContent = msg;
    addLogEntry(msg);

    // Update winner's displayed budget
    updateBudgetDisplay(data.winner_id, data.final_price);
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
    socket.emit('nominate_team', {
        room_id: ROOM_ID,
        team_id: teamId,
        starting_bid: startingBid
    });
}

function placeBid() {
    const amount = parseInt(document.getElementById('bid-input').value);
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

// ─── Helpers ──────────────────────────────────────────────────
function startCountdown(timerEndISO) {
    clearInterval(countdownInterval);
    const timerEnd = new Date(timerEndISO + 'Z'); // Ensure UTC parsing

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
    list.prepend(li); // newest on top
}

function updateBudgetDisplay(userId, amountSpent) {
    const el = document.getElementById(`user-${userId}`);
    if (el) {
        const match = el.textContent.match(/\$(\d+)/);
        if (match) {
            const newBudget = parseInt(match<a href="" class="citation-link" target="_blank" style="vertical-align: super; font-size: 0.8em; margin-left: 3px;">[1]</a>) - amountSpent;
            el.textContent = el.textContent.replace(/\$\d+/, `$${newBudget}`);
        }
    }
}
