/**
 * PulseCare Speak Aloud & Voice Accessibility Engine v3.2
 * Purpose-built for illiterate, elderly, and rural patients in India.
 *
 * Dedicated Accessibility Screen Reader:
 * 1. Read Page Aloud (data-voice-region elements or main content)
 * 2. Tap-to-Speak mode for elderly & rural citizens
 * 3. Multi-speed playback (0.8x, 1.0x, 1.2x)
 * 4. Regional Indian languages (Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, English)
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
    const langLabel = document.getElementById("voice-lang-name");
    const playText = document.getElementById("voice-play-text");
    const tapText = document.getElementById("voice-tap-text");

    if (langLabel) langLabel.innerText = lang.name + " Reader";
    if (playText) playText.innerText = lang.label;
    if (tapText) tapText.innerText = tapToSpeakActive ? lang.tapMode : lang.tapModeOff;

    if (isSpeaking && !isPaused) {
      if (playBtn) playBtn.classList.add("d-none");
      if (pauseBtn) pauseBtn.classList.remove("d-none");
      if (stopBtn) stopBtn.classList.remove("d-none");
      if (waveEl) waveEl.classList.remove("d-none");
      if (statusText) statusText.innerText = lang.reading;
    } else if (isPaused) {
      if (playBtn) playBtn.classList.remove("d-none");
      if (pauseBtn) pauseBtn.classList.add("d-none");
      if (stopBtn) stopBtn.classList.remove("d-none");
      if (waveEl) waveEl.classList.add("d-none");
      if (statusText) statusText.innerText = lang.pause;
    } else {
      if (playBtn) playBtn.classList.remove("d-none");
      if (pauseBtn) pauseBtn.classList.add("d-none");
      if (stopBtn) stopBtn.classList.add("d-none");
      if (waveEl) waveEl.classList.add("d-none");
      if (statusText) statusText.innerText = tapToSpeakActive ? lang.tapMode : lang.label;
      clearHighlight();
    }
  }

  function stopSpeaking() {
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
      currentAudio = null;
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
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

    let fallbackHandled = false;
    function triggerFallback() {
      if (fallbackHandled) return;
      fallbackHandled = true;
      if (currentAudio === audio) currentAudio = null;

      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
        const utter = new SpeechSynthesisUtterance(cleanText);
        utter.lang = langConfig.bcp47;
        utter.rate = speechRate;
        utter.onstart = function() {
          isSpeaking = true;
          isPaused = false;
          highlightElement(targetEl);
          updateWidgetUI();
        };
        utter.onend = function() {
          isSpeaking = false;
          isPaused = false;
          clearHighlight();
          updateWidgetUI();
          if (onEndCallback) onEndCallback();
        };
        utter.onerror = function() {
          isSpeaking = false;
          isPaused = false;
          clearHighlight();
          updateWidgetUI();
          if (onEndCallback) onEndCallback();
        };
        window.speechSynthesis.speak(utter);
      } else {
        isSpeaking = false;
        isPaused = false;
        clearHighlight();
        updateWidgetUI();
        if (onEndCallback) onEndCallback();
      }
    }

    audio.onplay = function() {
      isSpeaking = true;
      isPaused = false;
      highlightElement(targetEl);
      updateWidgetUI();
    };

    audio.onended = function() {
      isSpeaking = false;
      isPaused = false;
      currentAudio = null;
      clearHighlight();
      updateWidgetUI();
      if (onEndCallback) onEndCallback();
    };

    audio.onerror = function() {
      triggerFallback();
    };

    audio.play().catch(function() {
      triggerFallback();
    });
  }

  function pauseSpeaking() {
    if (currentAudio && !currentAudio.paused) {
      currentAudio.pause();
      isPaused = true;
      isSpeaking = false;
      updateWidgetUI();
    } else if (window.speechSynthesis && window.speechSynthesis.speaking) {
      window.speechSynthesis.pause();
      isPaused = true;
      isSpeaking = false;
      updateWidgetUI();
    }
  }

  function resumeSpeaking() {
    if (currentAudio && isPaused) {
      currentAudio.play().then(function() {
        isPaused = false;
        isSpeaking = true;
        updateWidgetUI();
      });
    } else if (window.speechSynthesis && isPaused) {
      window.speechSynthesis.resume();
      isPaused = false;
      isSpeaking = true;
      updateWidgetUI();
    }
  }

  function setSpeechRate(rate) {
    speechRate = rate;
    const valEl = document.getElementById("voice-speed-val");
    if (valEl) valEl.innerText = rate + "x";
  }

  function toggleTapToSpeak() {
    tapToSpeakActive = !tapToSpeakActive;
    if (tapToSpeakActive) {
      document.body.classList.add("tap-to-speak-active");
      speak("Tap to speak mode enabled. Click anywhere to listen.");
    } else {
      document.body.classList.remove("tap-to-speak-active");
      stopSpeaking();
    }
    updateWidgetUI();
  }

  function handleLanguageChanged(newLang) {
    activeLangOverride = newLang;
    updateWidgetUI();
  }

  function isGlobalVoiceDisabled() {
    return localStorage.getItem("pulsecare_voice_disabled") === "true";
  }

  function toggleGlobalVoice() {
    const current = isGlobalVoiceDisabled();
    if (current) {
      localStorage.removeItem("pulsecare_voice_disabled");
    } else {
      localStorage.setItem("pulsecare_voice_disabled", "true");
      stopSpeaking();
    }
    updateWidgetUI();
  }

  function extractTextFromElement(el) {
    if (!el) return "";
    if (el.getAttribute("data-voice-text")) return el.getAttribute("data-voice-text").trim();
    if (el.getAttribute("aria-label")) return el.getAttribute("aria-label").trim();
    if (el.getAttribute("title")) return el.getAttribute("title").trim();
    if (el.getAttribute("placeholder")) return el.getAttribute("placeholder").trim();
    if (el.value && el.tagName === "INPUT" && el.type !== "password") return el.value.trim();
    return el.innerText ? el.innerText.trim().replace(/[\n\r\t]+/g, " ").replace(/\s{2,}/g, " ") : "";
  }

  function handleDocumentTap(e) {
    if (isGlobalVoiceDisabled()) return;
    if (e.target.closest("#voice-assist-widget") || e.target.closest("#ai-assistant-fab") || e.target.closest(".modal")) {
      return;
    }

    const speakBtn = e.target.closest(".btn-speak-text");
    if (speakBtn) {
      e.preventDefault();
      e.stopPropagation();
      const text = speakBtn.getAttribute("data-speak") || extractTextFromElement(speakBtn);
      speak(text, speakBtn.closest("[data-voice-region], .card, tr, .alert, div") || speakBtn);
      return;
    }

    if (!tapToSpeakActive) return;

    e.preventDefault();
    e.stopPropagation();
    const clickedEl = e.target.closest("a, button, input, select, textarea, .card, .persona-card, tr, td, th, .badge, .alert, label, h1, h2, h3, h4, h5, h6, p, li, dt, dd, span, div") || e.target;
    const textToSpeak = extractTextFromElement(clickedEl);
    if (textToSpeak && textToSpeak.trim().length > 0) {
      speak(textToSpeak, clickedEl);
    }
  }

  function readFullPage() {
    if (isSpeaking) {
      stopSpeaking();
      return;
    }

    const items = [];
    const regions = document.querySelectorAll("[data-voice-region]");
    if (regions.length > 0) {
      regions.forEach(function(region) {
        const label = region.getAttribute("data-voice-region");
        if (label && label.trim().length > 0) {
          items.push({ el: region, text: label.trim() });
        }
      });
    }

    if (!items.length) {
      const h = document.querySelector(".header-title, main h1, h1");
      const s = document.querySelector(".header-subtitle, main h2, main h4");
      if (h && h.innerText) items.push({ el: h, text: h.innerText.trim() });
      if (s && s.innerText) items.push({ el: s, text: s.innerText.trim() });
    }

    if (items.length > 0) {
      let idx = 0;
      function readNext() {
        if (idx >= items.length) {
          isSpeaking = false;
          clearHighlight();
          updateWidgetUI();
          return;
        }
        const curr = items[idx++];
        speak(curr.text, curr.el, function() {
          setTimeout(readNext, 300);
        });
      }
      readNext();
    }
  }

  function injectVoiceWidget() {
    if (document.getElementById("voice-assist-widget")) return;
    const lang = VOICE_LANGS[getLangKey()] || VOICE_LANGS.en;
    const isDisabled = isGlobalVoiceDisabled();
    const widget = document.createElement("div");
    widget.id = "voice-assist-widget";
    widget.className = "voice-assist-container no-print";
    
    widget.innerHTML = `
      <div id="voice-mini-pill" class="voice-pill shadow-lg d-flex align-items-center gap-2" onclick="window.PulseCareVoice.toggleExpand(event)">
        <div class="voice-icon-box ${isDisabled ? 'bg-secondary' : 'bg-primary'} text-white d-flex align-items-center justify-content-center rounded-circle">
          <i class="bi ${isDisabled ? 'bi-volume-mute-fill' : 'bi-volume-up-fill'} fs-5" id="voice-pill-icon"></i>
        </div>
        <div class="voice-pill-info text-start d-none d-sm-block">
          <div class="fw-bold fs-8 ${isDisabled ? 'text-muted' : 'text-dark'}" id="voice-status-text">${isDisabled ? 'Voice Off' : lang.label}</div>
          <div class="text-muted fs-9" id="voice-lang-name">${lang.name} Reader</div>
        </div>
        <div class="voice-equalizer d-none" id="voice-wave-anim">
          <span></span><span></span><span></span><span></span>
        </div>
        <button type="button" class="btn btn-sm btn-link text-secondary p-0 ms-1" aria-label="Expand Voice Controls">
          <i class="bi bi-chevron-up fs-7" id="voice-expand-icon"></i>
        </button>
      </div>

      <div id="voice-expanded-panel" class="voice-panel shadow-lg rounded-4 p-3 bg-white border d-none">
        <div class="d-flex align-items-center justify-content-between pb-2 mb-2 border-bottom">
          <div class="d-flex align-items-center gap-2">
            <span class="badge bg-primary-subtle text-primary border border-primary-subtle py-1 px-2"><i class="bi bi-volume-up-fill me-1"></i>Accessibility Reader</span>
            <span class="fs-8 fw-bold text-dark" id="voice-panel-lang">${lang.name}</span>
          </div>
          <button type="button" class="btn-close fs-9" onclick="window.PulseCareVoice.toggleExpand(event)"></button>
        </div>
        <p class="fs-8 text-muted mb-3">Screen reader for patients & elderly citizens. Tap any button or card to hear it aloud.</p>
        
        <div class="form-check form-switch mb-3 p-2 bg-light rounded-3 d-flex align-items-center justify-content-between border">
          <label class="form-check-label fw-bold fs-7 text-dark m-0 ps-1" for="globalVoiceToggle"><i class="bi bi-person-fill-up me-1 text-primary"></i> Enable Screen Reader</label>
          <input class="form-check-input m-0" type="checkbox" role="switch" id="globalVoiceToggle" ${!isDisabled ? 'checked' : ''} onchange="window.PulseCareVoice.toggleGlobalVoice()">
        </div>

        <div id="voice-controls-section" class="${isDisabled ? 'opacity-50 pe-none' : ''}">
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
          <div class="d-flex align-items-center justify-content-between bg-light p-2 rounded-3 fs-8 border">
            <span class="text-muted fw-semibold"><i class="bi bi-speedometer2 me-1"></i>${lang.speed}:</span>
            <div class="btn-group btn-group-sm">
              <button type="button" class="btn btn-outline-secondary py-0 px-2 fs-9" onclick="window.PulseCareVoice.setRate(0.8)">0.8x</button>
              <button type="button" class="btn btn-primary py-0 px-2 fs-9 fw-bold" id="voice-speed-val" onclick="window.PulseCareVoice.setRate(0.95)">1.0x</button>
              <button type="button" class="btn btn-outline-secondary py-0 px-2 fs-9" onclick="window.PulseCareVoice.setRate(1.2)">1.2x</button>
            </div>
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
    toggleGlobalVoice: toggleGlobalVoice,
    isGlobalVoiceDisabled: isGlobalVoiceDisabled,
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
    document.addEventListener("click", handleDocumentTap, false);
    updateWidgetUI();
  });

})();
