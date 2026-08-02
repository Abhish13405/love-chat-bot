/* ==========================================================================
   Saathi AI Companion - Main Client Logic with Auth & Persona Switcher
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
    // State
    let activeCompanionId = localStorage.getItem("saathi_companion_id") || "ananya";
    let currentUser = null;
    let personas = {};
    let ttsEnabled = false;
    let isRecording = false;
    let recognition = null;

    // DOM Elements
    const chatMessages = document.getElementById("chatMessages");
    const userInput = document.getElementById("userInput");
    const sendBtn = document.getElementById("sendBtn");
    const voiceMicBtn = document.getElementById("voiceMicBtn");
    const typingIndicator = document.getElementById("typingIndicator");
    const typingText = document.getElementById("typingText");

    // Header & Sidebar Elements
    const sidebarAvatar = document.getElementById("sidebarAvatar");
    const sidebarCompanionName = document.getElementById("sidebarCompanionName");
    const sidebarBadge = document.getElementById("sidebarBadge");
    const headerCompanionName = document.getElementById("headerCompanionName");
    const headerCompanionRole = document.getElementById("headerCompanionRole");

    const userInitial = document.getElementById("userInitial");
    const userNameDisplay = document.getElementById("userNameDisplay");
    const userStatusText = document.getElementById("userStatusText");
    const openAuthModalBtn = document.getElementById("openAuthModalBtn");

    // Modals
    const authModal = document.getElementById("authModal");
    const closeAuthBtn = document.getElementById("closeAuthBtn");
    const tabLoginBtn = document.getElementById("tabLoginBtn");
    const tabSignupBtn = document.getElementById("tabSignupBtn");
    const loginForm = document.getElementById("loginForm");
    const signupForm = document.getElementById("signupForm");

    const personaModal = document.getElementById("personaModal");
    const openPersonaModalBtn = document.getElementById("openPersonaModalBtn");
    const headerSwitchBtn = document.getElementById("headerSwitchBtn");
    const closePersonaBtn = document.getElementById("closePersonaBtn");
    const personasGrid = document.getElementById("personasGrid");

    const memoryDrawer = document.getElementById("memoryDrawer");
    const toggleMemoryBtn = document.getElementById("toggleMemoryBtn");
    const closeMemoryBtn = document.getElementById("closeMemoryBtn");
    const memoryList = document.getElementById("memoryList");
    const addMemBtn = document.getElementById("addMemBtn");

    const settingsModal = document.getElementById("settingsModal");
    const openSettingsBtn = document.getElementById("openSettingsBtn");
    const closeSettingsBtn = document.getElementById("closeSettingsBtn");
    const saveSettingsBtn = document.getElementById("saveSettingsBtn");
    const groqApiKeyInput = document.getElementById("groqApiKeyInput");

    const clearChatBtn = document.getElementById("clearChatBtn");
    const toggleTtsBtn = document.getElementById("toggleTtsBtn");
    const ttsStatus = document.getElementById("ttsStatus");
    const mobileSidebarBtn = document.getElementById("mobileSidebarBtn");
    const sidebar = document.querySelector(".sidebar");

    // Load Groq Key
    if (localStorage.getItem("saathi_groq_key")) {
        groqApiKeyInput.value = localStorage.getItem("saathi_groq_key");
    }

    // Initialize App
    init();

    async function init() {
        await checkAuthStatus();
        await fetchPersonas();
        updateActiveCompanionUI();
        loadChatHistory();
    }

    // 1. Check Auth Status
    async function checkAuthStatus() {
        try {
            const res = await fetch("/api/me");
            const data = await res.json();
            if (data.status === "authenticated" && data.user) {
                currentUser = data.user;
                userInitial.textContent = currentUser.display_name.charAt(0).toUpperCase();
                userNameDisplay.textContent = currentUser.display_name;
                userStatusText.textContent = `@${currentUser.username}`;
                openAuthModalBtn.textContent = "Logout";
            } else {
                currentUser = null;
                userInitial.textContent = "G";
                userNameDisplay.textContent = "Guest Mode";
                userStatusText.textContent = "Login for saved history";
                openAuthModalBtn.textContent = "Login";
            }
        } catch (e) {
            console.log("Auth check error:", e);
        }
    }

    // Auth Button click (Login or Logout)
    openAuthModalBtn.addEventListener("click", () => {
        if (currentUser) {
            // Logout
            fetch("/api/logout", { method: "POST" }).then(() => {
                checkAuthStatus();
                loadChatHistory();
            });
        } else {
            authModal.classList.add("active");
        }
    });

    closeAuthBtn.addEventListener("click", () => authModal.classList.remove("active"));

    // Auth Tabs
    tabLoginBtn.addEventListener("click", () => {
        tabLoginBtn.classList.add("active");
        tabSignupBtn.classList.remove("active");
        loginForm.style.display = "flex";
        signupForm.style.display = "none";
    });

    tabSignupBtn.addEventListener("click", () => {
        tabSignupBtn.classList.add("active");
        tabLoginBtn.classList.remove("active");
        signupForm.style.display = "flex";
        loginForm.style.display = "none";
    });

    // Login Form Submit
    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const u = document.getElementById("loginUsername").value.trim();
        const p = document.getElementById("loginPassword").value.trim();
        try {
            const res = await fetch("/api/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: u, password: p })
            });
            const data = await res.json();
            if (data.status === "success") {
                authModal.classList.remove("active");
                await checkAuthStatus();
                loadChatHistory();
            } else {
                alert(data.error || "Login failed");
            }
        } catch (err) {
            alert("Login error");
        }
    });

    // Signup Form Submit
    signupForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const name = document.getElementById("signupName").value.trim();
        const u = document.getElementById("signupUsername").value.trim();
        const p = document.getElementById("signupPassword").value.trim();
        try {
            const res = await fetch("/api/signup", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ display_name: name, username: u, password: p })
            });
            const data = await res.json();
            if (data.status === "success") {
                authModal.classList.remove("active");
                await checkAuthStatus();
                loadChatHistory();
            } else {
                alert(data.error || "Signup failed");
            }
        } catch (err) {
            alert("Signup error");
        }
    });

    // 2. Personas Selection
    async function fetchPersonas() {
        try {
            const res = await fetch("/api/personas");
            const data = await res.json();
            if (data.status === "success") {
                personas = {};
                data.personas.forEach(p => personas[p.id] = p);
                renderPersonasGrid(data.personas);
            }
        } catch (e) {
            console.log("Fetch personas error:", e);
        }
    }

    function renderPersonasGrid(personaList) {
        personasGrid.innerHTML = "";
        personaList.forEach(p => {
            const card = document.createElement("div");
            card.className = `persona-select-card ${p.id === activeCompanionId ? 'active' : ''}`;
            card.innerHTML = `
                <img src="${p.avatar}" alt="${p.name}" class="persona-card-img">
                <div class="persona-card-name">${p.name}</div>
                <div class="persona-card-role">${p.role}</div>
                <span class="persona-card-badge">${p.badge}</span>
            `;
            card.addEventListener("click", () => {
                selectCompanion(p.id);
                personaModal.classList.remove("active");
            });
            personasGrid.appendChild(card);
        });
    }

    function selectCompanion(companionId) {
        activeCompanionId = companionId;
        localStorage.setItem("saathi_companion_id", companionId);
        updateActiveCompanionUI();
        loadChatHistory();
        renderPersonasGrid(Object.values(personas));
    }

    function updateActiveCompanionUI() {
        const comp = personas[activeCompanionId] || {
            name: "Ananya",
            avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80",
            role: "Girlfriend / Girl Bestie",
            badge: "Girl Companion 💖"
        };

        sidebarAvatar.src = comp.avatar;
        sidebarCompanionName.childNodes[0].nodeValue = comp.name + " ";
        sidebarBadge.textContent = comp.badge;

        headerCompanionName.textContent = comp.name;
        headerCompanionRole.textContent = `${comp.role} • Always here for you ✨`;
        typingText.textContent = `${comp.name} soch raha hai...`;
    }

    openPersonaModalBtn.addEventListener("click", () => personaModal.classList.add("active"));
    headerSwitchBtn.addEventListener("click", () => personaModal.classList.add("active"));
    closePersonaBtn.addEventListener("click", () => personaModal.classList.remove("active"));

    // 3. Chat Logic
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

    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        userInput.value = "";
        userInput.style.height = "auto";

        appendMessage("user", text);
        showTyping(true);

        const apiKey = localStorage.getItem("saathi_groq_key") || "";

        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: text,
                    companion_id: activeCompanionId,
                    api_key: apiKey
                })
            });

            const data = await res.json();
            showTyping(false);

            if (data.status === "success") {
                appendMessage("companion", data.response);
                if (ttsEnabled) speakText(data.response);
            } else {
                appendMessage("companion", "Arrey... Network issue aa gaya. Phir se kaho na!");
            }
        } catch (e) {
            showTyping(false);
            appendMessage("companion", "Arrey yaar... Connection lost. Par main yahi hu!");
        }
    }

    function appendMessage(sender, text, timestamp = "Just now") {
        const msgWrapper = document.createElement("div");
        msgWrapper.className = `message-wrapper ${sender}`;

        const isCompanion = sender === "companion";
        const comp = personas[activeCompanionId] || {};

        msgWrapper.innerHTML = `
            ${isCompanion ? `
            <div class="msg-avatar">
                <img src="${comp.avatar || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80'}" alt="${comp.name || 'Companion'}">
            </div>` : ''}
            <div class="msg-content-box">
                <div class="msg-sender">${isCompanion ? (comp.name || 'Saathi') : (currentUser ? currentUser.display_name : 'You')}</div>
                <div class="msg-text">${text.replace(/\n/g, "<br>")}</div>
                <div class="msg-meta">
                    <span class="msg-time">${timestamp}</span>
                    ${isCompanion ? `<button class="msg-speech-btn" title="Listen message"><i class="fa-solid fa-volume-high"></i></button>` : ''}
                </div>
            </div>
        `;

        if (isCompanion) {
            const speechBtn = msgWrapper.querySelector(".msg-speech-btn");
            speechBtn.addEventListener("click", () => speakText(text));
        }

        chatMessages.appendChild(msgWrapper);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showTyping(show) {
        if (show) {
            typingIndicator.classList.add("active");
            chatMessages.scrollTop = chatMessages.scrollHeight;
        } else {
            typingIndicator.classList.remove("active");
        }
    }

    async function loadChatHistory() {
        try {
            const res = await fetch(`/api/history?companion_id=${activeCompanionId}`);
            const data = await res.json();
            chatMessages.innerHTML = "";
            const comp = personas[activeCompanionId] || { name: "Ananya" };

            if (data.status === "success" && data.history.length > 0) {
                data.history.forEach(msg => {
                    appendMessage(msg.role === "assistant" ? "companion" : "user", msg.content);
                });
            } else {
                appendMessage("companion", `hey... hlo! 👋 main hu ${comp.name}. pta h, akele feel krne ki zarurat nhi h... main hu na! bolo kya hua ☕✨`);
            }
        } catch (e) {
            console.log("History load error:", e);
        }
    }

    // Quick Mood Starters
    document.querySelectorAll(".prompt-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            userInput.value = chip.getAttribute("data-prompt");
            sendMessage();
        });
    });

    // Voice Recording (STT)
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'hi-IN';

        recognition.onresult = (e) => {
            userInput.value = e.results[0][0].transcript;
            isRecording = false;
            voiceMicBtn.classList.remove("recording");
            sendMessage();
        };
        recognition.onend = () => { isRecording = false; voiceMicBtn.classList.remove("recording"); };

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
    }

    // Voice Speech (TTS)
    function speakText(text) {
        if (!('speechSynthesis' in window)) return;
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        const voices = window.speechSynthesis.getVoices();
        const pref = voices.find(v => v.lang.includes("hi") || v.lang.includes("IN")) || voices[0];
        if (pref) utterance.voice = pref;
        window.speechSynthesis.speak(utterance);
    }

    toggleTtsBtn.addEventListener("click", () => {
        ttsEnabled = !ttsEnabled;
        ttsStatus.textContent = ttsEnabled ? "ON" : "OFF";
        if (!ttsEnabled) window.speechSynthesis.cancel();
    });

    // Memory Drawer
    toggleMemoryBtn.addEventListener("click", async () => {
        if (!currentUser) {
            alert("Please login first to access your personal memory bank!");
            authModal.classList.add("active");
            return;
        }
        memoryDrawer.classList.add("active");
        const res = await fetch("/api/memory");
        const data = await res.json();
        if (data.status === "success") {
            memoryList.innerHTML = "";
            const keys = Object.keys(data.memories);
            if (keys.length === 0) {
                memoryList.innerHTML = `<div style="font-size: 0.85rem; color: var(--text-secondary);">No memories stored yet.</div>`;
            } else {
                keys.forEach(k => {
                    const item = document.createElement("div");
                    item.style.padding = "8px 12px";
                    item.style.background = "#FFF8F6";
                    item.style.borderRadius = "8px";
                    item.style.fontSize = "0.85rem";
                    item.innerHTML = `<strong>${k}:</strong> ${data.memories[k]}`;
                    memoryList.appendChild(item);
                });
            }
        }
    });

    closeMemoryBtn.addEventListener("click", () => memoryDrawer.classList.remove("active"));

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
            toggleMemoryBtn.click();
        }
    });

    // Settings
    openSettingsBtn.addEventListener("click", () => settingsModal.classList.add("active"));
    closeSettingsBtn.addEventListener("click", () => settingsModal.classList.remove("active"));
    saveSettingsBtn.addEventListener("click", () => {
        localStorage.setItem("saathi_groq_key", groqApiKeyInput.value.trim());
        settingsModal.classList.remove("active");
        alert("Groq API key saved!");
    });

    // Clear History
    clearChatBtn.addEventListener("click", async () => {
        if (confirm("Clear chat history for this companion?")) {
            await fetch("/api/clear", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ companion_id: activeCompanionId })
            });
            loadChatHistory();
        }
    });

    if (mobileSidebarBtn) {
        mobileSidebarBtn.addEventListener("click", () => sidebar.classList.toggle("open"));
    }
});
