"use client";

import React, { useState } from "react";

export default function OsmosSection({ prospects, apiFetch, BACKEND_URL }) {
  const [osmosLoading, setOsmosLoading] = useState(false);
  const [osmosScoreResults, setOsmosScoreResults] = useState(null);
  const [osmosPersona, setOsmosPersona] = useState(null);
  const [osmosPlan, setOsmosPlan] = useState(null);
  const [osmosContent, setOsmosContent] = useState(null);
  const [osmosError, setOsmosError] = useState("");
  const [osmosActiveSection, setOsmosActiveSection] = useState("score");
  const [osmosCampaignName, setOsmosCampaignName] = useState("IKSATECH");
  const [osmosCampaignSector, setOsmosCampaignSector] = useState("SaaS B2B");
  const [osmosCampaignValue, setOsmosCampaignValue] = useState("Automatisation commerciale IA pour PME");
  const [osmosSelectedProspect, setOsmosSelectedProspect] = useState(null);

  const handleOsmosScore = async () => {
    if (!prospects || prospects.length === 0) {
      setOsmosError("Lancez d'abord une recherche de prospects.");
      return;
    }
    setOsmosLoading(true);
    setOsmosError("");
    setOsmosScoreResults(null);
    try {
      const payload = {
        prospects: prospects.map((p) => ({
          name: `${p.first_name} ${p.last_name} (${p.company || "?"})`,
          sector: p.industry || "Services",
          size: p.company_size || "11-50",
          contact_name: `${p.first_name} ${p.last_name}`,
          contact_title: p.job_title || "Décideur",
          sector_fit: Math.min(10, Math.max(1, Math.round((p.score || 50) / 10))),
          size_score: p.company_size === "51-200" ? 7 : p.company_size === "201-500" ? 9 : 5,
          accessibility: p.job_title && (p.job_title.includes("CEO") || p.job_title.includes("Director") || p.job_title.includes("Founder")) ? 8 : 5,
          recent_activity: Math.floor(Math.random() * 4) + 5,
        })),
      };
      const res = await apiFetch(`${BACKEND_URL}/api/prospection/osmos/score`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const e = await res.json();
        throw new Error(e.detail || "Erreur scoring");
      }
      const data = await res.json();
      setOsmosScoreResults(data);
    } catch (e) {
      setOsmosError(e.message);
    } finally {
      setOsmosLoading(false);
    }
  };

  const handleOsmosPersona = async () => {
    setOsmosLoading(true);
    setOsmosError("");
    setOsmosPersona(null);
    try {
      const payload = {
        campaign: {
          company_name: osmosCampaignName,
          company_sector: osmosCampaignSector,
          value_proposition: osmosCampaignValue,
        },
        prospects_names: prospects.slice(0, 5).map((p) => p.company || p.first_name),
      };
      const res = await apiFetch(`${BACKEND_URL}/api/prospection/osmos/persona`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const e = await res.json();
        throw new Error(e.detail || "Erreur persona");
      }
      const data = await res.json();
      setOsmosPersona(data.persona);
    } catch (e) {
      setOsmosError(e.message);
    } finally {
      setOsmosLoading(false);
    }
  };

  const handleOsmosPlan = async () => {
    if (!osmosPersona) {
      setOsmosError("Générez d'abord un Persona IA.");
      return;
    }
    if (!osmosSelectedProspect) {
      setOsmosError("Sélectionnez un prospect cible.");
      return;
    }
    setOsmosLoading(true);
    setOsmosError("");
    setOsmosPlan(null);
    setOsmosContent(null);
    try {
      const payload = {
        campaign: {
          company_name: osmosCampaignName,
          company_sector: osmosCampaignSector,
          value_proposition: osmosCampaignValue,
        },
        persona: osmosPersona,
        prospect: osmosSelectedProspect,
      };
      const res = await apiFetch(`${BACKEND_URL}/api/prospection/osmos/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const e = await res.json();
        throw new Error(e.detail || "Erreur plan");
      }
      const data = await res.json();
      setOsmosPlan(data.action_plan);
      setOsmosContent(data.content);
    } catch (e) {
      setOsmosError(e.message);
    } finally {
      setOsmosLoading(false);
    }
  };

  const getStepBadgeClass = (actionType) => {
    if (actionType === "connect") return "bg-blue-900 text-blue-300 border-blue-700";
    if (actionType === "like") return "bg-rose-900 text-rose-300 border-rose-700";
    if (actionType === "comment") return "bg-amber-900 text-amber-300 border-amber-700";
    if (actionType === "message" || actionType === "dm") return "bg-emerald-900 text-emerald-300 border-emerald-700";
    return "bg-violet-900 text-violet-300 border-violet-700";
  };

  return (
    <div className="col-span-1 lg:col-span-3 mt-2">
      <div className="bg-slate-900 border border-violet-900 rounded-2xl p-6 backdrop-blur-md">
        {/* Header OSMOS */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-fuchsia-600 to-violet-600 flex items-center justify-center shadow-lg">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div>
              <h3 className="font-bold text-base text-white">Prospection Intelligente OSMOS</h3>
              <p className="text-xs text-violet-400">Scoring AHP/TOPSIS · Persona IA · Plan d&apos;action LinkedIn</p>
            </div>
          </div>

          {/* Navigation Tabs OSMOS */}
          <div className="flex space-x-1 bg-slate-950 rounded-xl p-1 border border-violet-900">
            {[
              { id: "score", label: "🎯 Scoring AHP/TOPSIS" },
              { id: "persona", label: "🤖 Persona IA" },
              { id: "plan", label: "📋 Plan Action" },
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => {
                  setOsmosActiveSection(t.id);
                  setOsmosError("");
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  osmosActiveSection === t.id
                    ? "bg-violet-600 text-white shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {osmosError && (
          <div className="mb-4 p-3 bg-rose-950 border border-rose-800 text-rose-300 rounded-xl text-xs">
            ⚠️ {osmosError}
          </div>
        )}

        {/* SECTION 1 : SCORING AHP/TOPSIS */}
        {osmosActiveSection === "score" && (
          <div className="space-y-4">
            <p className="text-xs text-slate-400">
              Analyse les prospects trouvés avec l&apos;algorithme <strong className="text-violet-300">AHP/TOPSIS</strong> sur 4 critères :
              <span className="text-fuchsia-300"> Fit sectoriel · Taille · Accessibilité · Activité récente</span>.
              Chaque prospect reçoit un label <strong>Top / High / Medium / Low</strong> et un score sur 100.
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              {["Fit Sectoriel", "Taille Entreprise", "Accessibilité Contact", "Activité Récente"].map((c, i) => (
                <div key={i} className="bg-slate-950 border border-violet-900 rounded-xl p-3 text-center">
                  <div className="text-lg mb-1">{["🎯", "🏢", "🤝", "⚡"][i]}</div>
                  <div className="text-xs font-semibold text-slate-300">{c}</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Critère AHP #{i + 1}</div>
                </div>
              ))}
            </div>

            <button
              onClick={handleOsmosScore}
              disabled={osmosLoading || prospects.length === 0}
              className="w-full bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white font-bold py-3 px-6 rounded-xl transition shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2 text-sm"
            >
              {osmosLoading ? (
                <span>Scoring AHP/TOPSIS en cours...</span>
              ) : (
                <span>🎯 Scorer les {prospects.length} prospects avec AHP/TOPSIS</span>
              )}
            </button>

            {osmosScoreResults && (
              <div className="space-y-3 mt-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-white">Résultats du classement TOPSIS</h4>
                  <span className="text-[10px] text-slate-500">CR={osmosScoreResults.ahp_cr?.toFixed(3)} · {osmosScoreResults.ahp_consistent ? "Cohérent" : "À revoir"}</span>
                </div>
                {osmosScoreResults.results.map((r, i) => (
                  <div key={i} className="flex items-center justify-between bg-slate-950 border border-violet-900 rounded-xl px-4 py-3">
                    <div className="flex items-center space-x-3">
                      <span className="text-xs font-bold text-slate-500 w-5">#{r.topsis_rank}</span>
                      <span className="text-sm font-semibold text-slate-200">{r.name}</span>
                    </div>
                    <div className="flex items-center space-x-3">
                      <div className="w-24 bg-slate-800 rounded-full h-2">
                        <div className="h-2 rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-all" style={{ width: `${r.score_100}%` }}></div>
                      </div>
                      <span className="text-xs font-bold text-fuchsia-300 w-10 text-right">{r.score_100}</span>
                      <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full border ${
                        r.priority_label === "Top" ? "bg-emerald-950 text-emerald-300 border-emerald-800" :
                        r.priority_label === "High" ? "bg-violet-950 text-violet-300 border-violet-800" :
                        r.priority_label === "Medium" ? "bg-amber-950 text-amber-300 border-amber-800" :
                        "bg-slate-950 text-slate-400 border-slate-800"
                      }`}>{r.priority_label}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* SECTION 2 : PERSONA IA */}
        {osmosActiveSection === "persona" && (
          <div className="space-y-4">
            <p className="text-xs text-slate-400">Génère un <strong className="text-violet-300">persona commercial virtuel marocain</strong> via IA (Ollama qwen3:8b). Ce persona servira à personnaliser la prospection LinkedIn.</p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Nom de l&apos;entreprise</label>
                <input
                  type="text"
                  value={osmosCampaignName}
                  onChange={(e) => setOsmosCampaignName(e.target.value)}
                  className="w-full bg-slate-950 border border-violet-900 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-violet-500 text-slate-200"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Secteur ciblé</label>
                <input
                  type="text"
                  value={osmosCampaignSector}
                  onChange={(e) => setOsmosCampaignSector(e.target.value)}
                  className="w-full bg-slate-950 border border-violet-900 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-violet-500 text-slate-200"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Proposition de valeur</label>
                <input
                  type="text"
                  value={osmosCampaignValue}
                  onChange={(e) => setOsmosCampaignValue(e.target.value)}
                  className="w-full bg-slate-950 border border-violet-900 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-violet-500 text-slate-200"
                />
              </div>
            </div>

            <button
              onClick={handleOsmosPersona}
              disabled={osmosLoading}
              className="w-full bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white font-bold py-3 px-6 rounded-xl transition shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2 text-sm"
            >
              {osmosLoading ? (
                <span>Génération en cours (Ollama qwen3:8b)...</span>
              ) : (
                <span>🤖 Générer le Persona Commercial IA</span>
              )}
            </button>

            {osmosPersona && (
              <div className="bg-slate-950 border border-violet-800 rounded-2xl p-6 mt-4">
                <div className="flex items-start space-x-4">
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-violet-600 to-fuchsia-600 flex items-center justify-center text-2xl font-bold shadow-lg flex-shrink-0">
                    {osmosPersona.full_name?.charAt(0) || "?"}
                  </div>
                  <div className="flex-1">
                    <h4 className="font-extrabold text-lg text-white">{osmosPersona.full_name}</h4>
                    <p className="text-violet-300 text-sm font-medium">{osmosPersona.headline}</p>
                    <div className="flex items-center space-x-3 mt-1 text-xs text-slate-400">
                      <span>{osmosPersona.role}</span>
                      <span>·</span>
                      <span>{osmosPersona.seniority}</span>
                      <span>·</span>
                      <span>{osmosPersona.age} ans</span>
                    </div>
                  </div>
                </div>
                <p className="text-sm text-slate-300 mt-4 leading-relaxed">{osmosPersona.bio}</p>
                <div className="mt-4">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Compétences clés</div>
                  <div className="flex flex-wrap gap-2">
                    {(osmosPersona.key_skills || []).map((s, i) => (
                      <span key={i} className="text-xs bg-violet-950 text-violet-300 border border-violet-800 px-3 py-1 rounded-full">{s}</span>
                    ))}
                  </div>
                </div>
                {osmosPersona.past_projects?.length > 0 && (
                  <div className="mt-4">
                    <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Projets réussis</div>
                    <div className="space-y-2">
                      {osmosPersona.past_projects.slice(0, 2).map((proj, i) => (
                        <div key={i} className="bg-slate-900 rounded-xl px-4 py-2.5">
                          <div className="font-semibold text-xs text-white">{proj.title}</div>
                          <div className="text-xs text-emerald-400 mt-0.5">{proj.quantifiable_result}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <button
                  onClick={() => setOsmosActiveSection("plan")}
                  className="mt-4 w-full bg-fuchsia-950 border border-fuchsia-800 text-fuchsia-300 font-semibold py-2.5 rounded-xl text-xs transition"
                >
                  📋 Générer le Plan d&apos;action pour ce persona →
                </button>
              </div>
            )}
          </div>
        )}

        {/* SECTION 3 : PLAN D'ACTION */}
        {osmosActiveSection === "plan" && (
          <div className="space-y-4">
            <p className="text-xs text-slate-400">Génère un <strong className="text-violet-300">plan de prospection LinkedIn en 6 étapes</strong> (3 semaines) + contenus personnalisés (post, commentaire, DM) pour un prospect sélectionné.</p>
            {!osmosPersona && (
              <div className="p-4 bg-amber-950 border border-amber-800 rounded-xl text-amber-300 text-xs">
                ⚠️ Génère d&apos;abord un <strong>Persona IA</strong> (onglet 🤖 Persona IA) avant de créer un plan d&apos;action.
              </div>
            )}
            {prospects && prospects.length > 0 && (
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Sélectionner un prospect cible</label>
                <select
                  value={osmosSelectedProspect ? JSON.stringify(osmosSelectedProspect) : ""}
                  onChange={(e) => setOsmosSelectedProspect(e.target.value ? JSON.parse(e.target.value) : null)}
                  className="w-full bg-slate-950 border border-violet-900 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-violet-500 text-slate-200"
                >
                  <option value="">-- Choisir un prospect --</option>
                  {prospects.map((p, i) => (
                    <option key={i} value={JSON.stringify({ name: p.company || `${p.first_name} ${p.last_name}`, sector: p.industry, contact_name: `${p.first_name} ${p.last_name}`, contact_title: p.job_title, sector_fit: 7, size_score: 6, accessibility: 7, recent_activity: 6 })}>
                      {p.first_name} {p.last_name} — {p.company} ({p.job_title})
                    </option>
                  ))}
                </select>
              </div>
            )}
            <button
              onClick={handleOsmosPlan}
              disabled={osmosLoading || !osmosPersona || !osmosSelectedProspect}
              className="w-full bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white font-bold py-3 px-6 rounded-xl transition shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2 text-sm"
            >
              {osmosLoading ? (
                <span>Génération du plan + contenus...</span>
              ) : (
                <span>📋 Générer Plan 6 étapes + Contenus LinkedIn</span>
              )}
            </button>

            {osmosPlan && (
              <div className="space-y-4 mt-4">
                <h4 className="text-sm font-bold text-white">🗓️ Plan de prospection — 6 étapes sur 3 semaines</h4>
                <div className="space-y-2">
                  {(osmosPlan.steps || []).map((step, i) => (
                    <div key={i} className="flex items-start space-x-3 bg-slate-950 border border-violet-900 rounded-xl px-4 py-3">
                      <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-violet-900 border border-violet-700 flex items-center justify-center text-xs font-bold text-violet-300">J{step.day}</div>
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getStepBadgeClass(step.action_type)}`}>
                            {step.action_type?.toUpperCase()}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 mt-1">{step.rationale}</p>
                      </div>
                    </div>
                  ))}
                </div>

                {osmosContent && (
                  <div className="space-y-3 mt-4">
                    <h4 className="text-sm font-bold text-white">✍️ Contenus LinkedIn personnalisés</h4>
                    {[
                      { label: "📢 Post LinkedIn", key: "post_text", borderCls: "border-violet-900", textCls: "text-violet-300" },
                      { label: "💬 Commentaire court", key: "short_comment", borderCls: "border-blue-900", textCls: "text-blue-300" },
                      { label: "📩 Message Direct (DM)", key: "direct_message", borderCls: "border-emerald-900", textCls: "text-emerald-300" },
                    ].map(({ label, key, borderCls, textCls }) => (
                      <div key={key} className={`bg-slate-950 border ${borderCls} rounded-xl p-4`}>
                        <div className={`text-xs font-bold ${textCls} mb-2`}>{label}</div>
                        <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">{osmosContent[key]}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
