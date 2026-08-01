'use client';
import React, { useState } from 'react';

export default function VoiceTab() {
  const [recording, setRecording] = useState(false);
  const [status, setStatus] = useState('Prêt pour enregistrement vocal.');
  const [transcript, setTranscript] = useState('');
  const [agentResponse, setAgentResponse] = useState('');

  const toggleRecording = () => {
    if (recording) {
      setRecording(false);
      setStatus('Traitement audio...');
      setTimeout(() => {
        setTranscript('Salam, ch7al kayklaf mshro3 site web f IKSATECH ?');
        setAgentResponse('Salam ! Nos tarifs de développement web débutent à partir de 4 900 DH. Souhaitez-vous planifier un échange de 15 minutes ?');
        setStatus('Réponse générée.');
      }, 1200);
    } else {
      setRecording(true);
      setStatus('Enregistrement en cours (Micro actif)...');
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-slate-100">Voice AI Agent (Darija / FR / EN)</h2>
        <span className="bg-emerald-600/20 text-emerald-400 text-xs px-3 py-1 rounded-full font-mono border border-emerald-500/30">
          WebSocket Live
        </span>
      </div>

      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-8 text-center flex flex-col items-center justify-center space-y-6">
        <button
          onClick={toggleRecording}
          className={`w-24 h-24 rounded-full flex items-center justify-center transition-all transform hover:scale-105 ${
            recording ? 'bg-red-600 animate-pulse text-white' : 'bg-indigo-600 hover:bg-indigo-500 text-white'
          }`}
        >
          <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 016 0v6a3 3 0 01-3 3z" />
          </svg>
        </button>
        <p className="text-sm font-medium text-slate-300">{status}</p>
      </div>

      {transcript && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800">
            <h4 className="text-xs uppercase tracking-wider text-slate-400 mb-2">Transcription Utilisateur</h4>
            <p className="text-slate-100 font-medium">{transcript}</p>
          </div>
          <div className="bg-indigo-950/40 p-4 rounded-xl border border-indigo-900/50">
            <h4 className="text-xs uppercase tracking-wider text-indigo-400 mb-2">Réponse Agent Vocal</h4>
            <p className="text-indigo-100 font-medium">{agentResponse}</p>
          </div>
        </div>
      )}
    </div>
  );
}
