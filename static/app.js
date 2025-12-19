const PAGE = document.body.dataset.page;
const errorBanner = document.getElementById("error-banner");

function showError(message) {
  if (!errorBanner) return;
  errorBanner.textContent = message;
  errorBanner.hidden = false;
}

function clearError() {
  if (!errorBanner) return;
  errorBanner.textContent = "";
  errorBanner.hidden = true;
}

function redirectHome() {
  window.location.href = "/";
}

function getQueryParams() {
  const params = new URLSearchParams(window.location.search);
  return {
    accessCode: params.get("access_code") || "",
    name: params.get("name") || "",
    isOrganizer: params.get("is_organizer") === "true",
  };
}

function renderIndex() {
  const form = document.getElementById("join-form");
  form?.addEventListener("submit", (evt) => {
    evt.preventDefault();
    const accessCode = document.getElementById("access-code-input").value.trim();
    const name = document.getElementById("name-input").value.trim();
    const isOrganizer = document.getElementById("organizer-input").checked;
    if (!accessCode || !name) {
      showError("Please provide access code and name.");
      return;
    }
    clearError();
    const params = new URLSearchParams({
      access_code: accessCode,
      name,
      is_organizer: String(isOrganizer),
    });
    window.location.href = `/board?${params.toString()}`;
  });
}

async function fetchJson(url, options, accessCode) {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Access-Code": accessCode,
      ...(options && options.headers),
    },
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      if (data.error) message = data.error;
    } catch (err) {
      // ignore
    }
    throw new Error(message);
  }
  const contentType = response.headers.get("Content-Type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return null;
}

function createStickyElement(note, scores, ownVotes, isVoting, isFinished, onMove, onVoteChange) {
  const div = document.createElement("div");
  div.className = "sticky";
  div.dataset.id = note.id;
  div.style.left = `${note.x}px`;
  div.style.top = `${note.y}px`;
  div.dataset.x = note.x;
  div.dataset.y = note.y;
  div.style.background = note.color || "#fff8b3";

  const text = document.createElement("div");
  text.textContent = note.text;
  div.appendChild(text);

  const meta = document.createElement("div");
  meta.className = "meta";
  const author = document.createElement("span");
  author.textContent = note.author_name;
  meta.appendChild(author);
  const score = document.createElement("span");
  const totalScore = scores[note.id] || 0;
  if (isVoting || isFinished) {
    score.textContent = `Points: ${totalScore}`;
    meta.appendChild(score);
  }
  div.appendChild(meta);

  if (isVoting && typeof onVoteChange === "function") {
    const voteWrapper = document.createElement("div");
    voteWrapper.className = "vote-control";
    const label = document.createElement("label");
    label.textContent = "Your points";
    const input = document.createElement("input");
    input.type = "number";
    input.min = "0";
    input.max = "5";
    input.value = ownVotes[note.id] || 0;
    input.addEventListener("change", (event) => {
      let val = parseInt(event.target.value, 10);
      if (Number.isNaN(val)) val = 0;
      val = Math.max(0, Math.min(5, val));
      event.target.value = val;
      onVoteChange(note.id, val);
    });
    voteWrapper.appendChild(label);
    voteWrapper.appendChild(input);
    div.appendChild(voteWrapper);
  }

  if (!isFinished && typeof onMove === "function") {
    attachDragHandlers(div, onMove);
  }

  return div;
}

function attachDragHandlers(element, onMove) {
  let isDragging = false;
  let offsetX = 0;
  let offsetY = 0;

  element.addEventListener("mousedown", (event) => {
    isDragging = true;
    offsetX = event.offsetX;
    offsetY = event.offsetY;
    element.classList.add("dragging");
  });

  document.addEventListener("mouseup", (event) => {
    if (!isDragging) return;
    isDragging = false;
    element.classList.remove("dragging");
    onMove(parseFloat(element.dataset.x), parseFloat(element.dataset.y));
  });

  document.addEventListener("mousemove", (event) => {
    if (!isDragging) return;
    const parent = element.parentElement.getBoundingClientRect();
    const x = event.clientX - parent.left - offsetX;
    const y = event.clientY - parent.top - offsetY;
    element.style.left = `${x}px`;
    element.style.top = `${y}px`;
    element.dataset.x = x;
    element.dataset.y = y;
  });
}

function renderBoard() {
  const { accessCode, name, isOrganizer } = getQueryParams();
  const phaseLabel = document.getElementById("phase-label");
  const remainingPointsLabel = document.getElementById("remaining-points");
  const userNameLabel = document.getElementById("user-name");
  const addSection = document.getElementById("add-note-section");
  const noteInput = document.getElementById("note-text");
  const addButton = document.getElementById("add-note");
  const canvas = document.getElementById("board-canvas");
  const organizerControls = document.getElementById("organizer-controls");
  const startVotingBtn = document.getElementById("start-voting");
  const finishBtn = document.getElementById("finish-board");
  const resetBtn = document.getElementById("reset-board");
  let currentPhase = "GENERATING";

  if (!accessCode || !name) {
    redirectHome();
    return;
  }

  userNameLabel.textContent = `User: ${name}${isOrganizer ? " (organizer)" : ""}`;

  function computeRemaining(votes) {
    const allocations = votes[name] || {};
    const used = Object.values(allocations).reduce((acc, v) => acc + v, 0);
    return Math.max(0, 5 - used);
  }

  async function joinBoard() {
    try {
      await fetchJson("/api/join", {
        method: "POST",
        body: JSON.stringify({ name, is_organizer: isOrganizer }),
      }, accessCode);
      clearError();
    } catch (error) {
      if (!String(error.message).includes("already taken")) {
        showError(`Failed to join: ${error.message}`);
        redirectHome();
        throw error;
      }
    }
  }

  function renderBoardState(data) {
    currentPhase = data.phase;
    phaseLabel.textContent = data.phase;
    const remaining = computeRemaining(data.votes);
    remainingPointsLabel.textContent = `Remaining points: ${remaining}`;
    addSection.hidden = data.phase !== "GENERATING";
    organizerControls.hidden = !isOrganizer;
    canvas.innerHTML = "";
    data.stickies.forEach((note) => {
      const stickyEl = createStickyElement(
        note,
        data.scores,
        data.votes[name] || {},
        data.phase === "VOTING",
        data.phase === "FINISHED",
        async (x, y) => {
          try {
            await fetchJson(`/api/stickies/${note.id}/move`, {
              method: "POST",
              body: JSON.stringify({ name, x, y }),
            }, accessCode);
            clearError();
          } catch (error) {
            showError(`Move failed: ${error.message}`);
          }
        },
        async (noteId, val) => {
          try {
            await fetchJson("/api/votes", {
              method: "POST",
              body: JSON.stringify({ name, sticky_id: noteId, points: val }),
            }, accessCode);
            clearError();
            const updated = await fetchJson("/api/board", { method: "GET" }, accessCode);
            renderBoardState(updated);
          } catch (error) {
            showError(`Vote failed: ${error.message}`);
          }
        }
      );
      canvas.appendChild(stickyEl);
    });
  }

  addButton?.addEventListener("click", async () => {
    if (currentPhase === "FINISHED") {
      showError("Board is finished. Changes are not allowed.");
      return;
    }
    const text = noteInput.value.trim();
    if (!text) return;
    const x = Math.floor(Math.random() * 400);
    const y = Math.floor(Math.random() * 300);
    try {
      await fetchJson("/api/stickies", {
        method: "POST",
        body: JSON.stringify({ name, text, x, y }),
      }, accessCode);
      clearError();
      noteInput.value = "";
      const updated = await fetchJson("/api/board", { method: "GET" }, accessCode);
      renderBoardState(updated);
    } catch (error) {
      showError(`Add failed: ${error.message}`);
    }
  });

  startVotingBtn?.addEventListener("click", async () => {
    try {
      await fetchJson("/api/phase", {
        method: "POST",
        body: JSON.stringify({ name, phase: "VOTING" }),
      }, accessCode);
      clearError();
      const updated = await fetchJson("/api/board", { method: "GET" }, accessCode);
      renderBoardState(updated);
    } catch (error) {
      showError(`Cannot start voting: ${error.message}`);
    }
  });

  finishBtn?.addEventListener("click", async () => {
    try {
      await fetchJson("/api/phase", {
        method: "POST",
        body: JSON.stringify({ name, phase: "FINISHED" }),
      }, accessCode);
      clearError();
      const updated = await fetchJson("/api/board", { method: "GET" }, accessCode);
      renderBoardState(updated);
    } catch (error) {
      showError(`Cannot finish: ${error.message}`);
    }
  });

  resetBtn?.addEventListener("click", async () => {
    if (!confirm("Reset board?")) return;
    try {
      await fetchJson("/api/reset", {
        method: "POST",
        body: JSON.stringify({ name }),
      }, accessCode);
      clearError();
      redirectHome();
    } catch (error) {
      showError(`Reset failed: ${error.message}`);
    }
  });

  let poller = null;
  async function pollBoard() {
    try {
      const data = await fetchJson("/api/board", { method: "GET" }, accessCode);
      renderBoardState(data);
    } catch (error) {
      console.error("Polling error", error.message);
    }
  }

  joinBoard().then(() => {
    pollBoard();
    poller = setInterval(pollBoard, 2500);
  });

  window.addEventListener("beforeunload", () => {
    if (poller) clearInterval(poller);
  });
}

if (PAGE === "index") {
  renderIndex();
} else if (PAGE === "board") {
  renderBoard();
}
