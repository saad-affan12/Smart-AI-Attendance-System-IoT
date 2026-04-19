/* =========================================================
   SMART AI DASHBOARD — FINAL VERSION
   Features:
   ✔ Clock
   ✔ Attendance cards
   ✔ Stats
   ✔ Live IoT status
   ✔ Sound alerts
   ✔ Smooth updates
========================================================= */

/* ─── CLOCK ─── */
function updateClock() {
  const now = new Date();

  document.getElementById('clock').textContent =
    now.toLocaleTimeString();

  document.getElementById('date-display').textContent =
    now.toDateString();

  document.getElementById('footer-time').textContent =
    now.toDateString();
}
setInterval(updateClock, 1000);


/* ─── CAMERA ERROR ─── */
function handleCamError() {
  const img = document.getElementById('camera-stream');
  img.style.display = "none";

  const div = document.createElement("div");
  div.innerHTML = "📷 Camera not working";
  img.parentElement.appendChild(div);
}


/* ─── SOUND SYSTEM ─── */
function playBeep(type){
  const audio = new Audio();

  if(type === "present"){
    audio.src = "https://actions.google.com/sounds/v1/alarms/beep_short.ogg";
  }
  else if(type === "fake"){
    audio.src = "https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg";
  }

  audio.play();
}


/* ─── LIVE STATUS (IMPORTANT FIX) ─── */
let lastName = "";

async function updateLiveStatus(){
  try{
    const res = await fetch('/api/latest');
    const d = await res.json();

    const nameEl = document.getElementById("name");
    const idEl = document.getElementById("id");
    const statusEl = document.getElementById("status");

    if(!nameEl) return;

    nameEl.innerText = d.name || "--";
    idEl.innerText = d.id || "--";
    statusEl.innerText = d.status || "Waiting";

    // COLORS
    statusEl.style.color = "white";

    if(d.status === "Present"){
      statusEl.style.color = "lime";
    }
    else if(d.status === "Fake"){
      statusEl.style.color = "red";
    }
    else if(d.status === "Unknown"){
      statusEl.style.color = "orange";
    }

    // SOUND TRIGGER
    if(d.name !== lastName){
      if(d.status === "Present") playBeep("present");
      if(d.status === "Fake") playBeep("fake");
      lastName = d.name;
    }

  }catch(e){
    console.warn("Live status error", e);
  }
}


/* ─── RECORDS ─── */
let lastCount = -1;

async function refreshRecords(){
  try{
    const res = await fetch('/api/records');
    const data = await res.json();

    const container = document.getElementById('attendance-cards');

    if(data.length !== lastCount){
      container.innerHTML = data.map(renderCard).join('');
      lastCount = data.length;
    }

  }catch(e){
    console.warn("Records error", e);
  }
}


/* ─── CARD RENDER ─── */
function renderCard(d){
  return `
  <div class="att-card">
    <div class="card-body">
      <div class="card-name">${d.Name}</div>
      <div>ID: ${d.ID}</div>
      <div>${d.Status}</div>
      <div>${d.Time}</div>
    </div>
  </div>
  `;
}


/* ─── STATS ─── */
async function refreshStats(){
  try{
    const res = await fetch('/api/stats');
    const s = await res.json();

    document.getElementById('stat-present').textContent = s.present;
    document.getElementById('stat-late').textContent = s.late;
    document.getElementById('stat-total').textContent = s.total_today;
    document.getElementById('stat-registered').textContent = s.total_registered;

  }catch(e){
    console.warn("Stats error", e);
  }
}


/* ─── MAIN LOOP ─── */
async function poll(){
  await Promise.all([
    refreshRecords(),
    refreshStats(),
    updateLiveStatus()
  ]);
}

/* INIT */
poll();
setInterval(poll, 2000);