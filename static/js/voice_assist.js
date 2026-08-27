/**
 * PulseCare Speak Aloud & Voice Accessibility Engine
 * Designed for illiterate, elderly, and rural patients, ASHA workers, and caregivers.
 * 
 * Features:
 * 1. Automatic sync with active site language: Hindi (hi-IN), Tamil (ta-IN), Telugu (te-IN),
 *    Bengali (bn-IN), Marathi (mr-IN), Gujarati (gu-IN), English (en-IN).
 * 2. Real-time translation of speech text to match user's selected language.
 * 3. Read Page Aloud (Intelligent conversational audio tour of any screen in native language).
 * 4. Interactive "Tap to Speak / Point & Hear" mode for illiterate users.
 * 5. Dedicated "Listen to Prescription / Clinical Advice" speaker buttons.
 * 6. Visual synchronized highlighting of spoken elements with animated equalizer wave.
 * 7. Device voice matcher for Android, iOS, Windows, Mac, ChromeOS.
 */

(function () {
  'use strict';

  // Language mapping configuration
  const VOICE_LANGS = {
    hi: {
      bcp47: "hi-IN",
      name: "हिंदी",
      label: "आवाज से सुनें",
      stop: "रोकें",
      pause: "विराम",
      resume: "जारी रखें",
      tapMode: "टैप करके सुनें (चालू)",
      tapModeOff: "टैप करके सुनें (बंद)",
      reading: "पढ़ रहे हैं...",
      speed: "गति",
      welcome: "पल्सकेयर सार्वजनिक स्वास्थ्य नेटवर्क में आपका स्वागत है।",
      tapInstruction: "टैप टू स्पीक चालू है। किसी भी कार्ड, बटन या टेक्स्ट पर क्लिक करके उसकी आवाज सुनें।",
      stopped: "आवाज बंद कर दी गई है।",
      paused: "आवाज रोक दी गई है।",
      langSwitched: "हिंदी भाषा चुनी गई है। आवाज सहायता तैयार है।"
    },
    ta: {
      bcp47: "ta-IN",
      name: "தமிழ்",
      label: "கேட்டு அறியவும்",
      stop: "நிறுத்து",
      pause: "இடைநிறுத்து",
      resume: "தொடரவும்",
      tapMode: "தொட்டு கேட்கும் முறை (ஆன்)",
      tapModeOff: "தொட்டு கேட்கும் முறை (ஆஃப்)",
      reading: "வாசிக்கிறது...",
      speed: "வேகம்",
      welcome: "பல்ஸ்கேர் பொது சுகாதார வலைப்பின்னலுக்கு நல்வரவு.",
      tapInstruction: "தொட்டு கேட்கும் முறை ஆன் செய்யப்பட்டுள்ளது. எந்த பொத்தான் அல்லது தகவலையும் தொட்டு கேட்கலாம்.",
      stopped: "வாசிப்பு நிறுத்தப்பட்டது.",
      paused: "வாசிப்பு இடைநிறுத்தப்பட்டது.",
      langSwitched: "தமிழ் மொழி தேர்ந்தெடுக்கப்பட்டது. ஒலி உதவி தயார்."
    },
    te: {
      bcp47: "te-IN",
      name: "తెలుగు",
      label: "వినండి",
      stop: "ఆపండి",
      pause: "విరామం",
      resume: "కొనసాగించండి",
      tapMode: "తాకి వినే మోడ్ (ఆన్)",
      tapModeOff: "తాకి వినే మోడ్ (ఆఫ్)",
      reading: "చదువుతోంది...",
      speed: "వేగం",
      welcome: "పల్స్‌కేర్ ప్రజారోగ్య వ్యవస్థకు స్వాగతం.",
      tapInstruction: "తాకి వినే మోడ్ ఆన్ చేయబడింది. వివరాలు వినడానికి ఏదైనా బటన్ లేదా కార్డును తాకండి.",
      stopped: "ధ్వని ఆపబడింది.",
      paused: "ధ్వని నిలిపివేయబడింది.",
      langSwitched: "తెలుగు భాష ఎంపిక చేయబడింది. ధ్వని సహాయం సిద్ధంగా ఉంది."
    },
    bn: {
      bcp47: "bn-IN",
      name: "বাংলা",
      label: "শুনে নিন",
      stop: "থামান",
      pause: "বিরতি",
      resume: "চালিয়ে যান",
      tapMode: "ট্যাপ করে শুনুন (চালু)",
      tapModeOff: "ট্যাপ করে শুনুন (বন্ধ)",
      reading: "পড়ছে...",
      speed: "গতি",
      welcome: "পালসকেয়ার জনস্বাস্থ্য নেটওয়ার্কে আপনাকে স্বাগতম।",
      tapInstruction: "ট্যাপ করে শোনার মোড চালু হয়েছে। যেকোনো বোতাম বা কার্ডে ট্যাপ করে ভয়েস শুনুন।",
      stopped: "পড়া বন্ধ করা হয়েছে।",
      paused: "পড়া স্থগিত রাখা হয়েছে।",
      langSwitched: "বাংলা ভাষা নির্বাচন করা হয়েছে। ভয়েস সহায়তা প্রস্তুত।"
    },
    mr: {
      bcp47: "mr-IN",
      name: "मराठी",
      label: "ऐका",
      stop: "थांबवा",
      pause: "विराम",
      resume: "सुरू ठेवा",
      tapMode: "टॅप करून ऐका (सुरू)",
      tapModeOff: "टॅप करून ऐका (बंद)",
      reading: "वाचत आहे...",
      speed: "गती",
      welcome: "पल्सकेअर सार्वजनिक आरोग्य नेटवर्कमध्ये आपले स्वागत आहे.",
      tapInstruction: "टॅप करून ऐकण्याची सुविधा सुरू झाली आहे. माहिती ऐकण्यासाठी कोणत्याही घटकावर क्लिक करा.",
      stopped: "आवाज थांबवला आहे.",
      paused: "आवाज स्थगित केला आहे.",
      langSwitched: "मराठी भाषा निवडली आहे. व्हॉइस असिस्ट तयार आहे."
    },
    gu: {
      bcp47: "gu-IN",
      name: "ગુજરાતી",
      label: "સાંભળો",
      stop: "રોકો",
      pause: "વિરામ",
      resume: "ચાલુ રાખો",
      tapMode: "ટેપ કરીને સાંભળો (ચાલુ)",
      tapModeOff: "ટેપ કરીને સાંભળો (બંધ)",
      reading: "વાંચી રહ્યા છીએ...",
      speed: "ઝડપ",
      welcome: "પલ્સકેર જાહેર આરોગ્ય નેટવર્કમાં આપનું સ્વાગત છે.",
      tapInstruction: "ટેપ કરીને સાંભળવાનો મોડ ચાલુ છે. માહિતી સાંભળવા માટે કોઈપણ કાર્ડ અથવા બટન પર ક્લિક કરો.",
      stopped: "વાંચન બંધ કરવામાં આવ્યું છે.",
      paused: "વાંચન અટકાવવામાં આવ્યું છે.",
      langSwitched: "ગુજરાતી ભાષા પસંદ કરવામાં આવી છે. અવાજ સહાય તૈયાર છે."
    },
    en: {
      bcp47: "en-IN",
      name: "English",
      label: "Speak Aloud",
      stop: "Stop",
      pause: "Pause",
      resume: "Resume",
      tapMode: "Tap to Speak (ON)",
      tapModeOff: "Tap to Speak (OFF)",
      reading: "Reading aloud...",
      speed: "Speed",
      welcome: "Welcome to PulseCare Public Health Network.",
      tapInstruction: "Tap to Speak mode is active. Tap or click any card, badge, or button to hear it aloud.",
      stopped: "Speech stopped.",
      paused: "Speech paused.",
      langSwitched: "English language selected. Voice Assist is ready."
    }
  };

  // State
  let synth = window.speechSynthesis;
  let isSpeaking = false;
  let isPaused = false;
  let tapToSpeakActive = false;
  let currentUtterance = null;
  let currentHighlightedEl = null;
  let speechQueue = [];
  let speechRate = 0.88; // Slower, clearer cadence suited for rural patients
  let cachedVoices = [];
  let activeLangOverride = null;

  function loadVoices() {
    if (!synth) return;
    cachedVoices = synth.getVoices();
  }

  if (synth) {
    loadVoices();
    if (speechSynthesis.onvoiceschanged !== undefined) {
      speechSynthesis.onvoiceschanged = loadVoices;
    }
  }

  /**
   * Automatically resolves the current active site language
   */
  function getLangKey() {
    if (activeLangOverride && VOICE_LANGS[activeLangOverride]) {
      return activeLangOverride;
    }

    const pMatch = document.cookie.match(/(?:^|;\s*)pulse_lang=([^;]+)/);
    if (pMatch && pMatch[1] && VOICE_LANGS[pMatch[1]]) return pMatch[1];

    const gMatch = document.cookie.match(/(?:^|;\s*)googtrans=\/en\/([^;]+)/);
    if (gMatch && gMatch[1] && VOICE_LANGS[gMatch[1]]) return gMatch[1];

    const stored = localStorage.getItem("pulsecare_lang");
    if (stored && VOICE_LANGS[stored]) return stored;

    const htmlLang = document.documentElement.getAttribute("lang");
    if (htmlLang && VOICE_LANGS[htmlLang]) return htmlLang;

    return "en";
  }

  /**
   * Searches available system voices for the best match for Indian regional languages
   */
  function findBestVoice(bcp47) {
    if (!cachedVoices || cachedVoices.length === 0) loadVoices();
    const langPrefix = bcp47.split("-")[0].toLowerCase();

    // 1. Exact match (e.g. hi-IN or hi_IN)
    let match = cachedVoices.find(v => v.lang && (v.lang.toLowerCase() === bcp47.toLowerCase() || v.lang.toLowerCase().replace('_', '-') === bcp47.toLowerCase()));
    if (match) return match;

    // 2. Prefix match (e.g. hi, ta, te, bn, mr, gu)
    match = cachedVoices.find(v => v.lang && v.lang.toLowerCase().startsWith(langPrefix));
    if (match) return match;

    // 3. Match voice names containing language keywords across Android, Windows, Mac, and Chrome
    const voiceKeywords = {
      hi: ["hindi", "देवनागरी", "kalpana", "hemant", "lekha", "sangeeta"],
      ta: ["tamil", "தமிழ்", "valluvar", "kavya"],
      te: ["telugu", "తెలుగు", "chitra", "mohan"],
      bn: ["bengali", "বাংলা", "bangla", "bashkar", "tanisha"],
      mr: ["marathi", "मराठी", "aarohi"],
      gu: ["gujarati", "ગુજરાતી", "dhwani", "niranjan"],
      en: ["india", "en-in", "heera", "ravi", "veena", "neerja", "prabhat"]
    };
    const keywords = voiceKeywords[langPrefix] || [];
    match = cachedVoices.find(v => {
      const name = (v.name || "").toLowerCase();
      return keywords.some(k => name.includes(k.toLowerCase()));
    });
    if (match) return match;

    // 4. Indian English fallback (sounds natural for Indian numbers/medical terms)
    match = cachedVoices.find(v => v.lang && (v.lang.toLowerCase().includes("en-in") || v.name.toLowerCase().includes("india")));
    if (match) return match;

    // 5. Default device voice
    return cachedVoices.find(v => v.default) || cachedVoices[0] || null;
  }

  /**
   * Translates text into the target language using the UI Dictionary before speech
   */
  function translateForSpeech(text, langKey) {
    if (!text || langKey === "en") return text;
    const dict = (window.PulseCareUIDictionary && window.PulseCareUIDictionary[langKey]) || {};

    let translated = text.trim();

    // Direct match
    if (dict[translated]) {
      return dict[translated];
    }

    // Replace known dictionary terms inside the sentence
    Object.keys(dict).forEach(function (enKey) {
      if (enKey.length > 2 && translated.includes(enKey)) {
        const reg = new RegExp(enKey, "gi");
        translated = translated.replace(reg, dict[enKey]);
      }
    });

    return translated;
  }

  function highlightElement(el) {
    if (currentHighlightedEl) {
      currentHighlightedEl.classList.remove("voice-reading-highlight");
    }
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
    const playBtn = document.getElementById("voice-btn-play");
    const pauseBtn = document.getElementById("voice-btn-pause");
    const stopBtn = document.getElementById("voice-btn-stop");
    const statusText = document.getElementById("voice-status-text");
    const waveEl = document.getElementById("voice-wave-anim");
    const topSpeakerBtn = document.getElementById("topbar-speak-btn");
    const langKey = getLangKey();
    const lang = VOICE_LANGS[langKey] || VOICE_LANGS.en;

    if (isSpeaking && !isPaused) {
      if (playBtn) playBtn.classList.add("d-none");
      if (pauseBtn) pauseBtn.classList.remove("d-none");
      if (stopBtn) stopBtn.classList.remove("d-none");
      if (waveEl) waveEl.classList.remove("d-none");
      if (statusText) statusText.innerText = lang.reading;
      if (topSpeakerBtn) {
        topSpeakerBtn.classList.add("btn-danger", "pulse-animation");
        topSpeakerBtn.classList.remove("btn-outline-primary", "btn-warning");
        topSpeakerBtn.innerHTML = `<i class="bi bi-stop-circle-fill"></i> <span class="d-none d-lg-inline">${lang.stop}</span>`;
      }
    } else if (isPaused) {
      if (playBtn) playBtn.classList.remove("d-none");
      if (pauseBtn) pauseBtn.classList.add("d-none");
      if (stopBtn) stopBtn.classList.remove("d-none");
      if (waveEl) waveEl.classList.add("d-none");
      if (statusText) statusText.innerText = lang.paused;
      if (topSpeakerBtn) {
        topSpeakerBtn.classList.remove("btn-danger", "pulse-animation");
        topSpeakerBtn.classList.add("btn-warning");
        topSpeakerBtn.innerHTML = `<i class="bi bi-play-circle-fill"></i> <span class="d-none d-lg-inline">${lang.resume}</span>`;
      }
    } else {
      if (playBtn) playBtn.classList.remove("d-none");
      if (pauseBtn) pauseBtn.classList.add("d-none");
      if (stopBtn) stopBtn.classList.add("d-none");
      if (waveEl) waveEl.classList.add("d-none");
      if (statusText) {
        statusText.innerText = tapToSpeakActive ? lang.tapMode : lang.label;
      }
      if (topSpeakerBtn) {
        topSpeakerBtn.classList.remove("btn-danger", "btn-warning", "pulse-animation");
        topSpeakerBtn.classList.add("btn-outline-primary");
        topSpeakerBtn.innerHTML = `<i class="bi bi-volume-up-fill"></i> <span class="d-none d-lg-inline">${lang.label}</span>`;
      }
      clearHighlight();
    }
  }

  /**
   * Speak a text string in the currently selected language
   */
  function speak(text, targetEl = null, onEndCallback = null) {
    if (!synth) {
      alert("Text-to-Speech is not supported in this browser. Please use Chrome, Edge, or Firefox.");
      return;
    }

    synth.cancel();
    if (!text || !text.trim()) return;

    const langKey = getLangKey();
    const langConfig = VOICE_LANGS[langKey] || VOICE_LANGS.en;
    
    // Translate text into selected language if needed
    const translatedText = translateForSpeech(text, langKey);
    const cleanText = translatedText.replace(/[\n\r]+/g, " ").replace(/\s{2,}/g, " ").trim();

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = langConfig.bcp47;
    utterance.rate = speechRate;
    utterance.pitch = 1.0;

    const bestVoice = findBestVoice(langConfig.bcp47);
    if (bestVoice) {
      utterance.voice = bestVoice;
    }

    utterance.onstart = function () {
      isSpeaking = true;
      isPaused = false;
      highlightElement(targetEl);
      updateWidgetUI();
    };

    utterance.onend = function () {
      isSpeaking = false;
      isPaused = false;
      clearHighlight();
      updateWidgetUI();
      if (onEndCallback) onEndCallback();
    };

    utterance.onerror = function (e) {
      console.warn("Speech synthesis notice:", e);
      isSpeaking = false;
      isPaused = false;
      clearHighlight();
      updateWidgetUI();
    };

    currentUtterance = utterance;
    synth.speak(utterance);
  }

  /**
   * Speak an array of elements or text segments sequentially
   */
  function speakSequence(items) {
    if (!items || items.length === 0) return;
    speechQueue = [...items];

    function playNext() {
      if (speechQueue.length === 0) {
        isSpeaking = false;
        clearHighlight();
        updateWidgetUI();
        return;
      }

      const nextItem = speechQueue.shift();
      const text = typeof nextItem === "string" ? nextItem : (nextItem.text || nextItem.innerText || "");
      const el = typeof nextItem === "object" ? (nextItem.el || nextItem) : null;

      if (!text || !text.trim()) {
        playNext();
        return;
      }

      speak(text, el, function () {
        setTimeout(playNext, 250);
      });
    }

    playNext();
  }

  /**
   * Reads the entire page content aloud intelligently in sequence in the chosen language.
   */
  function readFullPage() {
    if (isSpeaking) {
      stopSpeaking();
      return;
    }

    const langKey = getLangKey();
    const langConfig = VOICE_LANGS[langKey] || VOICE_LANGS.en;
    const itemsToRead = [];

    // 1. Page Header & Subtitle
    const titleEl = document.querySelector(".header-title, h1, .brand-title");
    const subTitleEl = document.querySelector(".header-subtitle, .brand-subtitle");
    if (titleEl && titleEl.innerText.trim()) {
      itemsToRead.push({ el: titleEl, text: `${titleEl.innerText.trim()}. ` });
    }
    if (subTitleEl && subTitleEl.innerText.trim()) {
      itemsToRead.push({ el: subTitleEl, text: `${subTitleEl.innerText.trim()}. ` });
    }

    // 2. Active Facility & User Role if present
    const facilityEl = document.querySelector(".topbar, .demo-role-bar, .persona-facility");
    if (facilityEl && facilityEl.innerText.trim()) {
      const facText = facilityEl.innerText.trim().replace(/\n+/g, " ");
      itemsToRead.push({ el: facilityEl, text: `${facText}. ` });
    }

    // 3. Stat Cards / Dashboard Metrics
    const metricCards = document.querySelectorAll(".card, .stat-card, .metric-box, .alert");
    metricCards.forEach(function (card) {
      if (card.closest(".sidebar") || card.closest("#voice-assist-widget")) return;
      const text = card.innerText ? card.innerText.trim().replace(/[\n\r]+/g, " - ") : "";
      if (text && text.length > 5 && text.length < 300) {
        itemsToRead.push({ el: card, text: `${text}. ` });
      }
    });

    // 4. Clinical tables / Appointment rows / Prescription rows
    const tableRows = document.querySelectorAll("tbody tr");
    tableRows.forEach(function (row) {
      const text = row.innerText ? row.innerText.trim().replace(/\t+/g, " ").replace(/[\n\r]+/g, ", ") : "";
      if (text && text.length > 5 && text.length < 400) {
        itemsToRead.push({ el: row, text: `${text}. ` });
      }
    });

    // Fallback if no structured cards found
    if (itemsToRead.length <= 1) {
      const generalNodes = document.querySelectorAll(".main-content p, .main-content h2, .main-content h3, .main-content h4, .auth-card p, .auth-card h4");
      generalNodes.forEach(function (node) {
        const t = node.innerText ? node.innerText.trim() : "";
        if (t && t.length > 3) {
          itemsToRead.push({ el: node, text: `${t}. ` });
        }
      });
    }

    if (itemsToRead.length === 0) {
      itemsToRead.push({ el: document.body, text: langConfig.welcome });
    }

    speakSequence(itemsToRead);
  }

  function pauseSpeaking() {
    if (synth && isSpeaking && !isPaused) {
      synth.pause();
      isPaused = true;
      updateWidgetUI();
    }
  }

  function resumeSpeaking() {
    if (synth && isPaused) {
      synth.resume();
      isPaused = false;
      updateWidgetUI();
    } else if (!isSpeaking) {
      readFullPage();
    }
  }

  function stopSpeaking() {
    if (synth) {
      synth.cancel();
    }
    speechQueue = [];
    isSpeaking = false;
    isPaused = false;
    clearHighlight();
    updateWidgetUI();
  }

  function setSpeechRate(rate) {
    speechRate = parseFloat(rate) || 0.88;
    const rateLabel = document.getElementById("voice-speed-val");
    if (rateLabel) rateLabel.innerText = `${speechRate}x`;
    if (isSpeaking && !isPaused) {
      const curText = currentUtterance ? currentUtterance.text : "";
      const curEl = currentHighlightedEl;
      speak(curText, curEl);
    }
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
      speak(lang.tapInstruction);
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

  /**
   * Triggered whenever user switches language via the dropdown
   */
  function handleLanguageChanged(newLangCode) {
    if (!newLangCode || !VOICE_LANGS[newLangCode]) return;
    activeLangOverride = newLangCode;
    stopSpeaking();
    updateWidgetUI();
  }

  /**
   * Handle global click events in Tap to Speak mode
   */
  function handleDocumentTap(e) {
    // Ignore clicks on voice assist widget itself
    if (e.target.closest("#voice-assist-widget") || e.target.closest("#topbar-speak-btn")) {
      return;
    }

    // Direct speaker button click
    const speakBtn = e.target.closest(".btn-speak-text, [data-speak]");
    if (speakBtn) {
      e.preventDefault();
      const speakText = speakBtn.getAttribute("data-speak") || speakBtn.parentElement.innerText;
      speak(speakText, speakBtn.closest(".card, tr, div, li") || speakBtn);
      return;
    }

    if (!tapToSpeakActive) return;

    // Find closest meaningful element
    const target = e.target.closest(
      "button, a, .card, .persona-card, tr, .badge, .alert, label, input, select, textarea, h1, h2, h3, h4, h5, h6, p, li"
    );

    if (target) {
      e.preventDefault();
      e.stopPropagation();

      let textToSpeak = "";

      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") {
        const lbl = document.querySelector(`label[for="${target.id}"]`) || target.closest(".mb-3")?.querySelector("label");
        const placeholder = target.placeholder || "";
        const val = target.value || "";
        textToSpeak = `${lbl ? lbl.innerText : ''} ${placeholder ? 'Placeholder: ' + placeholder : ''} ${val ? 'Value: ' + val : ''}`;
      } else if (target.tagName === "SELECT") {
        const lbl = target.closest(".mb-3")?.querySelector("label");
        const opt = target.options[target.selectedIndex]?.text || "";
        textToSpeak = `${lbl ? lbl.innerText : 'Select menu'}. Selected: ${opt}`;
      } else if (target.classList.contains("persona-card")) {
        const name = target.querySelector(".persona-name")?.innerText || "";
        const role = target.querySelector(".persona-role")?.innerText || "";
        const fac = target.querySelector(".persona-facility")?.innerText || "";
        textToSpeak = `Sign in as ${name}, ${role}, at ${fac}. Click to login.`;
      } else {
        textToSpeak = target.innerText ? target.innerText.trim().replace(/[\n\r]+/g, " ") : target.getAttribute("title") || "";
      }

      if (textToSpeak) {
        speak(textToSpeak, target);
      }
    }
  }

  /**
   * Inject the floating voice widget into the DOM
   */
  function injectVoiceWidget() {
    if (document.getElementById("voice-assist-widget")) return;

    const langKey = getLangKey();
    const lang = VOICE_LANGS[langKey] || VOICE_LANGS.en;

    const widget = document.createElement("div");
    widget.id = "voice-assist-widget";
    widget.className = "voice-assist-container no-print";
    widget.innerHTML = `
      <!-- Minimized Audio Float Pill -->
      <div id="voice-mini-pill" class="voice-pill shadow-lg d-flex align-items-center gap-2" onclick="window.PulseCareVoice.toggleExpand(event)">
        <div class="voice-icon-box bg-primary text-white d-flex align-items-center justify-content-center rounded-circle">
          <i class="bi bi-volume-up-fill fs-5"></i>
        </div>
        <div class="voice-pill-info text-start d-none d-sm-block">
          <div class="fw-bold fs-8 text-dark" id="voice-status-text">${lang.label}</div>
          <div class="text-muted fs-9" id="voice-lang-name">${lang.name} Audio</div>
        </div>
        <!-- Animated Equalizer Waveform -->
        <div class="voice-equalizer d-none" id="voice-wave-anim">
          <span></span><span></span><span></span><span></span>
        </div>
        <button type="button" class="btn btn-sm btn-link text-secondary p-0 ms-1" title="Settings">
          <i class="bi bi-chevron-up fs-7" id="voice-expand-icon"></i>
        </button>
      </div>

      <!-- Expanded Control Drawer -->
      <div id="voice-expanded-panel" class="voice-panel shadow-lg rounded-4 p-3 bg-white border d-none">
        <div class="d-flex align-items-center justify-content-between pb-2 mb-2 border-bottom">
          <div class="d-flex align-items-center gap-2">
            <span class="badge bg-primary-subtle text-primary border border-primary-subtle py-1 px-2">
              <i class="bi bi-soundwave me-1"></i>Voice Assist
            </span>
            <span class="fs-8 fw-bold text-dark" id="voice-panel-lang">${lang.name}</span>
          </div>
          <button type="button" class="btn-close fs-9" onclick="window.PulseCareVoice.toggleExpand(event)"></button>
        </div>

        <p class="fs-8 text-muted mb-3">
          Listen to page contents, clinical prescriptions, and OPD token updates in your language.
        </p>

        <!-- Primary Action Buttons -->
        <div class="d-grid gap-2 mb-3">
          <button type="button" class="btn btn-primary btn-sm fw-bold d-flex align-items-center justify-content-center gap-2 shadow-sm" id="voice-btn-play" onclick="window.PulseCareVoice.readPage()">
            <i class="bi bi-play-fill fs-6"></i> <span id="voice-play-text">${lang.label}</span>
          </button>
          <button type="button" class="btn btn-warning btn-sm fw-bold d-flex align-items-center justify-content-center gap-2 d-none shadow-sm" id="voice-btn-pause" onclick="window.PulseCareVoice.pause()">
            <i class="bi bi-pause-fill fs-6"></i> <span>${lang.pause}</span>
          </button>
          <button type="button" class="btn btn-outline-danger btn-sm fw-bold d-flex align-items-center justify-content-center gap-2 d-none" id="voice-btn-stop" onclick="window.PulseCareVoice.stop()">
            <i class="bi bi-stop-fill fs-6"></i> <span>${lang.stop}</span>
          </button>
        </div>

        <!-- Interactive Tap-to-Speak Mode Toggle -->
        <div class="mb-3">
          <button type="button" class="btn btn-sm btn-outline-secondary w-100 d-flex align-items-center justify-content-center gap-2" id="voice-btn-tapmode" onclick="window.PulseCareVoice.toggleTapMode()">
            <i class="bi bi-hand-index-thumb me-1"></i> <span id="voice-tap-text">${lang.tapModeOff}</span>
          </button>
        </div>

        <!-- Audio Speed Control -->
        <div class="d-flex align-items-center justify-content-between bg-light p-2 rounded-3 fs-8">
          <span class="text-muted fw-semibold"><i class="bi bi-speedometer2 me-1"></i>${lang.speed}:</span>
          <div class="btn-group btn-group-sm" role="group">
            <button type="button" class="btn btn-outline-secondary py-0 px-2 fs-9" onclick="window.PulseCareVoice.setRate(0.75)">0.8x</button>
            <button type="button" class="btn btn-primary py-0 px-2 fs-9 fw-bold" id="voice-speed-val" onclick="window.PulseCareVoice.setRate(0.9)">0.9x</button>
            <button type="button" class="btn btn-outline-secondary py-0 px-2 fs-9" onclick="window.PulseCareVoice.setRate(1.1)">1.1x</button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(widget);
  }

  // Public API
  window.PulseCareVoice = {
    readPage: readFullPage,
    pause: pauseSpeaking,
    resume: resumeSpeaking,
    stop: stopSpeaking,
    speakText: speak,
    setRate: setSpeechRate,
    toggleTapMode: toggleTapToSpeak,
    onLanguageChanged: handleLanguageChanged,
    toggleExpand: function (e) {
      if (e) e.stopPropagation();
      const panel = document.getElementById("voice-expanded-panel");
      const icon = document.getElementById("voice-expand-icon");
      if (panel) {
        const isHidden = panel.classList.contains("d-none");
        if (isHidden) {
          panel.classList.remove("d-none");
          if (icon) icon.className = "bi bi-chevron-down fs-7";
        } else {
          panel.classList.add("d-none");
          if (icon) icon.className = "bi bi-chevron-up fs-7";
        }
      }
    }
  };

  // Initialize on page load
  document.addEventListener("DOMContentLoaded", function () {
    injectVoiceWidget();
    document.addEventListener("click", handleDocumentTap, true);

    // Auto-update widget labels when language changes
    updateWidgetUI();
  });

})();
