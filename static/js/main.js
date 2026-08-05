/* ==========================================================================
   Saathi AI Companion - Main Client Logic with Safe Element Binding
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

    // Load stored Groq key if available
    if (groqApiKeyInput && localStorage.getItem("saathi_groq_key")) {
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

    const authErrorMsg = document.getElementById("authErrorMsg");

    // Helper to show auth errors
    function showAuthError(msg) {
        if (authErrorMsg) {
            authErrorMsg.textContent = msg;
            authErrorMsg.style.display = "block";
        } else {
            alert(msg);
        }
    }

    function clearAuthError() {
        if (authErrorMsg) {
            authErrorMsg.textContent = "";
            authErrorMsg.style.display = "none";
        }
    }

    // 1. Check Auth Status (Mandatory Auth Wall)
    async function checkAuthStatus() {
        try {
            const res = await fetch("/api/me");
            const data = await res.json();
            if (data.status === "authenticated" && data.user) {
                currentUser = data.user;
                if (userInitial) userInitial.textContent = currentUser.display_name.charAt(0).toUpperCase();
                if (userNameDisplay) userNameDisplay.textContent = currentUser.display_name;
                if (userStatusText) userStatusText.textContent = `@${currentUser.username}`;
                if (openAuthModalBtn) openAuthModalBtn.textContent = "Logout";
                if (authModal) authModal.classList.remove("active");
            } else {
                currentUser = null;
                if (userInitial) userInitial.textContent = "G";
                if (userNameDisplay) userNameDisplay.textContent = "Guest";
                if (userStatusText) userStatusText.textContent = "Offline";
                if (openAuthModalBtn) openAuthModalBtn.textContent = "Login";
                // Show mandatory auth modal if guest
                if (authModal) authModal.classList.add("active");
            }
        } catch (e) {
            console.log("Auth check error:", e);
            if (authModal) authModal.classList.add("active");
        }
    }

    // Auth Button listener
    if (openAuthModalBtn) {
        openAuthModalBtn.addEventListener("click", () => {
            if (currentUser) {
                fetch("/api/logout", { method: "POST" }).then(() => {
                    checkAuthStatus();
                    loadChatHistory();
                });
            } else if (authModal) {
                clearAuthError();
                authModal.classList.add("active");
            }
        });
    }

    if (closeAuthBtn && authModal) {
        closeAuthBtn.addEventListener("click", () => {
            if (currentUser) {
                authModal.classList.remove("active");
            } else {
                showAuthError("Please create an account or login to start chatting!");
            }
        });
    }

    // Auth Tabs Switching
    if (tabLoginBtn && tabSignupBtn && loginForm && signupForm) {
        tabLoginBtn.addEventListener("click", () => {
            clearAuthError();
            tabLoginBtn.classList.add("active");
            tabSignupBtn.classList.remove("active");
            loginForm.style.display = "flex";
            signupForm.style.display = "none";
        });

        tabSignupBtn.addEventListener("click", () => {
            clearAuthError();
            tabSignupBtn.classList.add("active");
            tabLoginBtn.classList.remove("active");
            signupForm.style.display = "flex";
            loginForm.style.display = "none";
        });
    }

    // Login Submit Handler
    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearAuthError();
            const email = document.getElementById("loginEmail").value.trim();
            const p = document.getElementById("loginPassword").value.trim();
            try {
                const res = await fetch("/api/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username: email, password: p })
                });
                const data = await res.json();
                if (data.status === "success") {
                    if (authModal) authModal.classList.remove("active");
                    await checkAuthStatus();
                    loadChatHistory();
                } else {
                    showAuthError(data.error || "Invalid login credentials");
                }
            } catch (err) {
                showAuthError("Login failed. Please try again.");
            }
        });
    }

    // Signup Submit Handler
    if (signupForm) {
        signupForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearAuthError();
            const name = document.getElementById("signupName").value.trim();
            const email = document.getElementById("signupEmail").value.trim();
            const u = document.getElementById("signupUsername").value.trim();
            const p = document.getElementById("signupPassword").value.trim();

            if (!email) { showAuthError("Email address is required"); return; }
            if (!u) { showAuthError("Username is required"); return; }
            if (!p) { showAuthError("Password is required"); return; }

            try {
                const res = await fetch("/api/signup", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ display_name: name, email: email, username: u, password: p })
                });
                const data = await res.json();
                if (data.status === "success") {
                    if (authModal) authModal.classList.remove("active");
                    await checkAuthStatus();
                    loadChatHistory();
                } else {
                    showAuthError(data.error || "Registration failed. Try a different username/email.");
                }
            } catch (err) {
                showAuthError("Registration error. Please check your connection.");
            }
        });
    }

    // Personas Grid
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
            console.log("Fetch personas notice:", e);
        }
    }

    function renderPersonasGrid(personaList) {
        if (!personasGrid) return;
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
                if (personaModal) personaModal.classList.remove("active");
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
            role: "Romantic Girlfriend",
            badge: "Girlfriend 💖"
        };

        if (sidebarAvatar) sidebarAvatar.src = comp.avatar;
        if (sidebarCompanionName) sidebarCompanionName.childNodes[0].nodeValue = comp.name + " ";
        if (sidebarBadge) sidebarBadge.textContent = comp.badge;

        if (headerCompanionName) headerCompanionName.textContent = comp.name;
        if (headerCompanionRole) headerCompanionRole.textContent = `${comp.role} • Always here 💖`;
        if (typingText) typingText.textContent = `${comp.name} soch raha hai...`;
    }

    if (openPersonaModalBtn && personaModal) {
        openPersonaModalBtn.addEventListener("click", () => personaModal.classList.add("active"));
    }
    if (headerSwitchBtn && personaModal) {
        headerSwitchBtn.addEventListener("click", () => personaModal.classList.add("active"));
    }
    if (closePersonaBtn && personaModal) {
        closePersonaBtn.addEventListener("click", () => personaModal.classList.remove("active"));
    }

    // 3. Chat Handler
    if (userInput) {
        userInput.addEventListener("input", () => {
            userInput.style.height = "auto";
            userInput.style.height = Math.min(userInput.scrollHeight, 100) + "px";
        });

        userInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    if (sendBtn) {
        sendBtn.addEventListener("click", sendMessage);
    }

    async function sendMessage() {
        if (!userInput) return;
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

            if (data.status === "success" && data.response) {
                appendMessage("companion", data.response);
                if (ttsEnabled) speakText(data.response);
            } else {
                appendMessage("companion", "hnn main sun rhi hu... thoda net issue lag rha h, wapas bolo na! ☕");
            }
        } catch (e) {
            showTyping(false);
            appendMessage("companion", "hnn main sun rhi hu... connection issue h, wapas bolo na!");
        }
    }

    function appendMessage(sender, text, timestamp = "Just now") {
        if (!chatMessages) return;
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
            if (speechBtn) speechBtn.addEventListener("click", () => speakText(text));
        }

        chatMessages.appendChild(msgWrapper);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showTyping(show) {
        if (!typingIndicator) return;
        if (show) {
            typingIndicator.classList.add("active");
            if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
        } else {
            typingIndicator.classList.remove("active");
        }
    }

    async function loadChatHistory() {
        if (!chatMessages) return;
        try {
            const res = await fetch(`/api/history?companion_id=${activeCompanionId}`);
            const data = await res.json();
            chatMessages.innerHTML = "";
            const comp = personas[activeCompanionId] || { name: "Ananya" };

            if (data.status === "success" && data.history && data.history.length > 0) {
                data.history.forEach(msg => {
                    appendMessage(msg.role === "assistant" ? "companion" : "user", msg.content);
                });
            } else {
                appendMessage("companion", `hey... hlo! 👋 main hu ${comp.name}. pta h, akele feel krne ki zarurat nhi h... main hu na! bolo kya hua ☕✨`);
            }
        } catch (e) {
            console.log("History notice:", e);
        }
    }

    // Voice Mic (STT)
    if (voiceMicBtn && ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'hi-IN';

        recognition.onresult = (e) => {
            if (userInput) userInput.value = e.results[0][0].transcript;
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

    // TTS Voice Speech
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

    if (toggleTtsBtn) {
        toggleTtsBtn.addEventListener("click", () => {
            ttsEnabled = !ttsEnabled;
            if (ttsStatus) ttsStatus.textContent = ttsEnabled ? "ON" : "OFF";
            if (!ttsEnabled) window.speechSynthesis.cancel();
        });
    }

    // Memory Drawer
    if (toggleMemoryBtn) {
        toggleMemoryBtn.addEventListener("click", async () => {
            if (!currentUser) {
                alert("Please login first to access your personal memory bank!");
                if (authModal) authModal.classList.add("active");
                return;
            }
            if (memoryDrawer) memoryDrawer.classList.add("active");
            const res = await fetch("/api/memory");
            const data = await res.json();
            if (data.status === "success" && memoryList) {
                memoryList.innerHTML = "";
                const keys = Object.keys(data.memories);
                if (keys.length === 0) {
                    memoryList.innerHTML = `<div style="font-size: 0.85rem; color: var(--text-muted);">No memories stored yet.</div>`;
                } else {
                    keys.forEach(k => {
                        const item = document.createElement("div");
                        item.style.padding = "6px 10px";
                        item.style.background = "#F8FAFC";
                        item.style.borderRadius = "6px";
                        item.style.fontSize = "0.85rem";
                        item.innerHTML = `<strong>${k}:</strong> ${data.memories[k]}`;
                        memoryList.appendChild(item);
                    });
                }
            }
        });
    }

    if (closeMemoryBtn && memoryDrawer) {
        closeMemoryBtn.addEventListener("click", () => memoryDrawer.classList.remove("active"));
    }

    if (addMemBtn) {
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
                if (toggleMemoryBtn) toggleMemoryBtn.click();
            }
        });
    }

    // Settings Modal
    if (openSettingsBtn && settingsModal) {
        openSettingsBtn.addEventListener("click", () => settingsModal.classList.add("active"));
    }
    if (closeSettingsBtn && settingsModal) {
        closeSettingsBtn.addEventListener("click", () => settingsModal.classList.remove("active"));
    }
    if (saveSettingsBtn && settingsModal) {
        saveSettingsBtn.addEventListener("click", () => {
            if (groqApiKeyInput) localStorage.setItem("saathi_groq_key", groqApiKeyInput.value.trim());
            settingsModal.classList.remove("active");
            alert("Groq API key saved!");
        });
    }

    // Clear Chat
    if (clearChatBtn) {
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
    }

    // Mobile Sidebar Toggle & Reverse Backdrop Logic
    const sidebarOverlay = document.getElementById("sidebarOverlay");
    const closeSidebarBtn = document.getElementById("closeSidebarBtn");

    function openMobileSidebar() {
        if (sidebar) sidebar.classList.add("open");
        if (sidebarOverlay) sidebarOverlay.classList.add("active");
    }

    function closeMobileSidebar() {
        if (sidebar) sidebar.classList.remove("open");
        if (sidebarOverlay) sidebarOverlay.classList.remove("active");
    }

    if (mobileSidebarBtn) {
        mobileSidebarBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            if (sidebar && sidebar.classList.contains("open")) {
                closeMobileSidebar();
            } else {
                openMobileSidebar();
            }
        });
    }

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener("click", closeMobileSidebar);
    }

    if (closeSidebarBtn) {
        closeSidebarBtn.addEventListener("click", closeMobileSidebar);
    }

    // Auto-close sidebar on mobile when persona or options are selected
    if (openPersonaModalBtn) {
        openPersonaModalBtn.addEventListener("click", () => {
            closeMobileSidebar();
            if (personaModal) personaModal.classList.add("active");
        });
    }

    if (openAuthModalBtn) {
        openAuthModalBtn.addEventListener("click", () => {
            if (window.innerWidth <= 768) closeMobileSidebar();
        });
    }
});

