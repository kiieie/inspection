const API_BASE = "/api";

let isMonitoring = true;
let lastTaskId = null;
let pollInterval = null;
let currentHighlightBox = null;

document.addEventListener("DOMContentLoaded", () => {
    // Initial Load (Live)
    setMonitoring(true);
    controlHistory('latest');
    startResultPolling();

    document.getElementById("btn-prev").addEventListener("click", () => {
        setMonitoring(false);
        controlHistory("prev");
    });
    document.getElementById("btn-next").addEventListener("click", () => {
        setMonitoring(false);
        controlHistory("next");
    });

    document.getElementById("btn-live").addEventListener("click", () => {
        setMonitoring(true);
        controlHistory("latest");
    });

    document.getElementById("btn-push").addEventListener("click", () => {
        setMonitoring(true);
        controlAction("push");
    });

    // Handle Window Resize to update highlight position
    window.addEventListener("resize", () => {
        if (currentHighlightBox) {
            highlightItem(currentHighlightBox);
        }
    });
});

function setMonitoring(active) {
    isMonitoring = active;
    const indicator = document.getElementById("status-indicator");
    if (indicator) {
        if (active) {
            indicator.textContent = "LIVE";
            indicator.className = "badge status-pass"; // Greenish
        } else {
            indicator.textContent = "HISTORY (Paused)";
            indicator.className = "badge status-fail"; // Reddish/Orange
        }
    }
}

async function controlHistory(direction) {
    if (!lastTaskId && direction !== 'latest') return;
    setLoading(true);
    try {
        const url = direction === 'latest'
            ? `${API_BASE}/latest_result`
            : `${API_BASE}/history/${direction}?current_id=${lastTaskId}`;

        const res = await fetch(url);
        const data = await res.json();

        if (data.status === "waiting") {
            setLoading(false);
            return;
        }

        lastTaskId = data.task_id;
        renderResult(data);
        setLoading(false);
    } catch (e) {
        console.error("History action failed", e);
        setLoading(false);
    }
}

async function controlAction(action) {
    setLoading(true);
    try {
        const res = await fetch(`${API_BASE}/control/${action}`);
        const data = await res.json();
        if (data.current_task) {
            updateInfo(data.current_task);
        }
        // Polling will catch the result since isMonitoring=true
    } catch (e) {
        console.error("Control action failed", e);
        setLoading(false);
    }
}

async function fetchStatus() {
    try {
        const res = await fetch(`${API_BASE}/status`);
        const data = await res.json();
        updateInfo(data);
    } catch (e) {
        console.error("Status fetch failed", e);
    }
}

function updateInfo(data) {
    if (data.error) return;
    document.getElementById("info-site").textContent = `Site: ${data.site}`;
    document.getElementById("info-mission").textContent = `Mission: ${data.mission}`;
    document.getElementById("info-insp").textContent = `Inspection: ${data.inspection}`;
    document.getElementById("info-idx").textContent = `Index: ${data.index + 1} / ${data.total}`;
}

function startResultPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(async () => {
        if (!isMonitoring) return; // Skip if in History Mode

        try {
            const res = await fetch(`${API_BASE}/latest_result`);
            const data = await res.json();

            if (data.status === "waiting") return;

            // In Live mode, always update if ID changes (presumably newer)
            if (data.task_id !== lastTaskId) {
                lastTaskId = data.task_id;
                renderResult(data);
                setLoading(false);
            }
        } catch (e) {
            console.error("Polling failed", e);
        }
    }, 1000);
}

function renderResult(data) {
    // Update Header Info (Sync with Result)
    if (data.site) document.getElementById("info-site").textContent = `Site: ${data.site}`;
    if (data.mission) document.getElementById("info-mission").textContent = `Mission: ${data.mission}`;
    if (data.inspection) document.getElementById("info-insp").textContent = `Inspection: ${data.inspection} (ID: ${data.task_id})`;

    // Update Image
    const imgParams = new Date().getTime(); // Prevent cache
    const imgEl = document.getElementById("result-image");

    if (data.web_image_url) {
        imgEl.src = `${data.web_image_url}?t=${imgParams}`;
        imgEl.style.display = "block";
        document.getElementById("placeholder-text").style.display = "none";
    } else {
        // Fallback or error
    }

    // Update Table
    const tbody = document.querySelector("#result-table tbody");
    tbody.innerHTML = "";

    data.items.forEach(item => {
        const tr = document.createElement("tr");

        // Judgment Styling
        const statusClass = item.status === "PASS" ? "status-pass" : "status-fail";

        // Parse Pos
        let posData = null;
        try {
            if (typeof item.pos === 'string') {
                posData = JSON.parse(item.pos);
            } else {
                posData = item.pos;
            }
        } catch (e) {
            console.warn("Invalid pos data", item.pos);
        }

        tr.innerHTML = `
            <td>${item.type}</td>
            <td class="font-mono">${item.value}</td>
            <td><span class="badge ${statusClass}">${item.status}</span></td>
            <td class="font-mono text-small">${Array.isArray(posData?.box) ? posData.box.join(", ") : "-"}</td> 
        `;

        // Click Event for Highlighting
        tr.addEventListener("click", () => {
            // Remove active class from others
            document.querySelectorAll("#result-table tbody tr").forEach(r => r.classList.remove("active-row"));
            tr.classList.add("active-row");

            if (posData && posData.box) {
                highlightItem(posData.box);
            } else {
                hideHighlight();
            }
        });

        tbody.appendChild(tr);
    });

    // Reset highlight on new load
    hideHighlight();
}

function highlightItem(box) {
    const img = document.getElementById("result-image");
    const highlight = document.getElementById("highlight-box");

    if (!img.naturalWidth) {
        return; // Image not loaded yet
    }

    currentHighlightBox = box; // Store for resize

    // Box Format: [x1, y1, x2, y2]
    const [x1, y1, x2, y2] = box;
    const w = x2 - x1;
    const h = y2 - y1;

    // Calculate Scale
    const scaleX = img.clientWidth / img.naturalWidth;
    const scaleY = img.clientHeight / img.naturalHeight;

    // Update Styles
    const finalLeft = x1 * scaleX;
    const finalTop = y1 * scaleY;
    const finalWidth = w * scaleX;
    const finalHeight = h * scaleY;

    highlight.style.left = `${finalLeft}px`;
    highlight.style.top = `${finalTop}px`;
    highlight.style.width = `${finalWidth}px`;
    highlight.style.height = `${finalHeight}px`;
    highlight.style.display = "block";
}

function hideHighlight() {
    currentHighlightBox = null;
    const highlight = document.getElementById("highlight-box");
    if (highlight) highlight.style.display = "none";
}

function setLoading(isLoading) {
    const overlay = document.getElementById("loading-overlay");
    if (isLoading) {
        overlay.style.display = "flex";
    } else {
        overlay.style.display = "none";
    }
}
