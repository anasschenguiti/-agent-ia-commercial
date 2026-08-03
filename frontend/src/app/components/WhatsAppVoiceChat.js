'use client';
import React, { useState, useRef, useEffect } from 'react';

const BACKEND_URL = "http://localhost:8000";

export default function WhatsAppVoiceChat({ selectedProspect }) {
  const [chatFeed, setChatFeed] = useState([
    {
      id: "welcome-msg",
      role: "assistant",
      type: "text",
      userText: "",
      agentText: "Salam ! Marhaba bik. Je suis l'Agent Commercial d'IKSATECH. Comment puis-je vous aider aujourd'hui ?",
      audioUrl: null,
      detectedLang: "Français / Darija",
      metrics: { total_duration_sec: 0.15 },
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);

  const [textInput, setTextInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const [recordDuration, setRecordDuration] = useState(0);
  const [statusMsg, setStatusMsg] = useState("🟢 Agent Commercial IA en ligne & prêt (Vocale / Texte)");
  const [playingAudioId, setPlayingAudioId] = useState(null);

  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const timerRef = useRef(null);
  const chatEndRef = useRef(null);
  const audioObjRef = useRef(null);

  // Auto-scroll to bottom of conversation thread
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatFeed, loading]);

  // Handle Recording Timer
  useEffect(() => {
    if (recording) {
      setRecordDuration(0);
      timerRef.current = setInterval(() => {
        setRecordDuration((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [recording]);

  // Helper to play audio Base64
  const playAudioTrack = (msgId, audioUrl) => {
    if (!audioUrl) return;

    if (audioObjRef.current) {
      audioObjRef.current.pause();
      audioObjRef.current = null;
    }

    if (playingAudioId === msgId) {
      setPlayingAudioId(null);
      return;
    }

    const audio = new Audio(audioUrl);
    audioObjRef.current = audio;
    setPlayingAudioId(msgId);

    audio.play().catch((err) => console.log("Play audio error:", err));
    audio.onended = () => setPlayingAudioId(null);
  };

  // Clear conversation history
  const handleClearChat = async () => {
    try {
      const sessionId = selectedProspect ? selectedProspect.id : "voice_tab_demo";
      await fetch(`${BACKEND_URL}/api/conversation/history/${sessionId}`, { method: "DELETE" });
    } catch (e) {
      console.log("Error clearing session history:", e);
    }
    setChatFeed([
      {
        id: "welcome-msg-" + Date.now(),
        role: "assistant",
        type: "text",
        userText: "",
        agentText: "Marhaba ! La conversation a été réinitialisée. Comment puis-je vous accompagner ?",
        audioUrl: null,
        detectedLang: "Français / Darija",
        metrics: { total_duration_sec: 0.1 },
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
    setStatusMsg("Conversation réinitialisée.");
  };

  // Submit Written Text Message (WhatsApp / ChatGPT Text-to-Text Mode)
  const handleSendText = async (e) => {
    if (e) e.preventDefault();
    if (!textInput.trim() || loading) return;

    const userMessage = textInput.trim();
    setTextInput("");
    setLoading(true);
    setStatusMsg("⚡ Traitement de votre message par l'Agent IA...");

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const msgId = "text-msg-" + Date.now();
    const startTime = Date.now();

    try {
      const token = localStorage.getItem("auth_token");
      const sessionId = selectedProspect ? selectedProspect.id : "voice_tab_demo";
      const res = await fetch(`${BACKEND_URL}/api/conversation/chat/${sessionId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { "Authorization": `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ message: userMessage })
      });

      if (res.ok) {
        const data = await res.json();
        const agentText = data.response || "Désolé, aucune réponse générée.";
        const latencySec = ((Date.now() - startTime) / 1000).toFixed(2);

        setChatFeed((prev) => [
          ...prev,
          {
            id: msgId,
            role: "turn",
            type: "text",
            userText: userMessage,
            agentText: agentText,
            audioUrl: null,
            detectedLang: "Français / Darija",
            metrics: { total_duration_sec: parseFloat(latencySec) },
            timestamp: timeStr
          }
        ]);

        setStatusMsg("✅ Message texte reçu et répondu !");
      } else {
        setStatusMsg("❌ Erreur de réponse du serveur.");
      }
    } catch (err) {
      console.error(err);
      setStatusMsg("❌ Erreur de connexion avec le serveur.");
    } finally {
      setLoading(false);
    }
  };

  // Start Voice Microphone Recording (WhatsApp style)
  const handleStartRecording = async () => {
    setStatusMsg("⚡ Demande d'accès au microphone...");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "audio/mp4";

      const recorder = new MediaRecorder(stream, { mimeType });
      const chunks = [];

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;

        if (chunks.length === 0) {
          setStatusMsg("❌ Enregistrement audio vide. Réessayez.");
          return;
        }

        const blob = new Blob(chunks, { type: mimeType });
        setStatusMsg("⏳ Traitement en cours (STT Faster-Whisper -> Agent LLM Qwen -> Edge-TTS)...");
        setLoading(true);

        const formData = new FormData();
        formData.append("file", blob, "input.webm");
        formData.append("session_id", selectedProspect ? selectedProspect.id : "voice_tab_demo");

        const msgId = "voice-msg-" + Date.now();
        const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        try {
          const token = localStorage.getItem("auth_token");
          const res = await fetch(`${BACKEND_URL}/api/v1/voice/interact`, {
            method: "POST",
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            body: formData,
          });

          if (res.ok) {
            const data = await res.json();
            const audioSrc = data.audio_base64
              ? `data:${data.content_type || "audio/mpeg"};base64,${data.audio_base64}`
              : null;

            setChatFeed((prev) => [
              ...prev,
              {
                id: msgId,
                role: "turn",
                type: "voice",
                userText: data.user_transcript || "Message Vocal",
                agentText: data.agent_response || "Pas de réponse",
                audioUrl: audioSrc,
                detectedLang: data.detected_language || "Darija",
                metrics: data.metrics || { total_duration_sec: 0.45 },
                timestamp: timeStr
              }
            ]);

            setStatusMsg(`✅ Réponse vocale générée (${data.detected_language || 'Darija'}) !`);

            if (audioSrc) {
              playAudioTrack(msgId, audioSrc);
            }
          } else {
            setStatusMsg("❌ Erreur lors du traitement vocal par le serveur.");
          }
        } catch (err) {
          setStatusMsg("❌ Erreur de connexion avec le serveur vocal.");
        } finally {
          setLoading(false);
        }
      };

      recorder.start(250);
      mediaRecorderRef.current = recorder;
      setRecording(true);
      setStatusMsg("🔴 Enregistrement vocal en cours... Parlez clairement.");
    } catch (err) {
      setRecording(false);
      setStatusMsg("❌ Impossible d'accéder au microphone : " + err.message);
    }
  };

  // Stop Recording
  const handleStopRecording = () => {
    setRecording(false);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try { mediaRecorderRef.current.stop(); } catch (e) {}
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
  };

  const formatSecs = (sec) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div className="flex flex-col h-[780px] bg-slate-950 rounded-3xl border border-fuchsia-900/40 shadow-2xl overflow-hidden backdrop-blur-xl">
      {/* WhatsApp / ChatGPT Header Bar */}
      <div className="bg-slate-900/90 border-b border-fuchsia-900/30 px-6 py-4 flex justify-between items-center z-10">
        <div className="flex items-center space-x-4">
          <div className="relative">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-fuchsia-600 to-violet-600 flex items-center justify-center text-white font-extrabold text-xl shadow-lg shadow-fuchsia-600/30">
              🤖
            </div>
            <span className="absolute -bottom-1 -right-1 w-4 h-4 bg-emerald-500 border-2 border-slate-900 rounded-full animate-pulse"></span>
          </div>

          <div>
            <div className="flex items-center space-x-2">
              <h3 className="font-extrabold text-slate-100 text-base">Agent Commercial IA</h3>
              <span className="px-2.5 py-0.5 bg-fuchsia-500/20 text-fuchsia-300 border border-fuchsia-500/30 rounded-full text-[10px] font-bold uppercase tracking-wider">
                Qwen 2.5 (7B)
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono mt-0.5 flex items-center space-x-2">
              <span>🇲🇦 Darija</span>
              <span>•</span>
              <span>🇫🇷 Français</span>
              <span>•</span>
              <span>🇬🇧 English</span>
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleClearChat}
            className="px-3.5 py-2 bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white rounded-xl border border-slate-700 text-xs font-semibold transition flex items-center space-x-2"
            title="Effacer l'historique de discussion"
          >
            <span>🗑️</span>
            <span className="hidden sm:inline">Effacer Chat</span>
          </button>

          <span className="hidden lg:flex items-center space-x-2 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-xl text-xs font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            <span>Ultra Latence Opérationnelle</span>
          </span>
        </div>
      </div>

      {/* Status Bar */}
      <div className="bg-fuchsia-950/40 border-b border-fuchsia-900/20 px-6 py-2 flex items-center justify-between text-xs font-mono text-fuchsia-300">
        <div className="flex items-center space-x-2">
          <span className={`w-2 h-2 rounded-full ${recording ? 'bg-rose-500 animate-ping' : 'bg-fuchsia-400'}`}></span>
          <span>{statusMsg}</span>
        </div>
        {recording && (
          <span className="bg-rose-600 text-white font-extrabold px-3 py-0.5 rounded-full text-[11px] animate-pulse">
            ⏺️ Enregistrement {formatSecs(recordDuration)}
          </span>
        )}
      </div>

      {/* WhatsApp / ChatGPT Message Thread Container */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-slate-950 to-slate-950">
        {chatFeed.map((turn) => (
          <div key={turn.id} className="space-y-4 animate-fadeIn">
            {/* User Message Bubble (Right Side) */}
            {turn.userText && (
              <div className="flex justify-end items-end space-x-2">
                <div className="max-w-[82%] sm:max-w-[70%] bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white rounded-2xl rounded-tr-none p-4 shadow-xl shadow-fuchsia-900/20 space-y-2">
                  <div className="flex items-center justify-between space-x-4 border-b border-white/10 pb-1.5">
                    <span className="text-[10px] uppercase font-extrabold tracking-wider text-violet-200 flex items-center space-x-1">
                      <span>{turn.type === 'voice' ? '🎙️ Message Vocal' : '✍️ Message Écrit'}</span>
                    </span>
                    <span className="text-[10px] opacity-75 font-mono">{turn.timestamp}</span>
                  </div>
                  <p className="text-sm leading-relaxed font-medium">{turn.userText}</p>
                </div>
                <div className="w-8 h-8 rounded-full bg-violet-600 text-white font-extrabold text-xs flex items-center justify-center shrink-0">
                  👤
                </div>
              </div>
            )}

            {/* Assistant AI Message Bubble (Left Side - WhatsApp / ChatGPT Style) */}
            {turn.agentText && (
              <div className="flex justify-start items-start space-x-3">
                <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-fuchsia-600 to-violet-600 text-white font-extrabold text-base flex items-center justify-center shrink-0 shadow-lg shadow-fuchsia-600/30">
                  🤖
                </div>

                <div className="max-w-[85%] sm:max-w-[75%] bg-slate-900/90 border border-fuchsia-900/40 text-slate-100 rounded-2xl rounded-tl-none p-5 shadow-2xl backdrop-blur-xl space-y-4">
                  <div className="flex items-center justify-between border-b border-white/10 pb-2">
                    <div className="flex items-center space-x-2">
                      <span className="font-extrabold text-xs text-fuchsia-300">Agent Commercial IKSATECH</span>
                      {turn.detectedLang && (
                        <span className="px-2 py-0.5 bg-fuchsia-500/20 text-fuchsia-300 border border-fuchsia-500/30 rounded-md text-[10px] font-mono">
                          {turn.detectedLang}
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] text-slate-400 font-mono">{turn.timestamp}</span>
                  </div>

                  {/* Text Response Content */}
                  <p className="text-sm text-slate-200 leading-relaxed font-normal whitespace-pre-line">
                    {turn.agentText}
                  </p>

                  {/* Playable WhatsApp Audio Player Component */}
                  {turn.audioUrl && (
                    <div className="bg-slate-950/80 border border-fuchsia-500/30 rounded-xl p-3.5 flex items-center justify-between gap-4">
                      <button
                        onClick={() => playAudioTrack(turn.id, turn.audioUrl)}
                        className={`w-11 h-11 rounded-xl flex items-center justify-center text-white font-extrabold transition shadow-lg shrink-0 ${
                          playingAudioId === turn.id
                            ? 'bg-rose-600 hover:bg-rose-500 animate-pulse shadow-rose-600/50'
                            : 'bg-gradient-to-r from-fuchsia-600 to-violet-600 hover:from-fuchsia-500 hover:to-violet-500 shadow-fuchsia-600/30'
                        }`}
                      >
                        <span className="text-lg">{playingAudioId === turn.id ? '⏸️' : '▶️'}</span>
                      </button>

                      {/* Visual Waveform */}
                      <div className="flex-1 flex items-center space-x-1.5 h-6">
                        {[40, 75, 55, 90, 30, 80, 60, 100, 45, 70, 85, 35, 95, 50, 65].map((height, i) => (
                          <span
                            key={i}
                            className={`w-1 rounded-full transition-all duration-300 ${
                              playingAudioId === turn.id
                                ? 'bg-fuchsia-400 animate-pulse'
                                : 'bg-slate-700'
                            }`}
                            style={{ height: `${playingAudioId === turn.id ? Math.max(20, (height * Math.random()).toFixed(0)) : height}%` }}
                          ></span>
                        ))}
                      </div>

                      {/* Audio Tag */}
                      <span className="text-[10px] font-mono text-fuchsia-300 shrink-0 bg-fuchsia-950/80 px-2.5 py-1 rounded-lg border border-fuchsia-800/40">
                        🎵 Note Vocale
                      </span>
                    </div>
                  )}

                  {/* Metrics Badge */}
                  {turn.metrics && (
                    <div className="flex items-center space-x-3 text-[10px] font-mono text-slate-400 pt-1 border-t border-white/5">
                      <span>⚡ Latence : <strong className="text-fuchsia-300">{(turn.metrics.total_duration_sec || 0.4).toFixed(2)}s</strong></span>
                      <span>•</span>
                      <span>Moteur : <strong className="text-violet-300">Edge-TTS (15% Fast)</strong></span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Typing Loading Indicator */}
        {loading && (
          <div className="flex justify-start items-center space-x-3 animate-pulse">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-fuchsia-600 to-violet-600 text-white font-extrabold text-base flex items-center justify-center shrink-0 shadow-lg shadow-fuchsia-600/30">
              🤖
            </div>
            <div className="bg-slate-900 border border-fuchsia-900/40 px-5 py-4 rounded-2xl rounded-tl-none flex items-center space-x-2">
              <span className="w-2.5 h-2.5 bg-fuchsia-400 rounded-full animate-bounce"></span>
              <span className="w-2.5 h-2.5 bg-violet-400 rounded-full animate-bounce [animation-delay:0.2s]"></span>
              <span className="w-2.5 h-2.5 bg-fuchsia-400 rounded-full animate-bounce [animation-delay:0.4s]"></span>
              <span className="text-xs text-slate-300 font-mono ml-2">L&apos;Agent génère sa réponse et l&apos;audio...</span>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* WhatsApp / ChatGPT Bottom Input Toolbar */}
      <div className="bg-slate-900/95 border-t border-fuchsia-900/30 p-4 backdrop-blur-xl">
        <form onSubmit={handleSendText} className="flex items-center gap-3">
          {/* Big WhatsApp Microphone Button */}
          <button
            type="button"
            onClick={recording ? handleStopRecording : handleStartRecording}
            className={`w-12 h-12 rounded-2xl flex items-center justify-center font-bold text-xl transition-all duration-300 shrink-0 shadow-lg ${
              recording
                ? 'bg-rose-600 hover:bg-rose-500 text-white animate-pulse shadow-rose-600/50 scale-110'
                : 'bg-gradient-to-r from-fuchsia-600 to-violet-600 hover:from-fuchsia-500 hover:to-violet-500 text-white shadow-fuchsia-600/30 hover:scale-105'
            }`}
            title={recording ? "Arrêter l'enregistrement" : "Enregistrer un message vocal (Micro)"}
          >
            <span>{recording ? '🛑' : '🎙️'}</span>
          </button>

          {/* ChatGPT Text Input */}
          <div className="flex-1 relative">
            <input
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Écrivez votre message à l'Agent IA (ex: Quels sont vos tarifs ? / bch7al site web ?)..."
              className="w-full bg-slate-950 border border-fuchsia-900/40 focus:border-fuchsia-500 rounded-2xl px-5 py-3.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none transition shadow-inner pr-12"
            />
          </div>

          {/* Send Button */}
          <button
            type="submit"
            disabled={loading || !textInput.trim()}
            className="bg-gradient-to-r from-fuchsia-600 to-violet-600 hover:from-fuchsia-500 hover:to-violet-500 disabled:opacity-40 text-white font-extrabold px-6 py-3.5 rounded-2xl transition text-xs flex items-center space-x-2 shadow-lg shadow-fuchsia-600/30 shrink-0"
          >
            <span>Envoyer</span>
            <span>🚀</span>
          </button>
        </form>
      </div>
    </div>
  );
}
