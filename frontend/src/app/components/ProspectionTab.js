'use client';
import React, { useState } from 'react';

export default function ProspectionTab() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [prospects, setProspects] = useState([]);

  const handleSearch = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch('/api/prospection/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: { keywords: query.split(' '), max_results: 10 } }),
      });
      const data = await res.json();
      setProspects(data.prospects || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-slate-100">Prospection B2B Automated</h2>
        <span className="bg-indigo-600/20 text-indigo-400 text-xs px-3 py-1 rounded-full font-mono border border-indigo-500/30">
          Module Active
        </span>
      </div>

      <form onSubmit={handleSearch} className="flex gap-4">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Mots-clés (ex: Agence Web Casablanca, Restaurant Rabat)..."
          className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-indigo-500"
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-6 py-3 rounded-xl transition"
        >
          {loading ? 'Recherche...' : 'Lancer Scraping'}
        </button>
      </form>

      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4">
        <h3 className="text-lg font-semibold text-slate-200 mb-4">Résultats ({prospects.length})</h3>
        {prospects.length === 0 ? (
          <p className="text-slate-400 text-sm italic">Aucun prospect chargé. Tapez une recherche ci-dessus.</p>
        ) : (
          <div className="space-y-3">
            {prospects.map((p, idx) => (
              <div key={idx} className="bg-slate-800/40 p-4 rounded-xl border border-slate-700/50 flex justify-between items-center">
                <div>
                  <h4 className="font-semibold text-slate-100">{p.company}</h4>
                  <p className="text-xs text-slate-400">{p.email || 'Pas d\'email'} • {p.phone || 'Pas de tel'}</p>
                </div>
                <span className="text-sm font-bold text-emerald-400">{p.score ? `${p.score}/100` : 'Non scoré'}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
