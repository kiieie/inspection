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
    }

    // 1. Render Expected Items
    const expectedTbody = document.querySelector("#expected-table tbody");
    if (expectedTbody) {
        expectedTbody.innerHTML = "";
        
        const resultItems = data.items || [];
        // Only classify as found if AI actually detected it (value is not 'Not Found')
        const foundTypes = new Set(
            resultItems
                .filter(item => item.value !== "Not Found")
                .map(item => item.type)
        );

        const expectedItems = data.expected_items || [];
        let expectedTypeCounts = {};
        
        expectedItems.forEach(item => {
            const tr = document.createElement("tr");
            expectedTypeCounts[item.type] = (expectedTypeCounts[item.type] || 0) + 1;
            tr.dataset.type = item.type; // For cross-highlighting
            tr.dataset.typeIdx = expectedTypeCounts[item.type]; // 1:1 matching
            let rangeTxt = "";
            if (item.min_value !== undefined && item.min_value !== null) {
                rangeTxt = `${item.min_value} ~ ${item.max_value}`;
            }

            const isFound = foundTypes.has(item.type);
            const statusHtml = isFound ? `<span class="badge status-pass">Found</span>` : `<span class="badge status-fail" style="background-color: var(--danger-color); color: white;">Not Found</span>`;

            // Find matching result logic
            let valText = "-";
            let judgeHtml = "-";

            if (isFound) {
                 const matchCandidates = resultItems.filter(r => r.type === item.type && r.value !== "Not Found");
                 const match = matchCandidates[expectedTypeCounts[item.type] - 1] || matchCandidates[0]; // fallback
                 if (match) {
                     valText = match.value || "-";
                     const judgeText = match.status || "-";
                     const judgeClass = (judgeText === "PASS" || judgeText.toLowerCase() === "ok") ? "status-pass" : (judgeText === "UNKNOWN" ? "status-unknown" : "status-fail");
                     judgeHtml = `<span class="badge ${judgeClass}">${judgeText}</span>`;
                 }
            }

            tr.innerHTML = `
                <td>${item.type}</td>
                <td>${item.facility_1 || ""} - ${item.facility_2 || ""}</td>
                <td class="font-mono">${rangeTxt}</td>
                <td style="font-weight: bold; color: #ffeb3b;">${valText}</td>
                <td>${judgeHtml}</td>
                <td>${statusHtml}</td>
            `;
            
            tr.addEventListener("click", () => {
                selectRow(item.type, null, tr, "expected-table"); // Expected items usually don't have pos yet
            });
            expectedTbody.appendChild(tr);
        });
    }

    // 2. Render Detected Results
    const resTbody = document.querySelector("#result-table tbody");
    if (resTbody) {
        resTbody.innerHTML = "";
        // Show all results including "Not Found" as requested by user
        const resultItems = data.items || [];
        let resultTypeCounts = {};
        
        resultItems.forEach(item => {
            let posData = null;
            try {
                if (typeof item.pos === 'string') posData = JSON.parse(item.pos);
                else posData = item.pos;
            } catch (e) { console.warn("Invalid pos data", item.pos); }

            // [display.md rule] Not Found items from DB should not be here
            if (item.value === "Not Found" || (!posData?.box || posData.box.every(v => v === 0) && !item.type.startsWith("Unmatched_"))) {
                return; // Skip NOT Found items completely
            }

            const tr = document.createElement("tr");
            resultTypeCounts[item.type] = (resultTypeCounts[item.type] || 0) + 1;
            tr.dataset.type = item.type; // For cross-highlighting
            tr.dataset.typeIdx = resultTypeCounts[item.type]; // 1:1 matching

            let displayType = item.type;
            let displayStatus = item.status || "UNKNOWN";
            let statusClass = item.status === "PASS" ? "status-pass" : (item.status === "FAIL" ? "status-fail" : "status-unknown");
            
            if (item.type.startsWith("Unmatched_")) {
                displayType = item.type.replace("Unmatched_", "");
                displayStatus = "Unmatched";
                statusClass = "status-unmatched"; 
            }

            tr.dataset.box = JSON.stringify(posData?.box || null);

            tr.innerHTML = `
                <td>${displayType}</td>
                <td class="font-mono">${item.value || ""}</td>
                <td><span class="badge ${statusClass}">${displayStatus}</span></td>
                <td class="font-mono text-small">${Array.isArray(posData?.box) ? posData.box.map(Math.round).join(", ") : "-"}</td> 
            `;

            tr.addEventListener("click", () => {
                selectRow(item.type, posData?.box, tr, "result-table");
            });

            resTbody.appendChild(tr);
        });
    }

    // Reset highlight on new load
    hideHighlight();
}

// Handler for cross-highlighting logic
function selectRow(type, box, clickedRow, sourceTableId) {
    // 1. Clear active-row from all tables
    document.querySelectorAll(".data-pane tbody tr").forEach(r => r.classList.remove("active-row"));

    // 2. Add active-row to the clicked row
    if (clickedRow) {
        clickedRow.classList.add("active-row");
    }

    // 3. Find 1:1 matching row in the OTHER table using typeIdx
    const otherTableId = sourceTableId === "expected-table" ? "result-table" : "expected-table";
    const typeIdx = clickedRow ? clickedRow.dataset.typeIdx : 1;
    let otherRow = document.querySelector(`#${otherTableId} tbody tr[data-type="${type}"][data-type-idx="${typeIdx}"]`);
    
    // [Fix] If missing in result-table, try to find an 'Unmatched_[type]' to show where AI actually found it
    // But since typeIdx might not match (Unmatched items are separate), just find the first available Unmatched item
    if (!otherRow && sourceTableId === "expected-table") {
        otherRow = document.querySelector(`#result-table tbody tr[data-type="Unmatched_${type}"]`);
    }

    // [Fix] Workaround: The "Detected Results (AI)" table actually includes BOTH Matched and Missed Expected points!
    // So if the user clicked "Not Found" in the result-table, it's actually an Expected Point that was missed.
    // We should try to find an "Unmatched" row in the same result-table that has the actual coordinates!
    if (sourceTableId === "result-table" && box && Array.isArray(box) && box.every(v => v === 0)) {
        // This is a "Not Found" row clicked in the right table (0,0,0,0)
        let unmatchedRow = document.querySelector(`#result-table tbody tr[data-type="Unmatched_${type}"]`);
        
        // [New Fallback] If exact label Unmatched is not found, fallback to ANY Unmatched detection
        // so the user can see where the AI found *something* that couldn't be mapped.
        if (!unmatchedRow) {
            unmatchedRow = document.querySelector(`#result-table tbody tr[data-type^="Unmatched_"]`);
        }

        if (unmatchedRow) {
            unmatchedRow.classList.add("active-row");
            if (unmatchedRow.dataset.box && unmatchedRow.dataset.box !== "null") {
                box = JSON.parse(unmatchedRow.dataset.box);
            }
        }
    }

    let finalBox = box;
    
    if (otherRow) {
        otherRow.classList.add("active-row");
        // if box is null but we clicked an expected item, read the box from the matched result row
        if (!finalBox && otherRow.dataset.box && otherRow.dataset.box !== "null") {
            finalBox = JSON.parse(otherRow.dataset.box);
        }
    }

    // [Fix] If we clicked an 'Unmatched' row in result-table, try to highlight the original expected point
    if (sourceTableId === "result-table" && type.startsWith("Unmatched_")) {
        const originalType = type.replace("Unmatched_", "");
        const fallbackExpectedRow = document.querySelector(`#expected-table tbody tr[data-type="${originalType}"]`);
        if (fallbackExpectedRow) {
            fallbackExpectedRow.classList.add("active-row");
        }
    }

    if (finalBox && Array.isArray(finalBox) && finalBox.some(v => v !== 0)) {
        highlightItem(finalBox);
    } else {
        hideHighlight();
    }
}

function highlightItem(box) {
    const img = document.getElementById("result-image");
    const container = img.parentElement;
    const highlight = document.getElementById("highlight-box");

    if (!img.naturalWidth) return; // Image not loaded yet

    currentHighlightBox = box; // Store for resize

    const [x1, y1, x2, y2] = box;
    const w = x2 - x1;
    const h = y2 - y1;

    // Calculate actual render size of object-fit: contain within container
    const imgRatio = img.naturalWidth / img.naturalHeight;
    const containerRatio = container.clientWidth / container.clientHeight;

    let renderWidth, renderHeight, offsetX = 0, offsetY = 0;

    if (containerRatio > imgRatio) {
        // Container is wider than image (pillarboxes on sides)
        renderHeight = container.clientHeight;
        renderWidth = renderHeight * imgRatio;
        offsetX = (container.clientWidth - renderWidth) / 2;
    } else {
        // Container is taller than image (letterboxes on top/bottom)
        renderWidth = container.clientWidth;
        renderHeight = renderWidth / imgRatio;
        offsetY = (container.clientHeight - renderHeight) / 2;
    }

    const scaleX = renderWidth / img.naturalWidth;
    const scaleY = renderHeight / img.naturalHeight;

    const finalLeft = offsetX + (x1 * scaleX);
    const finalTop = offsetY + (y1 * scaleY);
    const finalWidth = w * scaleX;
    const finalHeight = h * scaleY;

    highlight.style.left = `${finalLeft}px`;
    highlight.style.top = `${finalTop}px`;
    highlight.style.width = `${finalWidth}px`;
    highlight.style.height = `${finalHeight}px`;
    highlight.style.display = "block";
}

// Ensure highlight adjusts on window resize
window.addEventListener('resize', () => {
    if (currentHighlightBox) {
        highlightItem(currentHighlightBox);
    }
});

function hideHighlight() {
    currentHighlightBox = null;
    const highlight = document.getElementById("highlight-box");
    if (highlight) highlight.style.display = "none";
}

function setLoading(isLoading) {
    const overlay = document.getElementById("loading-overlay");
    if (isLoading) overlay.style.display = "flex";
    else overlay.style.display = "none";
}
