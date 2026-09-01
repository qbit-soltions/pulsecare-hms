/**
 * PulseCare Mitra — Dedicated Real-Time Conversational AI Voice Assistant v4.0
 * 
 * 100% Standalone & Independent Feature:
 * - Real-time conversational microphone stream via Web Speech API (Free STT)
 * - Intelligent Clinical & Hospital Knowledge via Gemini 2.5 Flash / Smart Healthcare Engine
 * - Natural spoken voice audio response via Web Audio & TTS
 * - Interactive action cards (OPD, Beds, Doctors, Emergency 108, Pharmacy, ABHA)
 */

(function () {
  'use strict';

  const AI_LANGS = {
    hi: { code: "hi", bcp47: "hi-IN", name: "हिंदी", greeting: "नमस्ते! मैं पल्सकेयर मित्र हूँ। आप मुझसे अस्पताल, डॉक्टर, खाली बेड या स्वास्थ्य लक्षणों के बारे में पूछ सकते हैं।" },
    ta: { code: "ta", bcp47: "ta-IN", name: "தமிழ்", greeting: "வணக்கம்! நான் பல்ஸ்கேர் மித்ரா. மருத்துவர்கள், படுக்கை இருப்பு அல்லது அவசர உதவி பற்றி கேளுங்கள்." },
    te: { code: "te", bcp47: "te-IN", name: "తెలుగు", greeting: "నమస్కారం! నేను పల్స్‌కేర్ మిత్ర. వైద్యులు, ఖాళీ పడకలు లేదా అత్యవసర సేవల గురించి అడగండి." },
    bn: { code: "bn", bcp47: "bn-IN", name: "বাংলা", greeting: "নমস্কার! আমি পাল্সকেয়ার মিত্র। ডাক্তার, বেড বা স্বাস্থ্য বিষয়ে আমাকে জিজ্ঞাসা করুন।" },
    mr: { code: "mr", bcp47: "mr-IN", name: "मराठी", greeting: "नमस्कार! मी पल्सकेअर मित्र आहे. डॉक्टर, खाटा किंवा उपचारांबद्दल मला विचारा." },
    gu: { code: "gu", bcp47: "gu-IN", name: "ગુજરાતી", greeting: "નમસ્તે! હું પલ્સકેર મિત્ર છું. હોસ્પિટલ, ડૉક્ટર અથવા સારવાર વિશે પૂછો." },
    en: { code: "en", bcp47: "en-IN", name: "English", greeting: "Hello! I am PulseCare Mitra, your healthcare AI assistant. Ask me about doctors, available beds, symptoms, or hospital services." }
  };

  const QUICK_PROMPTS = {
    hi: [
      { text: "अस्पताल में खाली बेड की स्थिति क्या है?", label: "🛏️ उपलब्ध बेड" },
      { text: "आज कौन से डॉक्टर ड्यूटी पर हैं?", label: "👨‍⚕️ डॉक्टर सूची" },
      { text: "इमरजेंसी 108 एम्बुलेंस सहायता चाहिए", label: "🚑 इमरजेंसी 108" },
      { text: "फार्मेसी में जरूरी दवाइयां चेक करें", label: "💊 फार्मेसी" },
      { text: "नया ABHA हेल्थ कार्ड कैसे बनाएं?", label: "🆔 ABHA कार्ड" }
    ],
    ta: [
      { text: "மருத்துவமனையில் படுக்கைகள் காலியாக உள்ளதா?", label: "🛏️ காலியான படுக்கைகள்" },
      { text: "இன்று பணியில் உள்ள மருத்துவர்கள் யார்?", label: "👨‍⚕️ மருத்துவர்கள்" },
      { text: "108 அவசர ஆம்புலன்ஸ் உதவி", label: "🚑 அவசர உதவி 108" },
      { text: "மருந்தகத்தில் மருந்துகள் இருப்பு உள்ளதா?", label: "💊 மருந்துகள்" }
    ],
    te: [
      { text: "ఆసుపత్రిలో ఖాళీ పడకల వివరాలు ఏమిటి?", label: "🛏️ ఖాళీ పడకలు" },
      { text: "డ్యూటీలో ఉన్న వైద్యుల జాబితా", label: "👨‍⚕️ వైద్యులు" },
      { text: "108 అత్యవసర అంబులెన్స్ సేవలు", label: "🚑 అత్యవసరం 108" }
    ],
    en: [
      { text: "How many hospital beds are currently available?", label: "🛏️ Available Beds" },
      { text: "Which doctors and specialists are on duty today?", label: "👨‍⚕️ Doctors On-Duty" },
      { text: "Call 108 National Emergency Ambulance", label: "🚑 Emergency 108" },
      { text: "Check pharmacy medicine stock and inventory", label: "💊 Pharmacy Stock" },
      { text: "How do I register for an ABHA Health Card?", label: "🆔 ABHA Card" },
      { text: "I have fever and body ache, what should I do?", label: "🩺 Symptom Guidance" }
    ]
  };

  let recognition = null;
  let isListening = false;
  let isThinking = false;
  let activeAudio = null;
  let conversationHistory = [];
  const speechRecognitionSupported = ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window);

  function getActiveLang() {
    const pMatch = document.cookie.match(/(?:^|;\s*)pulse_lang=([^;]+)/);
    if (pMatch && pMatch[1] && AI_LANGS[pMatch[1]]) return pMatch[1];
    const gMatch = document.cookie.match(/(?:^|;\s*)googtrans=\/en\/([^;]+)/);
    if (gMatch && gMatch[1] && AI_LANGS[gMatch[1]]) return gMatch[1];
    const stored = localStorage.getItem("pulsecare_lang");
    if (stored && AI_LANGS[stored]) return stored;
    return "en";
  }

  function stopAllSpeech() {
    if (activeAudio) {
      activeAudio.pause();
      activeAudio.currentTime = 0;
      activeAudio = null;
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  }

  function playVoiceAudio(text, onEndCallback) {
    stopAllSpeech();
    if (!text || !text.trim()) return;

    const langKey = getActiveLang();
    const langConfig = AI_LANGS[langKey] || AI_LANGS.en;
    const cleanText = text.replace(/[\n\r]+/g, " ").replace(/\s{2,}/g, " ").trim();
    const audioUrl = `/api/tts?lang=${encodeURIComponent(langConfig.code)}&q=${encodeURIComponent(cleanText.substring(0, 250))}`;
    
    const audio = new Audio(audioUrl);
    activeAudio = audio;

    let fallbackTriggered = false;
    function runSpeechSynthesisFallback() {
      if (fallbackTriggered) return;
      fallbackTriggered = true;
      if (activeAudio === audio) activeAudio = null;

      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
        const utter = new SpeechSynthesisUtterance(cleanText);
        utter.lang = langConfig.bcp47 || "en-IN";
        utter.rate = 0.95;
        utter.onend = function () {
          if (onEndCallback) onEndCallback();
        };
        utter.onerror = function () {
          if (onEndCallback) onEndCallback();
        };
        window.speechSynthesis.speak(utter);
      } else if (onEndCallback) {
        onEndCallback();
      }
    }

    audio.onended = function () {
      activeAudio = null;
      if (onEndCallback) onEndCallback();
    };

    audio.onerror = function () {
      runSpeechSynthesisFallback();
    };

    audio.play().catch(function () {
      runSpeechSynthesisFallback();
    });
  }

  function initSpeechRec() {
    if (!speechRecognitionSupported) return null;
    const SpeechClass = window.SpeechRecognition || window.webkitSpeechRecognition;
    const rec = new SpeechClass();
    rec.continuous = false;
    rec.interimResults = true;
    rec.maxAlternatives = 1;
    return rec;
  }

  function startListening() {
    stopAllSpeech();
    const langKey = getActiveLang();
    const langConfig = AI_LANGS[langKey] || AI_LANGS.en;

    const statusEl = document.getElementById("ai-modal-status");
    const micRing = document.getElementById("ai-mic-ring");
    const waveEl = document.getElementById("ai-modal-wave");
    const liveTranscript = document.getElementById("ai-live-transcript");

    if (!speechRecognitionSupported) {
      if (statusEl) statusEl.innerHTML = `<span class="text-danger"><i class="bi bi-exclamation-triangle-fill me-1"></i>Voice mic is not supported in this browser. Please type below.</span>`;
      return;
    }

    try {
      if (recognition) {
        recognition.abort();
      }
      recognition = initSpeechRec();
      if (!recognition) return;

      recognition.lang = langConfig.bcp47 || "en-IN";

      recognition.onstart = function () {
        isListening = true;
        if (micRing) micRing.classList.add("active");
        if (waveEl) waveEl.classList.remove("d-none");
        if (statusEl) statusEl.innerHTML = `<span class="text-primary fw-bold"><i class="bi bi-mic-fill me-1"></i>Listening in ${langConfig.name}...</span> Speak your question`;
        if (liveTranscript) {
          liveTranscript.innerText = "Listening to your voice...";
          liveTranscript.classList.remove("d-none");
        }
      };

      recognition.onresult = function (event) {
        let interimText = "";
        let finalText = "";

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalText += event.results[i][0].transcript;
          } else {
            interimText += event.results[i][0].transcript;
          }
        }

        const text = finalText || interimText;
        if (liveTranscript && text) {
          liveTranscript.innerText = `"${text}"`;
        }

        if (finalText && finalText.trim()) {
          processUserQuery(finalText.trim());
        }
      };

      recognition.onerror = function (event) {
        isListening = false;
        if (micRing) micRing.classList.remove("active");
        if (waveEl) waveEl.classList.add("d-none");
        if (statusEl) {
          if (event.error === "no-speech") {
            statusEl.innerHTML = `<span class="text-muted">No speech detected. Tap microphone to speak.</span>`;
          } else {
            statusEl.innerHTML = `<span class="text-warning"><i class="bi bi-info-circle me-1"></i>${event.error}. Tap microphone or type below.</span>`;
          }
        }
      };

      recognition.onend = function () {
        isListening = false;
        if (micRing) micRing.classList.remove("active");
        if (waveEl) waveEl.classList.add("d-none");
      };

      recognition.start();
    } catch (e) {
      console.warn("AI Voice Assistant Speech Recognition error:", e);
      if (statusEl) statusEl.innerText = "Tap microphone to speak.";
    }
  }

  function stopListening() {
    if (recognition && isListening) {
      recognition.stop();
    }
    isListening = false;
    const micRing = document.getElementById("ai-mic-ring");
    const waveEl = document.getElementById("ai-modal-wave");
    if (micRing) micRing.classList.remove("active");
    if (waveEl) waveEl.classList.add("d-none");
  }

  async function processUserQuery(queryText) {
    if (!queryText || !queryText.trim()) return;
    stopListening();
    stopAllSpeech();

    const langKey = getActiveLang();
    const statusEl = document.getElementById("ai-modal-status");
    const liveTranscript = document.getElementById("ai-live-transcript");
    const chatFeed = document.getElementById("ai-chat-feed");

    if (liveTranscript) liveTranscript.classList.add("d-none");
    if (statusEl) statusEl.innerHTML = `<span class="spinner-border spinner-border-sm text-primary me-2"></span>Thinking & searching healthcare network...`;

    // Append User Message to UI
    appendChatMessage("user", queryText);

    try {
      const res = await fetch("/api/ai-voice/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: queryText,
          language: langKey,
          current_url: window.location.pathname
        })
      });

      const data = await res.json();
      if (data && data.success) {
        const reply = data.reply || "I am here to assist you with healthcare services.";
        if (statusEl) statusEl.innerHTML = `<span class="text-success fw-bold"><i class="bi bi-check-circle-fill me-1"></i>Spoken in ${AI_LANGS[langKey] ? AI_LANGS[langKey].name : 'English'}</span>`;

        // Append AI Message to UI
        appendChatMessage("ai", reply, data.action, data.target_url);

        // Speak aloud
        playVoiceAudio(reply, function () {
          if (data.action === "navigate" && data.target_url && data.target_url !== window.location.pathname) {
            setTimeout(function () {
              window.location.href = data.target_url;
            }, 1200);
          }
        });
      } else {
        appendChatMessage("ai", "I could not process your query right now. Please try again.");
        if (statusEl) statusEl.innerText = "Please try asking again.";
      }
    } catch (err) {
      console.error("AI Assistant request error:", err);
      appendChatMessage("ai", "Network error. Please check your internet connection.");
      if (statusEl) statusEl.innerText = "Tap microphone to try again.";
    }
  }

  function appendChatMessage(sender, text, action, targetUrl) {
    const chatFeed = document.getElementById("ai-chat-feed");
    if (!chatFeed) return;

    const msgDiv = document.createElement("div");
    msgDiv.className = `d-flex gap-2 mb-3 ${sender === 'user' ? 'justify-content-end' : 'justify-content-start'}`;

    if (sender === "user") {
      msgDiv.innerHTML = `
        <div class="bg-primary text-white p-3 rounded-4 shadow-sm" style="max-width: 82%; font-size: 0.88rem; border-bottom-right-radius: 4px !important;">
          <div class="fw-semibold">${escapeHtml(text)}</div>
        </div>
      `;
    } else {
      let actionBtnHtml = "";
      if (targetUrl) {
        if (action === "call_108") {
          actionBtnHtml = `<a href="tel:108" class="btn btn-sm btn-danger rounded-pill mt-2 px-3 fs-8 fw-bold"><i class="bi bi-telephone-fill me-1"></i> Call 108 Helpline</a>`;
        } else {
          actionBtnHtml = `<a href="${targetUrl}" class="btn btn-sm btn-primary rounded-pill mt-2 px-3 fs-8 fw-bold"><i class="bi bi-arrow-right-circle-fill me-1"></i> Open Page (${targetUrl})</a>`;
        }
      }

      msgDiv.innerHTML = `
        <div class="p-2 bg-primary text-white rounded-circle d-flex align-items-center justify-content-center flex-shrink-0" style="width: 32px; height: 32px;">
          <i class="bi bi-stars fs-6"></i>
        </div>
        <div class="bg-light border p-3 rounded-4 shadow-sm text-dark" style="max-width: 85%; font-size: 0.88rem; border-top-left-radius: 4px !important;">
          <div class="d-flex align-items-center justify-content-between mb-1 pb-1 border-bottom border-light-subtle">
            <span class="fw-bold text-primary fs-9">PulseCare Mitra</span>
            <button type="button" class="btn btn-sm btn-link p-0 text-primary fs-9 text-decoration-none" onclick="window.PulseCareAIAssistant.replay('${escapeHtml(text).replace(/'/g, "\\'")}')">
              <i class="bi bi-volume-up-fill me-1"></i>Listen Again
            </button>
          </div>
          <div class="lh-base">${escapeHtml(text)}</div>
          ${actionBtnHtml}
        </div>
      `;
    }

    chatFeed.appendChild(msgDiv);
    chatFeed.scrollTop = chatFeed.scrollHeight;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
  }

  function renderQuickChips() {
    const chipContainer = document.getElementById("ai-chips-container");
    if (!chipContainer) return;
    const langKey = getActiveLang();
    const chips = QUICK_PROMPTS[langKey] || QUICK_PROMPTS.en;

    chipContainer.innerHTML = chips.map(c => `
      <button type="button" class="ai-chip-btn" onclick="window.PulseCareAIAssistant.ask('${c.text.replace(/'/g, "\\'")}')">
        ${c.label}
      </button>
    `).join("");
  }

  function openAIModal(initialQuery) {
    if (!document.getElementById("pulseAIVoiceModal")) {
      injectAIModal();
    }

    const modalEl = document.getElementById("pulseAIVoiceModal");
    if (modalEl && typeof bootstrap !== "undefined") {
      const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
      bsModal.show();
    }

    renderQuickChips();

    // If chat feed is empty, show welcome greeting
    const chatFeed = document.getElementById("ai-chat-feed");
    if (chatFeed && chatFeed.children.length === 0) {
      const langKey = getActiveLang();
      const greeting = (AI_LANGS[langKey] || AI_LANGS.en).greeting;
      appendChatMessage("ai", greeting);
    }

    if (initialQuery) {
      processUserQuery(initialQuery);
    } else {
      setTimeout(function () {
        startListening();
      }, 400);
    }
  }

  function injectAIModal() {
    if (document.getElementById("pulseAIVoiceModal")) return;
    const langKey = getActiveLang();
    const langConfig = AI_LANGS[langKey] || AI_LANGS.en;

    const modalDiv = document.createElement("div");
    modalDiv.innerHTML = `
      <div class="modal fade no-print" id="pulseAIVoiceModal" tabindex="-1" aria-labelledby="pulseAIVoiceModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered modal-lg">
          <div class="modal-content rounded-4 border-0 shadow-lg overflow-hidden">
            
            <!-- Modal Header -->
            <div class="modal-header bg-dark text-white py-3 px-4 d-flex align-items-center justify-content-between border-0" style="background: linear-gradient(135deg, #091322 0%, #0f243d 50%, #0369a1 100%) !important;">
              <div class="d-flex align-items-center gap-3">
                <div class="p-2 bg-white bg-opacity-15 text-white rounded-3 border border-white border-opacity-20 d-flex align-items-center justify-content-center" style="width: 40px; height: 40px;">
                  <i class="bi bi-robot fs-4 text-info"></i>
                </div>
                <div>
                  <h5 class="modal-title fw-bold text-white fs-6 mb-0" id="pulseAIVoiceModalLabel">PulseCare Mitra — Real-Time Conversational Voice AI</h5>
                  <small class="text-white-50 fs-9">Multilingual Healthcare Navigator & Clinical Assistant</small>
                </div>
              </div>
              <button type="button" class="btn-close btn-close-white fs-8" data-bs-dismiss="modal" onclick="window.PulseCareAIAssistant.stop()"></button>
            </div>

            <!-- Modal Body -->
            <div class="modal-body p-3 p-md-4 bg-white d-flex flex-column" style="min-height: 480px; max-height: 75vh;">
              
              <!-- Top Voice Orb & Visualizer Area -->
              <div class="p-3 bg-light rounded-4 border mb-3 text-center">
                
                <!-- Glowing Mic Ring -->
                <div class="ai-voice-listening-ring mb-2" id="ai-mic-ring" onclick="window.PulseCareAIAssistant.toggleListening()" style="cursor: pointer;" title="Tap to Speak / Stop">
                  <div class="ai-voice-orb-btn">
                    <i class="bi bi-mic-fill fs-3"></i>
                  </div>
                </div>

                <!-- Animated Waveform Bars -->
                <div class="ai-waveform-bars mb-2 d-none" id="ai-modal-wave">
                  <span></span><span></span><span></span><span></span><span></span><span></span>
                </div>

                <!-- Status indicator -->
                <div class="fs-8 fw-semibold text-dark" id="ai-modal-status">
                  <span class="text-primary"><i class="bi bi-soundwave me-1"></i>Tap the microphone to speak</span>
                </div>

                <!-- Live interim speech transcript -->
                <div class="text-muted fs-8 fst-italic mt-1 d-none" id="ai-live-transcript"></div>
              </div>

              <!-- Conversation Chat Feed -->
              <div class="flex-grow-1 overflow-y-auto px-1 mb-3" id="ai-chat-feed" style="max-height: 240px;"></div>

              <!-- Quick Inquiry Suggestion Chips -->
              <div class="mb-2">
                <div class="text-muted fw-bold fs-9 text-uppercase mb-1"><i class="bi bi-lightning-fill text-warning me-1"></i>Quick Healthcare Questions:</div>
                <div class="d-flex flex-wrap gap-1" id="ai-chips-container"></div>
              </div>

              <!-- Text Question Input Bar -->
              <div class="mt-auto pt-2 border-top">
                <form onsubmit="event.preventDefault(); const inp = document.getElementById('ai-text-input'); if(inp && inp.value){ window.PulseCareAIAssistant.ask(inp.value); inp.value=''; }" class="d-flex gap-2">
                  <input type="text" class="form-control rounded-pill fs-8 px-3" id="ai-text-input" placeholder="Or type your medical question or request here...">
                  <button type="submit" class="btn btn-primary rounded-pill px-4 fs-8 fw-bold d-flex align-items-center gap-1">
                    <i class="bi bi-send-fill"></i>
                    <span class="d-none d-sm-inline">Ask</span>
                  </button>
                </form>
              </div>

            </div>

            <!-- Modal Footer -->
            <div class="modal-footer bg-light py-2 px-4 border-top d-flex align-items-center justify-content-between fs-9 text-muted">
              <div><i class="bi bi-shield-check text-success me-1"></i>Free & Grounded in Live Hospital Data</div>
              <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill px-3 py-1 fs-8" data-bs-dismiss="modal" onclick="window.PulseCareAIAssistant.stop()">Close</button>
            </div>

          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modalDiv);
  }

  function injectFloatingFab() {
    if (document.getElementById("ai-assistant-fab")) return;

    const fab = document.createElement("div");
    fab.id = "ai-assistant-fab";
    fab.className = "no-print";
    fab.style.cssText = "position: fixed; bottom: 85px; right: 24px; z-index: 1050;";

    fab.innerHTML = `
      <button type="button" class="ai-voice-floating-btn shadow-lg d-flex align-items-center gap-2" onclick="window.PulseCareAIAssistant.openModal()" title="Ask PulseCare AI Voice Assistant">
        <div class="ai-fab-icon-box">
          <i class="bi bi-robot fs-5"></i>
        </div>
        <div class="ai-fab-label d-none d-sm-block">
          <span class="fw-bold fs-8">PulseCare AI</span>
          <span class="d-block text-white-50 fs-9">Real-Time Voice</span>
        </div>
      </button>
    `;
    document.body.appendChild(fab);
    injectAIModal();
  }

  window.PulseCareAIAssistant = {
    openModal: openAIModal,
    ask: processUserQuery,
    startListening: startListening,
    stopListening: stopListening,
    stop: function () {
      stopListening();
      stopAllSpeech();
    },
    toggleListening: function () {
      if (isListening) {
        stopListening();
      } else {
        startListening();
      }
    },
    replay: function (text) {
      playVoiceAudio(text);
    }
  };

  document.addEventListener("DOMContentLoaded", function () {
    injectFloatingFab();
  });

})();
