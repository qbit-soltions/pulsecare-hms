/**
 * PulseCare Speak Aloud & Voice Accessibility Engine v3.1
 * Purpose-built for illiterate, elderly, and rural patients in India.
 *
 * Fix for Dual-Audio / Double Playback:
 * 1. Single fallback guard prevents audio.onerror and audio.play().catch() from firing twice.
 * 2. readFullPage uses data-voice-region attribute ONLY (does NOT concatenate innerText).
 * 3. Dedicated handler ignores elements with explicit readPage calls.
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
    const opdBtn = document.getElementById("opd-speak-btn");
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
      if (opdBtn) {
        opdBtn.classList.add("btn-danger","pulse-animation");
        opdBtn.classList.remove("btn-outline-light");
        opdBtn.innerHTML = `<i class="bi bi-stop-circle-fill me-1"></i> ${lang.stop}`;
      }
    } else if (isPaused) {
      if (playBtn) playBtn.classList.remove("d-none");
      if (pauseBtn) pauseBtn.classList.add("d-none");
      if (stopBtn) stopBtn.classList.remove("d-none");
      if (waveEl) waveEl.classList.add("d-none");
      if (statusText) statusText.innerText = lang.pause;
      if (opdBtn) {
        opdBtn.classList.remove("btn-danger","pulse-animation");
        opdBtn.classList.add("btn-warning");
        opdBtn.innerHTML = `<i class="bi bi-play-circle-fill me-1"></i> ${lang.resume}`;
      }
    } else {
      if (playBtn) playBtn.classList.remove("d-none");
      if (pauseBtn) pauseBtn.classList.add("d-none");
      if (stopBtn) stopBtn.classList.add("d-none");
      if (waveEl) waveEl.classList.add("d-none");
      if (statusText) statusText.innerText = tapToSpeakActive ? lang.tapMode : lang.label;
      if (opdBtn) {
        opdBtn.classList.remove("btn-danger","btn-warning","pulse-animation");
        opdBtn.classList.add("btn-outline-light");
        opdBtn.innerHTML = `<i class="bi bi-volume-up-fill me-1"></i> Speak Queue`;
      }
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

  function speakSequence(items) {
    if (!items || !items.length) return;
    speechQueue = [...items];
    function playNext() {
      if (!speechQueue.length) {
        isSpeaking = false;
        clearHighlight();
        updateWidgetUI();
        return;
      }
      const item = speechQueue.shift();
      const text = typeof item === "string" ? item : (item.text || "");
      const el = typeof item === "object" ? (item.el || null) : null;
      if (!text || !text.trim()) {
        playNext();
        return;
      }
      speak(text, el, function() {
        setTimeout(playNext, 400);
      });
    }
    playNext();
  }

  /**
   * Reads only [data-voice-region] sections without duplicating innerText.
   */
  function readFullPage() {
    if (isSpeaking) {
      stopSpeaking();
      return;
    }

    const items = [];

    // 1. Look for explicitly marked voice regions
    const regions = document.querySelectorAll("[data-voice-region]");
    if (regions.length > 0) {
      regions.forEach(function(region) {
        const label = region.getAttribute("data-voice-region");
        if (label && label.trim().length > 0) {
          items.push({ el: region, text: label.trim() });
        } else {
          const text = region.innerText ? region.innerText.trim().replace(/[\n\r\t]+/g, " ").replace(/\s{2,}/g, " ") : "";
          if (text && text.length > 3) {
            items.push({ el: region, text: text });
          }
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
      items.push({ el: document.body, text: "Welcome to PulseCare Public Health Network." });
    }

    speakSequence(items);
  }

  function pauseSpeaking() {
    if (currentAudio && isSpeaking && !isPaused) {
      currentAudio.pause();
      isPaused = true;
      updateWidgetUI();
    }
  }

  function resumeSpeaking() {
    if (currentAudio && isPaused) {
      currentAudio.play();
      isPaused = false;
      updateWidgetUI();
    } else if (!isSpeaking) {
      readFullPage();
    }
  }

  function setSpeechRate(rate) {
    speechRate = parseFloat(rate) || 0.95;
    const lbl = document.getElementById("voice-speed-val");
    if (lbl) lbl.innerText = speechRate + "x";
    if (currentAudio) currentAudio.playbackRate = speechRate;
  }

  function toggleTapToSpeak() {
    tapToSpeakActive = !tapToSpeakActive;
    const tapBtn = document.getElementById("voice-btn-tapmode");
    const lang = VOICE_LANGS[getLangKey()] || VOICE_LANGS.en;
    if (tapToSpeakActive) {
      document.body.classList.add("tap-to-speak-active");
      if (tapBtn) {
        tapBtn.classList.add("btn-primary");
        tapBtn.classList.remove("btn-outline-secondary");
        tapBtn.innerHTML = `<i class="bi bi-hand-index-thumb-fill text-warning me-1"></i> ${lang.tapMode}`;
      }
      speak("Tap to Speak mode is active. Tap any card or text to hear it aloud.");
    } else {
      document.body.classList.remove("tap-to-speak-active");
      if (tapBtn) {
        tapBtn.classList.remove("btn-primary");
        tapBtn.classList.add("btn-outline-secondary");
        tapBtn.innerHTML = `<i class="bi bi-hand-index-thumb me-1"></i> ${lang.tapModeOff}`;
      }
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

  function isGlobalVoiceDisabled() {
    return localStorage.getItem("pulsecare_voice_disabled") === "true";
  }

  function toggleGlobalVoice() {
    const isDisabled = isGlobalVoiceDisabled();
    if (isDisabled) {
      localStorage.setItem("pulsecare_voice_disabled", "false");
      speak("Voice assistance enabled.");
    } else {
      stopSpeaking();
      localStorage.setItem("pulsecare_voice_disabled", "true");
    }
    updateWidgetUI();
  }

  function extractTextFromElement(target) {
    if (!target) return "";
    
    // Check for explicit data attributes
    const explicit = target.getAttribute("data-speak") || target.getAttribute("data-voice-region") || target.getAttribute("aria-label");
    if (explicit && explicit.trim()) return explicit.trim();

    // If input / textarea
    if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") {
      let labelText = "";
      if (target.id) {
        const lbl = document.querySelector(`label[for="${target.id}"]`);
        if (lbl) labelText = lbl.innerText.trim();
      }
      if (!labelText) {
        const parentLabel = target.closest("label");
        if (parentLabel) labelText = parentLabel.innerText.trim();
      }
      const placeholder = target.placeholder ? `Placeholder: ${target.placeholder}` : "";
      const val = target.value ? `Entered: ${target.value}` : "";
      return [labelText, placeholder, val].filter(Boolean).join(". ");
    }

    // If select dropdown
    if (target.tagName === "SELECT") {
      const selectedOption = target.options && target.options[target.selectedIndex] ? target.options[target.selectedIndex].text : "";
      let labelText = "";
      if (target.id) {
        const lbl = document.querySelector(`label[for="${target.id}"]`);
        if (lbl) labelText = lbl.innerText.trim();
      }
      return `${labelText ? labelText + ": " : ""}${selectedOption || target.name || "Dropdown option"}`;
    }

    // If image
    if (target.tagName === "IMG") {
      return target.alt || target.title || "Image";
    }

    // For cards, table rows, headings, paragraphs, buttons, links, etc.
    let text = target.innerText ? target.innerText.trim().replace(/[\n\r\t]+/g, " ").replace(/\s{2,}/g, " ") : "";
    
    if (!text || text.length < 2) {
      const container = target.closest("a, button, .card, p, h1, h2, h3, h4, h5, h6, li, tr, td, th, label, .badge, .alert");
      if (container && container.innerText) {
        text = container.innerText.trim().replace(/[\n\r\t]+/g, " ").replace(/\s{2,}/g, " ");
      }
    }

    return text || target.getAttribute("title") || "";
  }

  function handleDocumentTap(e) {
    if (isGlobalVoiceDisabled()) return;

    // Ignore clicks inside the voice widget or OPD TV speak button
    if (e.target.closest("#voice-assist-widget") || e.target.closest("#opd-speak-btn")) {
      return;
    }

    // 1. Dedicated speak button (elements explicitly designated with .btn-speak-text)
    const speakBtn = e.target.closest(".btn-speak-text");
    if (speakBtn) {
      e.preventDefault();
      e.stopPropagation();
      const text = speakBtn.getAttribute("data-speak") || extractTextFromElement(speakBtn);
      speak(text, speakBtn.closest("[data-voice-region], .card, tr, .alert, div") || speakBtn);
      return;
    }

    // 2. If Tap to Speak is OFF, do NOT intercept anything (normal clicks, links, and forms work 100% normally)
    if (!tapToSpeakActive) {
      return;
    }

    // 3. When Tap to Speak is ON: read aloud wherever the cursor is clicked!
    e.preventDefault();
    e.stopPropagation();

    const clickedEl = e.target.closest("a, button, input, select, textarea, .card, .persona-card, tr, td, th, .badge, .alert, label, h1, h2, h3, h4, h5, h6, p, li, dt, dd, .queue-card-tv, span, div") || e.target;
    
    const textToSpeak = extractTextFromElement(clickedEl);
    if (textToSpeak && textToSpeak.trim().length > 0) {
      speak(textToSpeak, clickedEl);
    }
  }

  // =========================================================================
  // REAL-TIME AI VOICE ASSISTANT (100% FREE SPEECH RECOGNITION + AI ENGINE)
  // =========================================================================

  let recognition = null;
  let isListening = false;
  let speechRecognitionSupported = ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window);

  const AI_QUICK_CHIPS = {
    hi: [
      { text: "खाली बेड की स्थिति क्या है?", label: "🛏️ उपलब्ध बेड" },
      { text: "ऑन-ड्यूटी डॉक्टर कौन हैं?", label: "👨‍⚕️ डॉक्टर सूची" },
      { text: "108 एम्बुलेंस सहायता", label: "🚑 इमरजेंसी 108" },
      { text: "फार्मेसी में दवाइयाँ", label: "💊 फार्मेसी" },
      { text: "नया ABHA कार्ड बनाएं", label: "🆔 ABHA कार्ड" }
    ],
    ta: [
      { text: "படுக்கை இருப்பு விவரம்?", label: "🛏️ காலியான படுக்கைகள்" },
      { text: "பணியில் உள்ள மருத்துவர்கள் யார்?", label: "👨‍⚕️ மருத்துவர்கள்" },
      { text: "108 அவசர ஆம்புலன்ஸ்", label: "🚑 அவசர உதவி 108" },
      { text: "மருந்தக இருப்பு", label: "💊 மருந்துகள்" },
      { text: "புதிய ABHA அட்டை", label: "🆔 ABHA அட்டை" }
    ],
    te: [
      { text: "ఖాళీ పడకల వివరాలు ఏమిటి?", label: "🛏️ అందుబాటులో ఉన్న పడకలు" },
      { text: "డ్యూటీలో ఉన్న వైద్యులు ఎవరు?", label: "👨‍⚕️ వైద్యుల జాబితా" },
      { text: "108 అత్యవసర అంబులెన్స్", label: "🚑 అత్యవసరం 108" },
      { text: "ఫార్మసీ మందులు", label: "💊 మందుల నిల్వ" }
    ],
    en: [
      { text: "What is the hospital bed occupancy?", label: "🛏️ Available Beds" },
      { text: "Who are the on-duty doctors today?", label: "👨‍⚕️ Doctors On-Duty" },
      { text: "Call 108 Emergency Ambulance", label: "🚑 Emergency 108" },
      { text: "Check pharmacy medicine catalog", label: "💊 Pharmacy Stock" },
      { text: "Register for National ABHA Card", label: "🆔 ABHA Registration" },
      { text: "View my Lab Reports", label: "🔬 Lab Reports" }
    ]
  };

  function initSpeechRecognition() {
    if (!speechRecognitionSupported) return null;
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    const rec = new SpeechRec();
    rec.continuous = false;
    rec.interimResults = true;
    rec.maxAlternatives = 1;
    return rec;
  }

  function startAIVoiceListening() {
    stopSpeaking();
    const langKey = getLangKey();
    const langConfig = VOICE_LANGS[langKey] || VOICE_LANGS.en;

    const micStatus = document.getElementById("ai-voice-status");
    const micOrb = document.getElementById("ai-voice-mic-orb");
    const userTranscript = document.getElementById("ai-voice-user-transcript");
    const waveEl = document.getElementById("ai-voice-wave");

    if (!speechRecognitionSupported) {
      if (micStatus) micStatus.innerText = "Voice input is not supported in this browser. Please type your query below.";
      return;
    }

    try {
      if (recognition) {
        recognition.abort();
      }
      recognition = initSpeechRecognition();
      if (!recognition) return;

      recognition.lang = langConfig.bcp47 || "en-IN";

      recognition.onstart = function() {
        isListening = true;
        if (micOrb) micOrb.classList.add("active");
        if (waveEl) waveEl.classList.remove("d-none");
        if (micStatus) micStatus.innerHTML = `<span class="text-primary fw-bold"><i class="bi bi-mic-fill me-1"></i>Listening in ${langConfig.name}...</span> (Speak now)`;
        if (userTranscript) userTranscript.innerText = "...";
      };

      recognition.onresult = function(event) {
        let interimTranscript = "";
        let finalTranscript = "";

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }

        const text = finalTranscript || interimTranscript;
        if (userTranscript && text) {
          userTranscript.innerText = `"${text}"`;
        }

        if (finalTranscript && finalTranscript.trim()) {
          sendAIVoiceQuery(finalTranscript.trim());
        }
      };

      recognition.onerror = function(event) {
        isListening = false;
        if (micOrb) micOrb.classList.remove("active");
        if (waveEl) waveEl.classList.add("d-none");
        if (micStatus) {
          if (event.error === "no-speech") {
            micStatus.innerText = "No speech detected. Tap microphone to speak again.";
          } else {
            micStatus.innerText = `Voice notice: ${event.error}. Please try again or type below.`;
          }
        }
      };

      recognition.onend = function() {
        isListening = false;
        if (micOrb) micOrb.classList.remove("active");
        if (waveEl) waveEl.classList.add("d-none");
      };

      recognition.start();
    } catch (e) {
      console.warn("Speech recognition start error:", e);
      if (micStatus) micStatus.innerText = "Tap microphone button to start listening.";
    }
  }

  function stopAIVoiceListening() {
    if (recognition && isListening) {
      recognition.stop();
    }
    isListening = false;
    const micOrb = document.getElementById("ai-voice-mic-orb");
    const waveEl = document.getElementById("ai-voice-wave");
    if (micOrb) micOrb.classList.remove("active");
    if (waveEl) waveEl.classList.add("d-none");
  }

  async function sendAIVoiceQuery(queryText) {
    if (!queryText || !queryText.trim()) return;
    stopAIVoiceListening();

    const langKey = getLangKey();
    const micStatus = document.getElementById("ai-voice-status");
    const aiResponseCard = document.getElementById("ai-voice-response-card");
    const aiResponseText = document.getElementById("ai-voice-response-text");
    const userTranscript = document.getElementById("ai-voice-user-transcript");
    const aiActionBtn = document.getElementById("ai-voice-action-btn");

    if (userTranscript) userTranscript.innerText = `"${queryText}"`;
    if (micStatus) micStatus.innerHTML = `<span class="spinner-border spinner-border-sm text-primary me-2"></span>PulseCare Mitra is thinking...`;
    if (aiResponseCard) aiResponseCard.classList.remove("d-none");
    if (aiResponseText) aiResponseText.innerHTML = `<span class="text-muted fst-italic">Fetching real-time healthcare response...</span>`;
    if (aiActionBtn) aiActionBtn.classList.add("d-none");

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
        const reply = data.reply || "Thank you. How else can I assist you?";
        if (aiResponseText) aiResponseText.innerText = reply;
        if (micStatus) micStatus.innerHTML = `<span class="text-success fw-bold"><i class="bi bi-check-circle-fill me-1"></i>Answered in ${VOICE_LANGS[langKey] ? VOICE_LANGS[langKey].name : 'English'}</span>`;

        // Speak response aloud via TTS!
        speak(reply, aiResponseCard, function() {
          if (data.action === "navigate" && data.target_url && data.target_url !== window.location.pathname) {
            setTimeout(function() {
              window.location.href = data.target_url;
            }, 1200);
          }
        });

        // Show action button if navigation or call is available
        if (data.target_url && aiActionBtn) {
          aiActionBtn.classList.remove("d-none");
          if (data.action === "call_108") {
            aiActionBtn.innerHTML = `<i class="bi bi-telephone-fill me-1"></i> Call 108 Helpline`;
            aiActionBtn.onclick = function() { window.location.href = "tel:108"; };
          } else {
            aiActionBtn.innerHTML = `<i class="bi bi-arrow-right-circle-fill me-1"></i> Open Page (${data.target_url})`;
            aiActionBtn.onclick = function() { window.location.href = data.target_url; };
          }
        }
      } else {
        if (aiResponseText) aiResponseText.innerText = "I could not process your query right now. Please try again.";
        if (micStatus) micStatus.innerText = "Please try asking again.";
      }
    } catch (err) {
      console.error("AI Voice Query error:", err);
      if (aiResponseText) aiResponseText.innerText = "Network connection issue. Please check your connection and try again.";
      if (micStatus) micStatus.innerText = "Tap microphone to try again.";
    }
  }

  function openAIVoiceModal(initialQuery) {
    const modalEl = document.getElementById("aiVoiceModal");
    if (!modalEl) {
      injectAIVoiceModal();
    }
    
    const targetModal = document.getElementById("aiVoiceModal");
    if (targetModal && typeof bootstrap !== "undefined") {
      const bsModal = bootstrap.Modal.getOrCreateInstance(targetModal);
      bsModal.show();
    }

    // Refresh quick chips for active language
    renderAIQuickChips();

    if (initialQuery) {
      sendAIVoiceQuery(initialQuery);
    } else {
      setTimeout(function() {
        startAIVoiceListening();
      }, 400);
    }
  }

  function renderAIQuickChips() {
    const chipContainer = document.getElementById("ai-voice-chips");
    if (!chipContainer) return;
    const langKey = getLangKey();
    const chips = AI_QUICK_CHIPS[langKey] || AI_QUICK_CHIPS.en;

    chipContainer.innerHTML = chips.map(c => `
      <button type="button" class="ai-chip-btn" onclick="window.PulseCareVoice.askAI('${c.text.replace(/'/g, "\\'")}')">
        ${c.label}
      </button>
    `).join("");
  }

  function injectAIVoiceModal() {
    if (document.getElementById("aiVoiceModal")) return;
    const langKey = getLangKey();
    const langConfig = VOICE_LANGS[langKey] || VOICE_LANGS.en;

    const modalDiv = document.createElement("div");
    modalDiv.innerHTML = `
      <div class="modal fade no-print" id="aiVoiceModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
          <div class="modal-content rounded-4 border-0 shadow-lg overflow-hidden">
            
            <!-- Modal Header -->
            <div class="modal-header bg-light border-bottom py-3 px-4 d-flex align-items-center justify-content-between">
              <div class="d-flex align-items-center gap-2">
                <div class="p-1 bg-primary text-white rounded-circle d-flex align-items-center justify-content-center" style="width: 32px; height: 32px;">
                  <i class="bi bi-robot fs-6"></i>
                </div>
                <div>
                  <h6 class="modal-title fw-bold text-dark fs-7 mb-0">PulseCare Mitra — Real-Time Voice AI</h6>
                  <small class="text-muted fs-9">100% Free Multilingual Healthcare Assistant</small>
                </div>
              </div>
              <button type="button" class="btn-close fs-8" data-bs-dismiss="modal" onclick="window.PulseCareVoice.stop()"></button>
            </div>

            <!-- Modal Body -->
            <div class="modal-body p-4 text-center">
              
              <!-- Listening Glowing Orb -->
              <div class="mb-3">
                <div class="ai-voice-listening-ring" id="ai-voice-mic-orb" onclick="window.PulseCareVoice.toggleListening()" style="cursor: pointer;" title="Tap to Listen/Stop">
                  <div class="ai-voice-orb-btn">
                    <i class="bi bi-mic-fill fs-3"></i>
                  </div>
                </div>
              </div>

              <!-- Animated Waveform -->
              <div class="ai-waveform-bars mb-2 d-none" id="ai-voice-wave">
                <span></span><span></span><span></span><span></span><span></span><span></span>
              </div>

              <!-- Status Text -->
              <div class="fs-8 mb-2" id="ai-voice-status">
                <span class="text-primary fw-semibold"><i class="bi bi-soundwave me-1"></i>Tap microphone to start speaking</span>
              </div>

              <!-- User Speech Transcript -->
              <div class="p-2 px-3 bg-light rounded-3 text-muted fs-8 mb-3 border min-vh-25" style="min-height: 44px; word-break: break-word;" id="ai-voice-user-transcript">
                "Speak in Hindi, Tamil, Telugu, English or ask for beds, doctors, emergency..."
              </div>

              <!-- AI Response Card -->
              <div class="p-3 bg-primary-subtle border border-primary-subtle rounded-4 text-start mb-3 d-none shadow-sm" id="ai-voice-response-card">
                <div class="d-flex align-items-center justify-content-between mb-1">
                  <span class="badge bg-primary text-white fs-9"><i class="bi bi-stars me-1"></i>PulseCare Mitra</span>
                  <button type="button" class="btn btn-sm btn-link p-0 text-primary fs-8 text-decoration-none" onclick="window.PulseCareVoice.replayResponse()" title="Replay Voice">
                    <i class="bi bi-volume-up-fill me-1"></i>Listen Again
                  </button>
                </div>
                <div class="fs-7 text-dark fw-medium lh-base" id="ai-voice-response-text">
                  Fetching response...
                </div>
                <button type="button" class="btn btn-sm btn-primary rounded-pill mt-2 px-3 fs-8 d-none" id="ai-voice-action-btn"></button>
              </div>

              <!-- Quick Suggestion Chips -->
              <div class="text-start mb-2">
                <div class="text-muted fw-bold fs-9 text-uppercase mb-1"><i class="bi bi-lightning-fill text-warning me-1"></i>Quick Inquiries:</div>
                <div class="d-flex flex-wrap gap-1" id="ai-voice-chips"></div>
              </div>

              <!-- Manual Text Input Option -->
              <div class="mt-3 pt-2 border-top">
                <form onsubmit="event.preventDefault(); const inp = document.getElementById('ai-voice-text-input'); if(inp && inp.value){ window.PulseCareVoice.askAI(inp.value); inp.value=''; }" class="d-flex gap-2">
                  <input type="text" class="form-control form-control-sm rounded-pill fs-8" id="ai-voice-text-input" placeholder="Or type your question here...">
                  <button type="submit" class="btn btn-sm btn-primary rounded-pill px-3 fs-8"><i class="bi bi-send-fill"></i></button>
                </form>
              </div>

            </div>

            <!-- Modal Footer -->
            <div class="modal-footer bg-light py-2 px-3 border-0 d-flex align-items-center justify-content-between fs-9 text-muted">
              <div><i class="bi bi-shield-check text-success me-1"></i>Private & Local Voice AI</div>
              <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill px-3 py-0 fs-8" data-bs-dismiss="modal">Close</button>
            </div>

          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modalDiv);
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
            <span class="badge bg-primary text-white py-1 px-2"><i class="bi bi-stars me-1"></i>Voice Hub</span>
            <span class="fs-8 fw-bold text-dark" id="voice-panel-lang">${lang.name}</span>
          </div>
          <button type="button" class="btn-close fs-9" onclick="window.PulseCareVoice.toggleExpand(event)"></button>
        </div>
        
        <!-- Primary AI Voice Assistant Button -->
        <div class="mb-3">
          <button type="button" class="btn btn-gradient-primary w-100 py-2 fw-bold text-white shadow-sm d-flex align-items-center justify-content-center gap-2 rounded-3" 
                  style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); font-size: 0.85rem;"
                  onclick="window.PulseCareVoice.openAIModal()">
            <i class="bi bi-robot fs-5"></i> <span>Ask PulseCare AI (Voice)</span>
          </button>
        </div>

        <div class="form-check form-switch mb-3 p-2 bg-light rounded-3 d-flex align-items-center justify-content-between border">
          <label class="form-check-label fw-bold fs-7 text-dark m-0 ps-1" for="globalVoiceToggle"><i class="bi bi-volume-up-fill me-1 text-primary"></i> Page Screen Reader</label>
          <input class="form-check-input m-0" type="checkbox" role="switch" id="globalVoiceToggle" ${!isDisabled ? 'checked' : ''} onchange="window.PulseCareVoice.toggleGlobalVoice()">
        </div>

        <div id="voice-controls-section" class="${isDisabled ? 'opacity-50 pe-none' : ''}">
          <div class="d-grid gap-2 mb-3">
            <button type="button" class="btn btn-outline-primary btn-sm fw-bold d-flex align-items-center justify-content-center gap-2" id="voice-btn-play" onclick="window.PulseCareVoice.readPage()">
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
    injectAIVoiceModal();
  }

  // Override updateWidgetUI to handle Global Disabled state
  const originalUpdateWidgetUI = updateWidgetUI;
  updateWidgetUI = function() {
    const isDisabled = isGlobalVoiceDisabled();
    const ctrlSection = document.getElementById("voice-controls-section");
    const iconBox = document.querySelector("#voice-mini-pill .voice-icon-box");
    const pillIcon = document.getElementById("voice-pill-icon");
    const statusText = document.getElementById("voice-status-text");
    
    if (isDisabled) {
      if (ctrlSection) { ctrlSection.classList.add("opacity-50", "pe-none"); }
      if (iconBox) { iconBox.classList.remove("bg-primary"); iconBox.classList.add("bg-secondary"); }
      if (pillIcon) { pillIcon.className = "bi bi-volume-mute-fill fs-5"; }
      if (statusText) { statusText.innerText = "Voice Off"; statusText.classList.remove("text-dark"); statusText.classList.add("text-muted"); }
      const gToggle = document.getElementById("globalVoiceToggle");
      if (gToggle) gToggle.checked = false;
    } else {
      if (ctrlSection) { ctrlSection.classList.remove("opacity-50", "pe-none"); }
      if (iconBox) { iconBox.classList.add("bg-primary"); iconBox.classList.remove("bg-secondary"); }
      if (pillIcon) { pillIcon.className = "bi bi-volume-up-fill fs-5"; }
      if (statusText) { statusText.classList.add("text-dark"); statusText.classList.remove("text-muted"); }
      const gToggle = document.getElementById("globalVoiceToggle");
      if (gToggle) gToggle.checked = true;
      originalUpdateWidgetUI();
    }
  };

  // Override speak and readFullPage to check global disable
  const originalSpeak = speak;
  speak = function(text, targetEl, onEndCallback) {
    if (isGlobalVoiceDisabled()) return;
    originalSpeak(text, targetEl, onEndCallback);
  };
  
  const originalReadFullPage = readFullPage;
  readFullPage = function() {
    if (isGlobalVoiceDisabled()) return;
    originalReadFullPage();
  };

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
    openAIModal: openAIVoiceModal,
    askAI: sendAIVoiceQuery,
    toggleListening: function() {
      if (isListening) {
        stopAIVoiceListening();
      } else {
        startAIVoiceListening();
      }
    },
    replayResponse: function() {
      const respEl = document.getElementById("ai-voice-response-text");
      if (respEl && respEl.innerText) {
        speak(respEl.innerText);
      }
    },
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

