'use client';
import React, { useState } from 'react';

const BACKEND_URL = "http://localhost:8000";

export default function VoiceTab() {
  const [recording, setRecording] = useState(false);
  const [status, setStatus] = useState('Prêt pour interaction vocale (micro) ou écrite (texte).');
  const [textInput, setTextInput] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mediaRecorderObj, setMediaRecorderObj] = useState(null);
  const [activeMediaStream, setActiveMediaStream] = useState(null);

  const handleSendText = async (e) => {
    if (e) e.preventDefault();
    if (!textInput.trim() || loading) return;

    const userMessage = textInput.trim();
    setTextInput('');
    setLoading(true);
    setStatus('L\'Agent IA Commercial prépare sa réponse...');

    setChatMessages((prev) => [
      ...prev,
      { role: 'user', content: userMessage, timestamp: new Date().toLocaleTimeString() }
    ]);

    try {
      const token = localStorage.getItem("auth_token");
      const res = await fetch(`${BACKEND_URL}/api/conversation/chat/demo_session`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { "Authorization": `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ message: userMessage })
      });

      if (res.ok) {
        const data = await res.json();
        const responseText = data.response || "Désolé, aucune réponse générée.";
        setChatMessages((prev) => [
          ...prev,
          { role: 'assistant', content: responseText, timestamp: new Date().toLocaleTimeString() }
        ]);
        setStatus('Réponse générée avec succès !');
      } else {
        setStatus('❌ Erreur de réponse du serveur.');
      }
    } catch (err) {
      console.error(err);
      setStatus('❌ Erreur de connexion au serveur backend.');
    } finally {
      setLoading(false);
    }
  };

  const handleStartRecording = async () => {
    setStatus("⚡ Demande d'accès au microphone...");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setActiveMediaStream(stream);
      const recorder = new MediaRecorder(stream);
      const chunks = [];

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        setActiveMediaStream(null);

        const blob = new Blob(chunks, { type: "audio/webm" });
        setStatus("⏳ Traitement en cours (STT Faster-Whisper -> Agent LLM -> Synthèse Vocale)...");
        setLoading(true);

        const formData = new FormData();
        formData.append("file", blob, "input.webm");
        formData.append("session_id", "demo_session");

        try {
          const token = localStorage.getItem("auth_token");
          const res = await fetch(`${BACKEND_URL}/api/v1/voice/interact`, {
            method: "POST",
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            body: formData,
          });

          if (res.ok) {
            const data = await res.json();
            if (data.user_transcript) {
              setChatMessages((prev) => [
                ...prev,
                { role: 'user', content: `🎙️ ${data.user_transcript}`, timestamp: new Date().toLocaleTimeString() }
              ]);
            }
            if (data.agent_response) {
              setChatMessages((prev) => [
                ...prev,
                { role: 'assistant', content: data.agent_response, timestamp: new Date().toLocaleTimeString() }
              ]);
            }
            setStatus(`✅ Réponse vocale générée (${data.detected_language || 'Darija/FR'}) !`);

            if (data.audio_base64) {
              const audioSrc = `data:${data.content_type || "audio/mpeg"};base64,${data.audio_base64}`;
              const audio = new Audio(audioSrc);
              audio.play();
            }
          } else {
            setStatus("❌ Erreur de traitement vocal par le serveur.");
          }
        } catch (err) {
          setStatus("❌ Erreur de connexion avec le serveur vocal.");
        } finally {
          setLoading(false);
        }
      };

      recorder.start();
      setMediaRecorderObj(recorder);
      setRecording(true);
      setStatus("🔴 Enregistrement vocal en cours... Cliquez à nouveau pour arrêter.");
    } catch (err) {
      setRecording(false);
      setStatus("❌ Impossible d'accéder au microphone : " + err.message);
    }
  };

  const handleStopRecording = () => {
    setRecording(false);
    if (mediaRecorderObj && mediaRecorderObj.state !== "inactive") {
      try { mediaRecorderObj.stop(); } catch (e) {}
    }
    if (activeMediaStream) {
      activeMediaStream.getTracks().forEach((track) => track.stop());
      setActiveMediaStream(null);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <span>💬 Voice & Text AI Agent</span>
            <span className="text-xs px-3 py-1 bg-violet-600/20 text-violet-300 border border-violet-500/30 rounded-full font-mono">
              Darija / FR / EN
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Échangez au choix par écrit (champ de texte ci-dessous) ou de vive voix (microphone) avec l&apos;Agent IA Commercial.
          </p>
        </div>
        <span className="bg-emerald-600/20 text-emerald-400 text-xs px-3 py-1 rounded-full font-mono border border-emerald-500/30">
          WebSocket & REST Active
        </span>
      </div>

      {/* Voice Recording Control */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 text-center flex flex-col items-center justify-center space-y-4">
        <button
          type="button"
          onClick={recording ? handleStopRecording : handleStartRecording}
          className={`w-20 h-20 rounded-full flex items-center justify-center transition-all transform hover:scale-105 ${
            recording ? 'bg-rose-600 animate-pulse text-white shadow-lg shadow-rose-600/50' : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30'
          }`}
        >
          <svg className="w-9 h-9" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 016 0v6a3 3 0 01-3 3z" />
          </svg>
        </button>
        <p className="text-xs font-semibold text-slate-300">{status}</p>
      </div>

      {/* Message Thread */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 min-h-[220px] max-h-[360px] overflow-y-auto space-y-3">
        {chatMessages.length === 0 ? (
          <div className="text-center py-10 text-slate-500 text-xs">
            Aucun message pour le moment. Tapez votre message ci-dessous ou utilisez le micro.
          </div>
        ) : (
          chatMessages.map((msg, idx) => (
            <div key={idx} className={`flex items-start space-x-3 ${msg.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}>
              <div className={`w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold shrink-0 ${
                msg.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-violet-300 border border-violet-500/30'
              }`}>
                {msg.role === 'user' ? '👤' : '🤖'}
              </div>
              <div className={`max-w-[80%] rounded-2xl p-3.5 text-xs leading-relaxed ${
                msg.role === 'user' ? 'bg-indigo-600 text-white rounded-tr-none' : 'bg-slate-800 text-slate-200 border border-slate-700 rounded-tl-none'
              }`}>
                <div className="text-[10px] opacity-75 font-semibold mb-1">
                  {msg.role === 'user' ? 'Vous' : 'Agent IA Commercial'} • {msg.timestamp}
                </div>
                <p className="whitespace-pre-line">{msg.content}</p>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Text Input Area Form */}
      <form onSubmit={handleSendText} className="flex gap-3">
        <input
          type="text"
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          placeholder="Écrivez votre message à l'Agent IA (ex: Quels sont vos tarifs ?...)"
          className="flex-1 bg-slate-900 border border-slate-700 focus:border-indigo-500 rounded-xl px-4 py-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none transition"
        />
        <button
          type="submit"
          disabled={loading || !textInput.trim()}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-bold px-6 py-3 rounded-xl transition text-xs flex items-center space-x-2 shadow-lg shadow-indigo-600/30"
        >
          <span>Envoyer</span>
          <span>🚀</span>
        </button>
      </form>
    </div>
  );
}
