/* ==========================================================================
   Saathi AI Companion - Main Client Logic
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const chatMessages = document.getElementById("chatMessages");
    const userInput = document.getElementById("userInput");
    const sendBtn = document.getElementById("sendBtn");
    const voiceMicBtn = document.getElementById("voiceMicBtn");
    const typingIndicator = document.getElementById("typingIndicator");
    const activeModelLabel = document.getElementById("activeModelLabel");
    
    // Controls & Modals
    const toggleMemoryBtn = document.getElementById("toggleMemoryBtn");
    const memoryDrawer = document.getElementById("memoryDrawer");
    const closeMemoryBtn = document.getElementById("closeMemoryBtn");
    const memoryList = document.getElementById("memoryList");
    const addMemBtn = document.getElementById("addMemBtn");

    const openSettingsBtn = document.getElementById("openSettingsBtn");
    const settingsModal = document.getElementById("settingsModal");
    const closeSettingsBtn = document.getElementById("closeSettingsBtn");
    const cancelSettingsBtn = document.getElementById("cancelSettingsBtn");
    const saveSettingsBtn = document.getElementById("saveSettingsBtn");
    const groqApiKeyInput = document.getElementById("groqApiKeyInput");

    const clearChatBtn = document.getElementById("clearChatBtn");
    const toggleTtsBtn = document.getElementById("toggleTtsBtn");
    const ttsStatus = document.getElementById("ttsStatus");
    const mobileSidebarBtn = document.getElementById("mobileSidebarBtn");
    const sidebar = document.querySelector(".sidebar");

    // State Variables
    let ttsEnabled = false;
    let isRecording = false;
    let recognition = null;

    // Load stored Groq Key on startup
    const storedKey = localStorage.getItem("saathi_groq_key") || "";
    if (storedKey) {
        groqApiKeyInput.value = storedKey;
    }

    // Load Chat History from backend
    loadChatHistory();

    // 1. Auto-resize Textarea
    userInput.addEventListener("input", () => {
        userInput.style.height = "auto";
        userInput.style.height = Math.min(userInput.scrollHeight, 120) + "px";
    });

    userInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendBtn.addEventListener("click", sendMessage);

    // 2. Send Message Handler
    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        // Clear input field
        userInput.value = "";
        userInput.style.height = "auto";

        // Append User Message to UI
        appendMessage("user", text);

        // Show Typing Indicator
        showTyping(true);

        const apiKey = localStorage.getItem("saathi_groq_key") || "";

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: text,
                    api_key: apiKey
                })
            });

            const data = await response.json();
            showTyping(false);

            if (data.status === "success") {
                appendMessage("companion", data.response);

                // Update active model badge
                if (data.model) {
                    activeModelLabel.textContent = data.model;
                }

                // Speak if TTS enabled
                if (ttsEnabled) {
                    speakText(data.response);
                }
            } else {
                appendMessage("companion", "Arrey... Network me kuch dikkat aayi lagta hai. Wapas bolo na!");
            }
        } catch (err) {
            showTyping(false);
            appendMessage("companion", "Arrey yaar... thoda connection issue ho gaya. Par main yahi hu, wapas bolo!");
        }
    }

    // 3. Append Message to UI
    function appendMessage(sender, text, timestamp = "Just now") {
        const msgWrapper = document.createElement("div");
        msgWrapper.className = `message-wrapper ${sender}`;

        const isCompanion = sender === "companion";

        msgWrapper.innerHTML = `
            ${isCompanion ? `
            <div class="msg-avatar">
                <img src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&q=80" alt="Saathi">
            </div>` : ''}
            <div class="msg-content-box">
                <div class="msg-sender">${isCompanion ? 'Saathi' : 'You'}</div>
                <div class="msg-text">${formatMessageText(text)}</div>
                <div class="msg-meta">
                    <span class="msg-time">${timestamp}</span>
                    ${isCompanion ? `<button class="msg-speech-btn" title="Listen message"><i class="fa-solid fa-volume-high"></i></button>` : ''}
                </div>
            </div>
        `;

        // Attach Speech Button listener
        if (isCompanion) {
            const speechBtn = msgWrapper.querySelector(".msg-speech-btn");
            speechBtn.addEventListener("click", () => speakText(text));
        }

        chatMessages.appendChild(msgWrapper);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function formatMessageText(text) {
        return text.replace(/\n/g, "<br>");
    }

    function showTyping(show) {
        if (show) {
            typingIndicator.classList.add("active");
            chatMessages.scrollTop = chatMessages.scrollHeight;
        } else {
            typingIndicator.classList.remove("active");
        }
    }

    // 4. Quick Mood Prompt Chips
    document.querySelectorAll(".prompt-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const promptText = chip.getAttribute("data-prompt");
            userInput.value = promptText;
            sendMessage();
        });
    });

    // 5. Speech-to-Text (STT - Voice Input)
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'hi-IN'; // Default to Hindi/Hinglish recognition

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            userInput.value = transcript;
            isRecording = false;
            voiceMicBtn.classList.remove("recording");
            sendMessage();
        };

        recognition.onerror = () => {
            isRecording = false;
            voiceMicBtn.classList.remove("recording");
        };

        recognition.onend = () => {
            isRecording = false;
            voiceMicBtn.classList.remove("recording");
        };

        voiceMicBtn.addEventListener("click", () => {
            if (!isRecording) {
                recognition.start();
                isRecording = true;
                voiceMicBtn.classList.add("recording");
            } else {
                recognition.stop();
                isRecording = false;
                voiceMicBtn.classList.remove("recording");
            }
        });
    } else {
        voiceMicBtn.style.display = "none";
    }

    // 6. Text-to-Speech (TTS Voice Audio)
    function speakText(text) {
        if (!('speechSynthesis' in window)) return;
        window.speechSynthesis.cancel(); // Stop any active speech

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        // Try selecting a natural voice
        const voices = window.speechSynthesis.getVoices();
        const preferredVoice = voices.find(v => v.lang.includes("hi") || v.lang.includes("IN")) || voices[0];
        if (preferredVoice) {
            utterance.voice = preferredVoice;
        }

        window.speechSynthesis.speak(utterance);
    }

    toggleTtsBtn.addEventListener("click", () => {
        ttsEnabled = !ttsEnabled;
        ttsStatus.textContent = ttsEnabled ? "ON" : "OFF";
        if (!ttsEnabled) window.speechSynthesis.cancel();
    });

    // 7. Load History & Memory
    async function loadChatHistory() {
        try {
            const res = await fetch("/api/history");
            const data = await res.json();
            if (data.status === "success" && data.history.length > 0) {
                // Clear welcome message if history exists
                chatMessages.innerHTML = "";
                data.history.forEach(msg => {
                    appendMessage(msg.role === "assistant" ? "companion" : "user", msg.content);
                });
            }
        } catch (e) {
            console.log("History load notice:", e);
        }
    }

    // 8. Memory Drawer
    toggleMemoryBtn.addEventListener("click", openMemoryDrawer);
    closeMemoryBtn.addEventListener("click", () => memoryDrawer.classList.remove("active"));

    async function openMemoryDrawer() {
        memoryDrawer.classList.add("active");
        try {
            const res = await fetch("/api/memory");
            const data = await res.json();
            if (data.status === "success") {
                renderMemories(data.memories);
            }
        } catch (e) {
            console.log("Memory error:", e);
        }
    }

    function renderMemories(memories) {
        memoryList.innerHTML = "";
        const keys = Object.keys(memories);
        if (keys.length === 0) {
            memoryList.innerHTML = `<div class="memory-empty">Abhi tak koi stored memories nahi hain.</div>`;
            return;
        }

        keys.forEach(k => {
            const item = document.createElement("div");
            item.className = "memory-item";
            item.innerHTML = `<strong>${k}:</strong> <span>${memories[k]}</span>`;
            memoryList.appendChild(item);
        });
    }

    addMemBtn.addEventListener("click", async () => {
        const k = document.getElementById("newMemKey").value.trim();
        const v = document.getElementById("newMemVal").value.trim();
        if (k && v) {
            await fetch("/api/memory", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ key: k, value: v })
            });
            document.getElementById("newMemKey").value = "";
            document.getElementById("newMemVal").value = "";
            openMemoryDrawer();
        }
    });

    // 9. Settings Modal
    openSettingsBtn.addEventListener("click", () => settingsModal.classList.add("active"));
    closeSettingsBtn.addEventListener("click", () => settingsModal.classList.remove("active"));
    cancelSettingsBtn.addEventListener("click", () => settingsModal.classList.remove("active"));

    saveSettingsBtn.addEventListener("click", () => {
        const keyVal = groqApiKeyInput.value.trim();
        localStorage.setItem("saathi_groq_key", keyVal);
        settingsModal.classList.remove("active");
        alert("Groq API key saved successfully!");
    });

    // 10. Clear Chat History
    clearChatBtn.addEventListener("click", async () => {
        if (confirm("Kya aap saari chat history clear karna chahte hain?")) {
            await fetch("/api/clear", { method: "POST" });
            chatMessages.innerHTML = `
                <div class="message-wrapper companion">
                    <div class="msg-avatar">
                        <img src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&q=80" alt="Saathi">
                    </div>
                    <div class="msg-content-box">
                        <div class="msg-sender">Saathi</div>
                        <div class="msg-text">New fresh start! ✨ Main yahi hu, bolo kya kehna chahte ho?</div>
                    </div>
                </div>
            `;
        }
    });

    // Mobile Sidebar Toggle
    if (mobileSidebarBtn) {
        mobileSidebarBtn.addEventListener("click", () => {
            sidebar.classList.toggle("open");
        });
    }
});
