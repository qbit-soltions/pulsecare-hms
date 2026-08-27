/**
 * PulseCare Speak Aloud & Voice Accessibility Engine v3.0
 * Purpose-built for illiterate, elderly, and rural patients in India.
 *
 * Key Fix: readFullPage() now reads ONLY regions marked with [data-voice-region]
 * so it never picks up the navbar, logo, or sidebar — only clinical content.
 *
 * How to mark a region for voice reading:
 *   <div data-voice-region="Patient Summary">...</div>
 *   <div data-voice-region="My Prescriptions">...</div>
 *
 * How to add a point-and-speak button:
 *   <button class="btn-speak-text" data-speak="Medicine: Paracetamol, 500mg, twice daily">
 *     <i class="bi bi-volume-up-fill"></i> Listen
 *   </button>
 */

(function () {
  'use strict';

  const VOICE_LANGS = {
    hi: { code:"hi", bcp47:"hi-IN", name:"हिंदी", label:"आवाज से सुनें", stop:"रोकें", pause:"विराम", resume:"जारी रखें", tapMode:"टैप करके सुनें (चालू)", tapModeOff:"टैप करके सुनें (बंद)", reading:"पढ़ रहे हैं...", speed:"गति" },
    ta: { code:"ta", bcp47:"ta-IN", name:"தமிழ்", label:"கேட்டு அறியவும்", stop:"நிறுத்து", pause:"இடைநிறுத்து", resume:"தொடரவும்", tapMode:"தொட்டு கேட்கும் முறை (ஆன்)", tapModeOff:"தொட்டு கேட்கும் முறை (ஆஃப்)", reading:"வாசிக்கிறது...", speed:"வேகம்" },
    te: { code:"te", bcp47:"te-IN", name:"తెలుగు", label:"వినండి", stop:"ఆపండి", pause:"విరామం", resume:"కొనసాగించండి", tapMode:"తాకి వినే మోడ్ (ఆన్)", tapModeOff:"తాకి వినే మోడ్ (ఆఫ్)", reading:"చదువుతోంది...", speed:"వేగం" },
    bn: { code:"bn", bcp47:"bn-IN", name:"বাংলা", label:"শুনে নিন", stop:"থামান", pause:"বিরতি", resume:"চালিয়ে যান", tapMode:"ট্যাপ করে শুনুন (চালু)", tapModeOff:"ট্যাপ করে শুনুন (বন্ধ)", reading:"পড়ছে...", speed:"গতি" },
    mr: { code:"mr", bcp47:"mr-IN", name:"मराठी", label:"ऐका", stop:"थांबवा", pause:"विराम", resume:"सुरू ठेवा", tapMode:"टॅप करून ऐका (सुरू)", tapModeOff:"टॅप करून ऐका (बंद)", reading:"वाचत आहे...", speed:"गती" },
    gu: { code:"gu", bcp47:"gu-IN", name:"ગુજરાતી", label:"સાંભળો", stop:"રોકો", pause:"વિરામ", resume:"ચાલુ રાખો", tapMode:"ટેપ કરીને સાંભળો (ચાલુ)", tapModeOff:"ટેપ કરીને સાંભળો (બંધ)", reading:"વાંચી રહ્યા છીએ...", speed:"ઝડપ" },
    en: { code:"en", bcp47:"en-IN", name:"English", label:"Speak Aloud", stop:"Stop", pause:"Pause", resume:"Resume", tapMode:"Tap to Speak (ON)", tapModeOff:"Tap to Speak (OFF)", reading:"Reading aloud...", speed:"Speed" }
  };

  let isSpeaking = false;
  let isPaused = false;
  let tapToSpeakActive = false;
  let currentAudio = null;
  let currentHighlightedEl = null;
  let speechQueue = [];
  let speechRate = 0.95;
  let activeLangOverride = null;

  function getLangKey() {
    if (activeLangOverride && VOICE_LANGS[activeLangOverride]) return activeLangOverride;
    const pMatch = document.cookie.match(/(?:^|;\s*)pulse_lang=([^;]+)/);
    if (pMatch && pMatch[1] && VOICE_LANGS[pMatch[1]]) return pMatch[1];
    const gMatch = document.cookie.match(/(?:^|;\s*)googtrans=\/en\/([^;]+)/);
    if (gMatch && gMatch[1] && VOICE_LANGS[gMatch[1]]) return gMatch[1];
    const stored = localStorage.getItem("pulsecare_lang");
    if (stored && VOICE_LANGS[stored]) return stored;
    return "en";
  }

  function highlightElement(el) {
    if (currentHighlightedEl) currentHighlightedEl.classList.remove("voice-reading-highlight");
    if (el && el.classList) {
      el.classList.add("voice-reading-highlight");
      currentHighlightedEl = el;
      el.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  function clearHighlight() {
    if (currentHighlightedEl) {
      currentHighlightedEl.classList.remove("voice-reading-highlight");
      currentHighlightedEl = null;
    }
  }

  function updateWidgetUI() {
    const lang = VOICE_LANGS[getLangKey()] || VOICE_LANGS.en;
    const playBtn = document.getElementById("voice-btn-play");
    const pauseBtn = document.getElementById("voice-btn-pause");
    const stopBtn = document.getElementById("voice-btn-stop");
    const statusText = document.getElementById("voice-status-text");
    const waveEl = document.getElementById("voice-wave-anim");
    const topSpeakerBtn = document.getElementById("topbar-speak-btn");
    const langLabel = document.getElementById("voice-lang-name");
    const playText = document.getElementById("voice-play-text");
    const tapText = document.getElementById("voice-tap-text");

    if (langLabel) langLabel.innerText = lang.name + " Audio";
    if (playText) playText.innerText = lang.label;
    if (tapText) tapText.innerText = tapToSpeakActive ? lang.tapMode : lang.tapModeOff;

    if (isSpeaking && !isPaused) {
      if (playBtn) playBtn.classList.add("d-none");
      if (pauseBtn) pauseBtn.classList.remove("d-none");
      if (stopBtn) stopBtn.classList.remove("d-none");
      if (waveEl) waveEl.classList.remove("d-none");
      if (statusText) statusText.innerText = lang.reading;
      if (topSpeakerBtn) {
        topSpeakerBtn.classList.add("btn-danger","pulse-animation");
        topSpeakerBtn.classList.remove("btn-outline-primary","btn-warning");
        topSpeakerBtn.innerHTML = `<i class="bi bi-stop-circle-fill"></i> <span class="d-none d-lg-inline">${lang.stop}</span>`;
      }
    } else if (isPaused) {
      if (playBtn) playBtn.classList.remove("d-none");
      if (pauseBtn) pauseBtn.classList.add("d-none");
      if (stopBtn) stopBtn.classList.remove("d-none");
      if (waveEl) waveEl.classList.add("d-none");
      if (statusText) statusText.innerText = lang.pause;
      if (topSpeakerBtn) {
        topSpeakerBtn.classList.remove("btn-danger","pulse-animation");
        topSpeakerBtn.classList.add("btn-warning");
        topSpeakerBtn.innerHTML = `<i class="bi bi-play-circle-fill"></i> <span class="d-none d-lg-inline">${lang.resume}</span>`;
      }
    } else {
      if (playBtn) playBtn.classList.remove("d-none");
      if (pauseBtn) pauseBtn.classList.add("d-none");
      if (stopBtn) stopBtn.classList.add("d-none");
      if (waveEl) waveEl.classList.add("d-none");
      if (statusText) statusText.innerText = tapToSpeakActive ? lang.tapMode : lang.label;
      if (topSpeakerBtn) {
        topSpeakerBtn.classList.remove("btn-danger","btn-warning","pulse-animation");
        topSpeakerBtn.classList.add("btn-outline-primary");
        topSpeakerBtn.innerHTML = `<i class="bi bi-volume-up-fill"></i> <span class="d-none d-lg-inline">${lang.label}</span>`;
      }
      clearHighlight();
    }
  }

  function stopSpeaking() {
    if (currentAudio) { currentAudio.pause(); currentAudio.currentTime = 0; currentAudio = null; }
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    speechQueue = [];
    isSpeaking = false;
    isPaused = false;
    clearHighlight();
    updateWidgetUI();
  }

  function speak(text, targetEl, onEndCallback) {
    stopSpeaking();
    if (!text || !text.trim()) return;
    const langKey = getLangKey();
    const langConfig = VOICE_LANGS[langKey] || VOICE_LANGS.en;
    const cleanText = text.replace(/[\n\r]+/g, " ").replace(/\s{2,}/g, " ").trim();
    const audioUrl = `/api/tts?lang=${encodeURIComponent(langConfig.code)}&q=${encodeURIComponent(cleanText.substring(0, 200))}`;
    const audio = new Audio(audioUrl);
    audio.playbackRate = speechRate;
    currentAudio = audio;

    audio.onplay = function() { isSpeaking = true; isPaused = false; highlightElement(targetEl); updateWidgetUI(); };
    audio.onended = function() { isSpeaking = false; isPaused = false; currentAudio = null; clearHighlight(); updateWidgetUI(); if (onEndCallback) onEndCallback(); };
    audio.onerror = function() {
      // Fallback to Web Speech API
      if (window.speechSynthesis) {
        const utter = new SpeechSynthesisUtterance(cleanText);
        utter.lang = langConfig.bcp47;
        utter.rate = speechRate;
        utter.onstart = function() { isSpeaking = true; isPaused = false; highlightElement(targetEl); updateWidgetUI(); };
        utter.onend = function() { isSpeaking = false; isPaused = false; clearHighlight(); updateWidgetUI(); if (onEndCallback) onEndCallback(); };
        utter.onerror = function() { isSpeaking = false; isPaused = false; clearHighlight(); updateWidgetUI(); };
        window.speechSynthesis.speak(utter);
      } else {
        isSpeaking = false; isPaused = false; clearHighlight(); updateWidgetUI();
      }
    };
    audio.play().catch(function() {
      if (window.speechSynthesis) {
        const utter = new SpeechSynthesisUtterance(cleanText);
        utter.lang = langConfig.bcp47;
        utter.rate = speechRate;
        window.speechSynthesis.speak(utter);
      }
    });
  }

  function speakSequence(items) {
    if (!items || !items.length) return;
    speechQueue = [...items];
    function playNext() {
      if (!speechQueue.length) { isSpeaking = false; clearHighlight(); updateWidgetUI(); return; }
      const item = speechQueue.shift();
      const text = typeof item === "string" ? item : (item.text || "");
      const el = typeof item === "object" ? (item.el || null) : null;
      if (!text || !text.trim()) { playNext(); return; }
      speak(text, el, function() { setTimeout(playNext, 350); });
    }
    playNext();
  }

  /**
   * CORE FIX: readFullPage now reads ONLY [data-voice-region] sections.
   * Falls back to page title + subtitle if no regions are marked.
   */
  function readFullPage() {
    if (isSpeaking) { stopSpeaking(); return; }

    const items = [];

    // 1. Look for explicitly marked voice regions
    const regions = document.querySelectorAll("[data-voice-region]");
    if (regions.length > 0) {
      regions.forEach(function(region) {
        const label = region.getAttribute("data-voice-region");
        const text = region.innerText ? region.innerText.trim().replace(/[\n\r\t]+/g, " ").replace(/\s{2,}/g, " ") : "";
        if (text && text.length > 3) {
          items.push({ el: region, text: (label ? label + ". " : "") + text + ". " });
        }
      });
    }

    // 2. Fallback: read page title + subtitle only
    if (!items.length) {
      const h = document.querySelector(".header-title, main h1, h1");
      const s = document.querySelector(".header-subtitle, main h2, main h4");
      if (h && h.innerText.trim()) items.push({ el: h, text: h.innerText.trim() + ". " });
      if (s && s.innerText.trim()) items.push({ el: s, text: s.innerText.trim() + ". " });
    }

    if (!items.length) {
      const lang = VOICE_LANGS[getLangKey()] || VOICE_LANGS.en;
      items.push({ el: document.body, text: "Welcome to PulseCare Public Health Network." });
    }

    speakSequence(items);
  }

  function pauseSpeaking() { if (currentAudio && isSpeaking && !isPaused) { currentAudio.pause(); isPaused = true; updateWidgetUI(); } }
  function resumeSpeaking() { if (currentAudio && isPaused) { currentAudio.play(); isPaused = false; updateWidgetUI(); } else if (!isSpeaking) { readFullPage(); } }
  function setSpeechRate(rate) { speechRate = parseFloat(rate) || 0.95; const lbl = document.getElementById("voice-speed-val"); if (lbl) lbl.innerText = speechRate + "x"; if (currentAudio) currentAudio.playbackRate = speechRate; }

  function toggleTapToSpeak() {
    tapToSpeakActive = !tapToSpeakActive;
    const tapBtn = document.getElementById("voice-btn-tapmode");
    const lang = VOICE_LANGS[getLangKey()] || VOICE_LANGS.en;
    if (tapToSpeakActive) {
      document.body.classList.add("tap-to-speak-active");
      if (tapBtn) { tapBtn.classList.add("btn-primary"); tapBtn.classList.remove("btn-outline-secondary"); tapBtn.innerHTML = `<i class="bi bi-hand-index-thumb-fill text-warning me-1"></i> ${lang.tapMode}`; }
      speak("Tap to Speak mode is active. Tap any card or text to hear it aloud.");
    } else {
      document.body.classList.remove("tap-to-speak-active");
      if (tapBtn) { tapBtn.classList.remove("btn-primary"); tapBtn.classList.add("btn-outline-secondary"); tapBtn.innerHTML = `<i class="bi bi-hand-index-thumb me-1"></i> ${lang.tapModeOff}`; }
      stopSpeaking();
    }
    updateWidgetUI();
  }

  function handleLanguageChanged(newLangCode) {
    if (!newLangCode || !VOICE_LANGS[newLangCode]) return;
    activeLangOverride = newLangCode;
    stopSpeaking();
    updateWidgetUI();
  }

  function handleDocumentTap(e) {
    if (e.target.closest("#voice-assist-widget") || e.target.closest("#topbar-speak-btn")) return;

    // Dedicated speak button
    const speakBtn = e.target.closest(".btn-speak-text, [data-speak]");
    if (speakBtn) {
      e.preventDefault();
      const text = speakBtn.getAttribute("data-speak") || speakBtn.innerText;
      speak(text, speakBtn.closest("[data-voice-region], .card, tr, .alert, div") || speakBtn);
      return;
    }

    if (!tapToSpeakActive) return;

    const target = e.target.closest("button, a, .card, .persona-card, tr, .badge, .alert, label, input, h1, h2, h3, h4, h5, h6, p, li, .queue-card-tv");
    if (target) {
      e.preventDefault();
      e.stopPropagation();
      let textToSpeak = "";
      if (target.tagName === "INPUT") {
        const lbl = document.querySelector(`label[for="${target.id}"]`);
        textToSpeak = (lbl ? lbl.innerText : "") + " " + (target.placeholder || "") + " " + (target.value || "");
      } else if (target.classList.contains("persona-card")) {
        const name = target.querySelector(".persona-name")?.innerText || "";
        const role = target.querySelector(".persona-role")?.innerText || "";
        textToSpeak = `${name}, ${role}`;
      } else {
        textToSpeak = target.innerText ? target.innerText.trim().replace(/[\n\r]+/g, " ") : (target.getAttribute("title") || "");
      }
      if (textToSpeak) speak(textToSpeak, target);
    }
  }

  function injectVoiceWidget() {
    if (document.getElementById("voice-assist-widget")) return;
    const lang = VOICE_LANGS[getLangKey()] || VOICE_LANGS.en;
    const widget = document.createElement("div");
    widget.id = "voice-assist-widget";
    widget.className = "voice-assist-container no-print";
    widget.innerHTML = `
      <div id="voice-mini-pill" class="voice-pill shadow-lg d-flex align-items-center gap-2" onclick="window.PulseCareVoice.toggleExpand(event)">
        <div class="voice-icon-box bg-primary text-white d-flex align-items-center justify-content-center rounded-circle">
          <i class="bi bi-volume-up-fill fs-5"></i>
        </div>
        <div class="voice-pill-info text-start d-none d-sm-block">
          <div class="fw-bold fs-8 text-dark" id="voice-status-text">${lang.label}</div>
          <div class="text-muted fs-9" id="voice-lang-name">${lang.name} Audio</div>
        </div>
        <div class="voice-equalizer d-none" id="voice-wave-anim">
          <span></span><span></span><span></span><span></span>
        </div>
        <button type="button" class="btn btn-sm btn-link text-secondary p-0 ms-1">
          <i class="bi bi-chevron-up fs-7" id="voice-expand-icon"></i>
        </button>
      </div>
      <div id="voice-expanded-panel" class="voice-panel shadow-lg rounded-4 p-3 bg-white border d-none">
        <div class="d-flex align-items-center justify-content-between pb-2 mb-2 border-bottom">
          <div class="d-flex align-items-center gap-2">
            <span class="badge bg-primary-subtle text-primary border border-primary-subtle py-1 px-2"><i class="bi bi-soundwave me-1"></i>Voice Assist</span>
            <span class="fs-8 fw-bold text-dark" id="voice-panel-lang">${lang.name}</span>
          </div>
          <button type="button" class="btn-close fs-9" onclick="window.PulseCareVoice.toggleExpand(event)"></button>
        </div>
        <p class="fs-8 text-muted mb-3">Listen to page content in your language. Tap any item to hear it.</p>
        <div class="d-grid gap-2 mb-3">
          <button type="button" class="btn btn-primary btn-sm fw-bold d-flex align-items-center justify-content-center gap-2" id="voice-btn-play" onclick="window.PulseCareVoice.readPage()">
            <i class="bi bi-play-fill fs-6"></i> <span id="voice-play-text">${lang.label}</span>
          </button>
          <button type="button" class="btn btn-warning btn-sm fw-bold d-flex align-items-center justify-content-center gap-2 d-none" id="voice-btn-pause" onclick="window.PulseCareVoice.pause()">
            <i class="bi bi-pause-fill fs-6"></i> <span>${lang.pause}</span>
          </button>
          <button type="button" class="btn btn-outline-danger btn-sm fw-bold d-flex align-items-center justify-content-center gap-2 d-none" id="voice-btn-stop" onclick="window.PulseCareVoice.stop()">
            <i class="bi bi-stop-fill fs-6"></i> <span>${lang.stop}</span>
          </button>
        </div>
        <div class="mb-3">
          <button type="button" class="btn btn-sm btn-outline-secondary w-100 d-flex align-items-center justify-content-center gap-2" id="voice-btn-tapmode" onclick="window.PulseCareVoice.toggleTapMode()">
            <i class="bi bi-hand-index-thumb me-1"></i> <span id="voice-tap-text">${lang.tapModeOff}</span>
          </button>
        </div>
        <div class="d-flex align-items-center justify-content-between bg-light p-2 rounded-3 fs-8">
          <span class="text-muted fw-semibold"><i class="bi bi-speedometer2 me-1"></i>${lang.speed}:</span>
          <div class="btn-group btn-group-sm">
            <button type="button" class="btn btn-outline-secondary py-0 px-2 fs-9" onclick="window.PulseCareVoice.setRate(0.8)">0.8x</button>
            <button type="button" class="btn btn-primary py-0 px-2 fs-9 fw-bold" id="voice-speed-val" onclick="window.PulseCareVoice.setRate(0.95)">1.0x</button>
            <button type="button" class="btn btn-outline-secondary py-0 px-2 fs-9" onclick="window.PulseCareVoice.setRate(1.2)">1.2x</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(widget);
  }

  window.PulseCareVoice = {
    readPage: readFullPage,
    pause: pauseSpeaking,
    resume: resumeSpeaking,
    stop: stopSpeaking,
    speakText: speak,
    setRate: setSpeechRate,
    toggleTapMode: toggleTapToSpeak,
    onLanguageChanged: handleLanguageChanged,
    toggleExpand: function(e) {
      if (e) e.stopPropagation();
      const panel = document.getElementById("voice-expanded-panel");
      const icon = document.getElementById("voice-expand-icon");
      if (panel) {
        const hidden = panel.classList.contains("d-none");
        panel.classList.toggle("d-none", !hidden);
        if (icon) icon.className = hidden ? "bi bi-chevron-down fs-7" : "bi bi-chevron-up fs-7";
      }
    }
  };

  document.addEventListener("DOMContentLoaded", function() {
    injectVoiceWidget();
    document.addEventListener("click", handleDocumentTap, true);
    updateWidgetUI();
  });

})();
