'use client';
import React, { useState } from 'react';

export default function CrmTab() {
  const [crmType, setCrmType] = useState('odoo');
  const [contactId, setContactId] = useState('');
  const [stage, setStage] = useState('Qualified');
  const [statusMessage, setStatusMessage] = useState('');

  const handleUpdateStage = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/crm/stage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ crm_type: crmType, contact_id: contactId, stage: stage }),
      });
      const data = await res.json();
      setStatusMessage(`Statut CRM mis à jour : ${JSON.stringify(data)}`);
    } catch (err) {
      setStatusMessage(`Erreur CRM: ${err}`);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold text-slate-100">Synchronisation CRM (Odoo & HubSpot)</h2>

      <form onSubmit={handleUpdateStage} className="bg-slate-900/60 p-6 rounded-2xl border border-slate-800 space-y-4 max-w-xl">
        <div>
          <label className="block text-sm text-slate-300 mb-1">Plateforme CRM</label>
          <select
            value={crmType}
            onChange={(e) => setCrmType(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-slate-100"
          >
            <option value="odoo">Odoo CRM</option>
            <option value="hubspot">HubSpot CRM</option>
          </select>
        </div>

        <div>
          <label className="block text-sm text-slate-300 mb-1">ID Partenaire / Email Contact</label>
          <input
            type="text"
            value={contactId}
            onChange={(e) => setContactId(e.target.value)}
            placeholder="ex: 12 ou contact@entreprise.ma"
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-slate-100"
          />
        </div>

        <div>
          <label className="block text-sm text-slate-300 mb-1">Nouvelle Étape Pipeline</label>
          <input
            type="text"
            value={stage}
            onChange={(e) => setStage(e.target.value)}
            placeholder="ex: Qualified, Proposition, Won"
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-slate-100"
          />
        </div>

        <button
          type="submit"
          className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2.5 rounded-xl font-medium transition w-full"
        >
          Mettre à jour étape Deal
        </button>

        {statusMessage && (
          <div className="p-3 bg-slate-800 rounded-lg text-xs font-mono text-indigo-300 break-all">
            {statusMessage}
          </div>
        )}
      </form>
    </div>
  );
}
