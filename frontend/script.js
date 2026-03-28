const API_BASE = "http://127.0.0.1:8000/api";

// State
let currentMediaPath = null;
let currentSrtPath = null;
let currentSegments = [];

// --- UI Helpers ---
function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
    
    event.target.classList.add('active');
    document.getElementById(`${tab}-tab`).classList.remove('hidden');
}

function updateStatus(message) {
    const box = document.getElementById("status-box");
    box.classList.remove("hidden");
    document.getElementById("status-text").innerText = message;
}

function enableExports() {
    document.getElementById("export-srt-btn").disabled = false;
    document.getElementById("export-video-btn").disabled = false;
}

// --- Styling Live Preview Engine ---
document.querySelectorAll('.style-controls input').forEach(el => {
    el.addEventListener('input', updateLivePreviewStyle);
});

function updateLivePreviewStyle() {
    const size = document.getElementById('style-size').value;
    const color = document.getElementById('style-color').value;
    const isBold = document.getElementById('style-bold').checked;
    const isItalic = document.getElementById('style-italic').checked;
    
    const list = document.getElementById('subtitle-list');
    
    // Inject directly into the CSSOM rendering root
    list.style.setProperty('--sub-size', `${size}px`);
    list.style.setProperty('--sub-color', color);
    list.style.setProperty('--sub-weight', isBold ? 'bold' : 'normal');
    list.style.setProperty('--sub-style', isItalic ? 'italic' : 'normal');
}

// --- 1. Upload File ---
async function uploadFile() {
    const fileInput = document.getElementById('media-file');
    if (!fileInput.files[0]) return alert("Select a file first!");

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    updateStatus("Uploading directly to local server folder...");
    
    try {
        const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData });
        const data = await res.json();
        
        if (res.ok) {
            currentMediaPath = data.saved_path;
            updateStatus(`Upload successful! You can now generate captions.`);
            document.getElementById('generate-btn').classList.remove('hidden');
        } else {
            updateStatus(`Error: ${data.detail}`);
        }
    } catch (e) {
        updateStatus("Connection failed. Is the Python backend running?");
    }
}

// --- 2. YouTube Link ---
async function processYouTube() {
    const url = document.getElementById('youtube-url').value;
    if (!url) return alert("Enter a YouTube URL first!");

    updateStatus("Downloading from YouTube using yt-dlp... This may take a moment.");
    
    try {
        const res = await fetch(`${API_BASE}/youtube`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({url})
        });
        const data = await res.json();
        
        if (res.ok) {
            currentMediaPath = data.video_path;
            updateStatus(`Download complete! You can now generate captions.`);
            document.getElementById('generate-btn').classList.remove('hidden');
        } else {
            updateStatus(`Download Error: ${data.detail}`);
        }
    } catch (e) {
        updateStatus("Connection failed. Is the Python backend running?");
    }
}

// --- 3. Start Transcription Pipeline ---
async function startTranscription() {
    if (!currentMediaPath) return;
    
    updateStatus("Evaluating Server Queue & Starting Transcription...");
    document.getElementById('generate-btn').disabled = true;

    try {
        const res = await fetch(`${API_BASE}/transcribe`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({file_path: currentMediaPath})
        });
        const data = await res.json();
        
        if (data.status === "rejected") {
            updateStatus(`Server rejected: ${data.message}`);
            document.getElementById('generate-btn').disabled = false;
        } else {
            // Server queued or is processing the request
            updateStatus(`Status: ${data.message} (Polling ID: ${data.job_id})`);
            pollJobQueue(data.job_id);
        }
    } catch (e) {
        updateStatus("Connection failed.");
        document.getElementById('generate-btn').disabled = false;
    }
}

// --- 4. Poll Queue Status ---
function pollJobQueue(jobId) {
    const pollInterval = setInterval(async () => {
        try {
            const res = await fetch(`${API_BASE}/transcribe/status/${jobId}`);
            const data = await res.json();
            
            if (data.status === "completed") {
                clearInterval(pollInterval);
                updateStatus("✅ Transcription rendering complete!");
                
                // Save data to state
                currentSrtPath = data.result.saved_srt_path;
                currentSegments = data.result.segments;
                
                // Unlock UI
                document.getElementById("editor-placeholder").classList.add("hidden");
                renderSubtitleEditor();
                enableExports();
                
            } else if (data.status === "processing") {
                updateStatus(`Processing (Heavy AI task active: Do not close browser)...`);
            } else if (data.status === "failed") {
                clearInterval(pollInterval);
                updateStatus(`Server crashed processing video: ${data.error}`);
            }
        } catch (e) {
            console.error(e);
        }
    }, 2000);
}

// --- 5. Render Live Editor ---
function renderSubtitleEditor() {
    const container = document.getElementById('editor-container');
    const list = document.getElementById('subtitle-list');
    
    container.classList.remove('hidden');
    list.innerHTML = "";
    
    currentSegments.forEach((seg, index) => {
        const item = document.createElement('div');
        item.className = 'subtitle-item subtitle-row';
        // Editable Text and Timestamp inputs
        item.innerHTML = `
            <div class="time-controls">
                <span>Start:</span>
                <input type="number" step="0.1" value="${parseFloat(seg.start).toFixed(2)}" class="time-input" onchange="updateTime(${index}, 'start', this.value)">
                <span> End:</span>
                <input type="number" step="0.1" value="${parseFloat(seg.end).toFixed(2)}" class="time-input" onchange="updateTime(${index}, 'end', this.value)">
            </div>
            <input type="text" value="${seg.text}" class="text-input" oninput="updateText(${index}, this.value)">
        `;
        list.appendChild(item);
    });
}

function updateText(index, newValue) {
    currentSegments[index].text = newValue;
}

function updateTime(index, field, newValue) {
    const val = parseFloat(newValue);
    if (!isNaN(val)) {
        currentSegments[index][field] = val;
    }
}

// --- 6. Export: Download Edited SRT ---
function downloadEditedSRT() {
    let srtText = "";
    
    const pad = (num, len) => String(num).padStart(len, '0');
    const formatTime = (secs) => {
        let h = Math.floor(secs / 3600);
        let m = Math.floor((secs % 3600) / 60);
        let s = Math.floor(secs % 60);
        let ms = Math.floor((secs % 1) * 1000);
        return `${pad(h, 2)}:${pad(m, 2)}:${pad(s, 2)},${pad(ms, 3)}`;
    };

    currentSegments.forEach((seg, i) => {
        srtText += `${i + 1}\n${formatTime(seg.start)} --> ${formatTime(seg.end)}\n${seg.text}\n\n`;
    });

    // Create a local virtual file for the browser
    const blob = new Blob([srtText], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "edited_auto_captions.srt";
    a.click();
}

// --- 7. Export: Burn Video ---
async function generateSubtitledVideo() {
    if (!currentMediaPath || !currentSegments || currentSegments.length === 0) return alert("Must generate captions first!");
    
    // UI State for Preview
    const container = document.getElementById("export-preview-container");
    const statusSpan = document.getElementById("export-status");
    const oldStatus = document.getElementById("export-status-old");
    const player = document.getElementById("final-video-player");
    const dlBtn = document.getElementById("download-icon-btn");
    
    container.classList.remove("hidden");
    oldStatus.classList.add("hidden");
    player.classList.add("hidden");
    dlBtn.classList.add("hidden");
    
    statusSpan.innerText = "Generating video preview... (This may take a minute)";
    statusSpan.style.color = "var(--text)";
    document.getElementById("export-video-btn").disabled = true;
    
    try {
        // Capture Styling Snapshot
        const styleOpts = {
            font_size: parseInt(document.getElementById('style-size').value),
            color: document.getElementById('style-color').value,
            bold: document.getElementById('style-bold').checked,
            italic: document.getElementById('style-italic').checked
        };
        
        // Send the absolute path AND the entirely modified live segment array
        const res = await fetch(`${API_BASE}/overlay`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ 
                video_path: currentMediaPath, 
                segments: currentSegments,
                style: styleOpts
            })
        });
        const data = await res.json();
        
        if (res.ok) {
            statusSpan.innerHTML = `<span style="color:var(--success)">✅ Success!</span>`;
            
            // 1. Tell HTML video player to load the FastAPI statically mounted media URL
            player.src = data.video_url;
            player.classList.remove("hidden");
            
            // 2. Configure the ⬇️ icon so users can natively download the file
            dlBtn.href = data.video_url;
            dlBtn.classList.remove("hidden");
            
        } else {
            statusSpan.innerText = `Error: ${data.detail}`;
        }
    } catch (e) {
        statusSpan.innerText = "Connection failed.";
    } finally {
        document.getElementById("export-video-btn").disabled = false;
    }
}
