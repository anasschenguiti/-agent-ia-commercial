"use client";

import React, { useState, useEffect } from "react";

const BACKEND_URL = "http://localhost:8000";

export default function Home() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [prospects, setProspects] = useState([]);
  const [prospectsPage, setProspectsPage] = useState(1);
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [cityFilter, setCityFilter] = useState("all");
  const prospectsPerPage = 4;
  const [loading, setLoading] = useState(false);
  const [searchKeywords, setSearchKeywords] = useState("Directeur Commercial, Responsable Digital");
  const [searchLocation, setSearchLocation] = useState("Casablanca");
  const [searchCountry, setSearchCountry] = useState("Maroc");
  const [searchIndustry, setSearchIndustry] = useState("Technologies de l'Information");
  const [searchCompanySize, setSearchCompanySize] = useState("11-50");
  const [searchRevenue, setSearchRevenue] = useState("2M - 10M MAD");
  const [searchLimit, setSearchLimit] = useState(5);
  const [scrapingStatus, setScrapingStatus] = useState("");
  
  // State pour le chat
  const [selectedProspect, setSelectedProspect] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  // State pour CRM et Calendriers (Étape 4)
  const [crmSyncStatus, setCrmSyncStatus] = useState("");
  const [availableSlots, setAvailableSlots] = useState([]);
  const [bookingStatus, setBookingStatus] = useState("");

  // State pour Relances Automatiques (Étape 5 / Module 9)
  const [simulatedDays, setSimulatedDays] = useState(0);
  const [followupsList, setFollowupsList] = useState([]);
  const [followupLoading, setFollowupLoading] = useState(false);
  const [followupActionStatus, setFollowupActionStatus] = useState("");

  // State pour Templates & Communication (Étape 6)
  const [templatesList, setTemplatesList] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [templateStatus, setTemplateStatus] = useState("");
  const [testRecipient, setTestRecipient] = useState("");

  // State pour Analytics (Étape 6)
  const [analyticsData, setAnalyticsData] = useState(null);

  // State pour l'authentification (Étape 5)
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    if (token) {
      setIsAuthenticated(true);
    }
  }, []);

  const apiFetch = async (url, options = {}) => {
    const token = localStorage.getItem("auth_token");
    const headers = { ...options.headers };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    return fetch(url, { ...options, headers });
  };

  const handleLogin = async (e) => {
    if (e) e.preventDefault();
    setAuthLoading(true);
    setAuthError("");
    try {
      const cleanEmail = (authEmail || "admin@iksatech.com").trim().toLowerCase();
      const cleanPassword = (authPassword || "admin").trim();
      
      const res = await fetch(`${BACKEND_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: cleanEmail, password: cleanPassword })
      });
      if (res.ok) {
        const data = await res.json();
        localStorage.setItem("auth_token", data.access_token);
        setIsAuthenticated(true);
        setAuthPassword("");
      } else {
        const errData = await res.json();
        setAuthError(errData.detail || "Email ou mot de passe incorrect");
      }
    } catch (err) {
      setAuthError("Erreur de connexion avec le serveur backend (http://localhost:8000). Vérifiez que le serveur tourne.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("auth_token");
    setIsAuthenticated(false);
  };

  const handleCrmSync = async (crmType) => {
    if (!selectedProspect) return;
    setCrmSyncStatus(`Synchronisation avec ${crmType}...`);
    try {
      const res = await apiFetch(`${BACKEND_URL}/api/crm/sync/${crmType}/${selectedProspect.id}`, {
        method: "POST"
      });
      if (res.ok) {
        const data = await res.json();
        setCrmSyncStatus(`Succès: ${crmType} synchronisé (${data.status || "complété"})`);
      } else {
        setCrmSyncStatus(`Erreur lors de la synchronisation.`);
      }
    } catch (e) {
      setCrmSyncStatus(`Erreur de connexion.`);
    }
  };

  const loadAvailableSlots = async () => {
    try {
      const dateFrom = new Date().toISOString();
      const dateTo = new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString();
      const res = await apiFetch(`${BACKEND_URL}/api/scheduling/slots?date_from=${dateFrom}&date_to=${dateTo}`);
      if (res.ok) {
        const data = await res.json();
        setAvailableSlots(data.slice(0, 4));
      }
    } catch (e) {
      console.error("Erreur chargement créneaux :", e);
    }
  };

  const handleBookSlot = async (slot) => {
    if (!selectedProspect) return;
    setBookingStatus("Planification en cours...");
    try {
      const res = await apiFetch(`${BACKEND_URL}/api/scheduling/appointments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          summary: `Rdv Commercial - ${selectedProspect.first_name} ${selectedProspect.last_name}`,
          start: slot.start,
          end: slot.end,
          description: `Rdv avec ${selectedProspect.first_name} ${selectedProspect.last_name} (${selectedProspect.company})`
        })
      });
      if (res.ok) {
        setBookingStatus("Rendez-vous planifié avec succès !");
      } else {
        setBookingStatus("Erreur lors de la réservation.");
      }
    } catch (e) {
      setBookingStatus("Erreur de connexion.");
    }
  };

  const loadFollowups = async (days = 0) => {
    setFollowupLoading(true);
    try {
      const res = await apiFetch(`${BACKEND_URL}/api/prospection/followups?simulate_days=${days}`);
      if (res.ok) {
        const data = await res.json();
        setFollowupsList(data);
      }
    } catch (e) {
      console.error("Erreur de chargement des relances :", e);
    } finally {
      setFollowupLoading(false);
    }
  };

  const handleTriggerFollowup = async (prospectId) => {
    setFollowupActionStatus("Déclenchement de la relance...");
    try {
      const res = await apiFetch(`${BACKEND_URL}/api/prospection/followups/trigger/${prospectId}`, {
        method: "POST"
      });
      if (res.ok) {
        const data = await res.json();
        setFollowupActionStatus(`Relance envoyée : "${data.message_sent}"`);
        loadFollowups(simulatedDays);
      } else {
        const errData = await res.json();
        setFollowupActionStatus(`Erreur : ${errData.detail || "impossible de relancer"}`);
      }
    } catch (e) {
      setFollowupActionStatus("Erreur réseau lors de la relance.");
    }
  };

  const loadTemplates = async () => {
    try {
      const res = await apiFetch(`${BACKEND_URL}/api/communication/templates`);
      if (res.ok) {
        const data = await res.json();
        setTemplatesList(data);
        if (data.length > 0 && !selectedTemplate) {
          setSelectedTemplate(data[0]);
        }
      }
    } catch (e) {
      console.error("Erreur de chargement des templates :", e);
    }
  };

  const loadAnalytics = async () => {
    try {
      const res = await apiFetch(`${BACKEND_URL}/api/prospection/analytics`);
      if (res.ok) {
        const data = await res.json();
        setAnalyticsData(data);
      }
    } catch (e) {
      console.error("Erreur de chargement des analytics :", e);
    }
  };

  const handleExportCSV = async () => {
    try {
      const token = localStorage.getItem("auth_token");
      const res = await fetch(`${BACKEND_URL}/api/prospection/export/csv`, {
        headers: token ? { "Authorization": `Bearer ${token}` } : {}
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "prospects_export.csv";
        document.body.appendChild(a);
        a.click();
        a.remove();
      }
    } catch (e) {
      console.error("Erreur d'exportation CSV :", e);
    }
  };

  const handleTestSendTemplate = async (template) => {
    if (!testRecipient) {
      setTemplateStatus("Veuillez saisir un destinataire de test.");
      return;
    }
    setTemplateStatus("Envoi du test en cours...");
    try {
      const res = await apiFetch(`${BACKEND_URL}/api/communication/send-test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channel: template.channel,
          to: testRecipient,
          subject: template.subject || "Message de Test",
          content: template.content
        })
      });
      if (res.ok) {
        setTemplateStatus(`Message de test envoyé avec succès sur le canal ${template.channel} !`);
      } else {
        const errorData = await res.json().catch(() => ({}));
        setTemplateStatus(errorData.detail || "Erreur lors de l'envoi du test.");
      }
    } catch (e) {
      setTemplateStatus("Erreur de connexion : " + e.message);
    }
  };

  useEffect(() => {
    if (activeTab === "followups") {
      loadFollowups(simulatedDays);
    } else if (activeTab === "templates") {
      loadTemplates();
    } else if (activeTab === "dashboard") {
      loadAnalytics();
    }
  }, [activeTab, simulatedDays]);

  // Charger les prospects au démarrage et au changement d'onglet
  useEffect(() => {
    fetchProspects();
  }, [activeTab]);

  const fetchProspects = async () => {
    try {
      const res = await apiFetch(`${BACKEND_URL}/api/prospection/prospects`);
      if (res.ok) {
        const data = await res.json();
        const sorted = data.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
        setProspects(sorted);
        if (sorted.length > 0 && !selectedProspect) {
          setSelectedProspect(sorted[0]);
        }
      }
    } catch (e) {
      console.error("Erreur de chargement des prospects :", e);
    }
  };

  const handleLaunchScraping = async (e) => {
    e.preventDefault();
    setLoading(true);
    setScrapingStatus("🌐 Web Scraping Multi-Sources Réel en cours (Google, LinkedIn, Annuaires B2B, Crawl HTTP)...");
    try {
      const res = await apiFetch(`${BACKEND_URL}/api/prospection/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: {
            keywords: searchKeywords.split(",").map(k => k.trim()),
            location: searchLocation,
            country: searchCountry,
            industry: searchIndustry,
            company_size: searchCompanySize,
            annual_revenue: searchRevenue,
            max_results: parseInt(searchLimit)
          }
        })
      });
      if (res.ok) {
        const data = await res.json();
        await fetchProspects();
        await loadAnalytics();
        setLoading(false);
        setScrapingStatus(`✅ Scraping terminé ! ${data.count || data.prospects?.length || 0} nouveaux prospects créés et affichés ci-dessous.`);
      } else {
        const errData = await res.json().catch(() => ({}));
        setLoading(false);
        setScrapingStatus(`⚠️ Erreur : ${errData.detail || "Échec de la recherche"}`);
      }
    } catch (err) {
      setLoading(false);
      setScrapingStatus("Erreur de connexion avec le serveur backend.");
    }
  };

  const handleResetDatabase = async () => {
    if (!confirm("Voulez-vous vraiment vider tous les prospects de la base de données ?")) return;
    setScrapingStatus("Réinitialisation en cours...");
    try {
      const res = await apiFetch(`${BACKEND_URL}/api/prospection/prospects`, {
        method: "DELETE"
      });
      if (res.ok) {
        setScrapingStatus("Base de données réinitialisée !");
        setProspects([]);
        setSelectedProspect(null);
      } else {
        setScrapingStatus("Erreur lors de la réinitialisation.");
      }
    } catch (e) {
      setScrapingStatus("Erreur de connexion.");
    }
  };

  // Charger l'historique du prospect sélectionné et ses créneaux dispo
  useEffect(() => {
    if (selectedProspect) {
      loadChatHistory(selectedProspect.id);
      loadAvailableSlots();
      setCrmSyncStatus("");
      setBookingStatus("");
    }
  }, [selectedProspect]);

  const loadChatHistory = async (session_id) => {
    try {
      const res = await apiFetch(`${BACKEND_URL}/api/conversation/history/${session_id}`);
      if (res.ok) {
        const data = await res.json();
        setChatMessages(data.messages || []);
      }
    } catch (e) {
      console.error("Erreur de chargement du chat :", e);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || !selectedProspect) return;

    const userMsg = inputMessage;
    setInputMessage("");
    setChatLoading(true);

    // Ajouter localement le message de l'utilisateur immédiatement
    setChatMessages((prev) => [
      ...prev,
      { role: "user", content: userMsg, timestamp: new Date().toISOString() }
    ]);

    try {
      const res = await apiFetch(`${BACKEND_URL}/api/conversation/chat/${selectedProspect.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg })
      });
      if (res.ok) {
        const data = await res.json();
        setChatMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.response, timestamp: new Date().toISOString() }
        ]);
      }
    } catch (err) {
      console.error("Erreur d'envoi du message :", err);
    } finally {
      setChatLoading(false);
    }
  };

  const handleClearHistory = async () => {
    if (!selectedProspect) return;
    try {
      const res = await apiFetch(`${BACKEND_URL}/api/conversation/history/${selectedProspect.id}`, {
        method: "DELETE"
      });
      if (res.ok) {
        setChatMessages([]);
      }
    } catch (e) {
      console.error("Erreur d'effacement de l'historique :", e);
    }
  };

  const getScoreBadgeColor = (score) => {
    if (!score && score !== 0) return "bg-gray-500/20 text-gray-400 border-gray-500/30";
    if (score >= 80) return "bg-rose-500/20 text-rose-300 border-rose-500/30";
    if (score >= 50) return "bg-amber-500/20 text-amber-300 border-amber-500/30";
    return "bg-sky-500/20 text-sky-300 border-sky-500/30";
  };

  const getScoreText = (score) => {
    if (!score && score !== 0) return "Non qualifié";
    if (score >= 80) return "Qualifié (Hot)";
    if (score >= 50) return "Moyen (Warm)";
    return "Froid (Cold)";
  };
  const totalLeads = prospects.length;
  const hotLeads = prospects.filter(p => p.score >= 80).length;
  const avgScore = totalLeads > 0 ? (prospects.reduce((acc, p) => acc + (p.score || 0), 0) / totalLeads).toFixed(1) : 0;
  const contactedLeads = prospects.filter(p => p.status === "contacted" || p.status === "in_progress").length;

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4" style={{ background: "radial-gradient(circle at 50% 0%, #171135 0%, #0a0715 70%, #040308 100%)" }}>
        <div className="w-full max-w-md bg-white/5 border border-white/10 rounded-3xl p-8 shadow-2xl backdrop-blur-md animate-fadeIn">
          <div className="flex flex-col items-center mb-8">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-violet-600 to-fuchsia-600 flex items-center justify-center font-bold text-2xl shadow-lg shadow-violet-500/20 mb-4">
              IK
            </div>
            <h2 className="font-extrabold text-2xl tracking-tight bg-gradient-to-r from-violet-200 to-fuchsia-200 bg-clip-text text-transparent">
              Connexion Portail
            </h2>
            <p className="text-slate-400 text-xs mt-1 text-center">
              Connectez-vous pour accéder au portail Sales AI Agent
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Adresse Email</label>
              <input
                type="email"
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                placeholder="nom@entreprise.com"
                className="w-full bg-slate-950/40 border border-violet-900/40 rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:border-violet-500 text-slate-200 transition"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Mot de passe</label>
              <input
                type="password"
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-slate-950/40 border border-violet-900/40 rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:border-violet-500 text-slate-200 transition"
                required
              />
            </div>

            {authError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/30 text-rose-300 rounded-xl text-xs text-center font-medium animate-fadeIn">
                {authError}
              </div>
            )}

            <button
              type="submit"
              disabled={authLoading}
              className="w-full bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white font-bold py-3.5 px-6 rounded-xl transition shadow-lg shadow-violet-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2 text-sm"
            >
              {authLoading ? (
                <>
                  <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  <span>Authentification...</span>
                </>
              ) : (
                <span>Se connecter</span>
              )}
            </button>
          </form>

          <button
            type="button"
            onClick={() => {
              setAuthEmail("admin@iksatech.com");
              setAuthPassword("admin");
              handleLogin();
            }}
            className="w-full mt-3 bg-violet-950/40 hover:bg-violet-900/60 text-violet-300 border border-violet-800/60 py-2.5 px-4 rounded-xl text-xs font-semibold transition"
          >
            ⚡ Connexion Rapide Démo (admin@iksatech.com)
          </button>

          <div className="mt-6 text-center text-[10px] text-slate-500 leading-normal">
            <p>Identifiants de test : <span className="font-semibold text-slate-400 text-center block">admin@iksatech.com / admin</span></p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden text-slate-100">
      {/* ── SIDEBAR ── */}
      <aside className="w-80 bg-[#0c0822]/90 border-r border-violet-950/40 p-6 flex flex-col justify-between">
        <div>
          {/* Logo */}
          <div className="flex items-center space-x-3 mb-10">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-violet-600 to-fuchsia-600 flex items-center justify-center font-bold text-lg shadow-lg shadow-violet-500/20">
              IK
            </div>
            <div>
              <h2 className="font-bold text-lg leading-tight">Sales AI Agent</h2>
              <span className="text-xs text-violet-400 font-medium">IKSATECH Portal</span>
            </div>
          </div>

          {/* Navigation */}
          <nav className="space-y-2">
            <button
              onClick={() => setActiveTab("dashboard")}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition text-sm font-medium ${
                activeTab === "dashboard"
                  ? "bg-violet-600/30 text-violet-300 border-l-4 border-violet-500"
                  : "text-slate-400 hover:bg-violet-950/20 hover:text-slate-200"
              }`}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2v-4zM14 16a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2v-4z" /></svg>
              <span>Tableau de bord</span>
            </button>

            <button
              onClick={() => setActiveTab("prospection")}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition text-sm font-medium ${
                activeTab === "prospection"
                  ? "bg-violet-600/30 text-violet-300 border-l-4 border-violet-500"
                  : "text-slate-400 hover:bg-violet-950/20 hover:text-slate-200"
              }`}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
              <span>Prospection IA (Scraping)</span>
            </button>

            <button
              onClick={() => setActiveTab("leads")}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition text-sm font-medium ${
                activeTab === "leads"
                  ? "bg-violet-600/30 text-violet-300 border-l-4 border-violet-500"
                  : "text-slate-400 hover:bg-violet-950/20 hover:text-slate-200"
              }`}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" /></svg>
              <span>Base Leads & Qualification</span>
            </button>

            <button
              onClick={() => setActiveTab("chat")}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition text-sm font-medium ${
                activeTab === "chat"
                  ? "bg-violet-600/30 text-violet-300 border-l-4 border-violet-500"
                  : "text-slate-400 hover:bg-violet-950/20 hover:text-slate-200"
              }`}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>
              <span>Agent Conversationnel</span>
            </button>

            <button
              onClick={() => setActiveTab("followups")}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition text-sm font-medium ${
                activeTab === "followups"
                  ? "bg-violet-600/30 text-violet-300 border-l-4 border-violet-500"
                  : "text-slate-400 hover:bg-violet-950/20 hover:text-slate-200"
              }`}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              <span>Relances & Campagnes</span>
            </button>

            <button
              onClick={() => setActiveTab("templates")}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition text-sm font-medium ${
                activeTab === "templates"
                  ? "bg-violet-600/30 text-violet-300 border-l-4 border-violet-500"
                  : "text-slate-400 hover:bg-violet-950/20 hover:text-slate-200"
              }`}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
              <span>Templates & Canaux</span>
            </button>
          </nav>
        </div>
        
        <div className="pt-4 border-t border-violet-950/40">
          <button
            onClick={handleLogout}
            className="w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition text-sm font-semibold text-rose-400 hover:bg-rose-950/20 hover:text-rose-300"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
            <span>Déconnexion</span>
          </button>
        </div>
      </aside>

      {/* ── MAIN CONTENT AREA ── */}
      <main className="flex-1 bg-[#05040a]/70 backdrop-blur-3xl overflow-y-auto p-10 flex flex-col justify-between">
        
        {/* Header */}
        <header className="flex justify-between items-center mb-8 border-b border-violet-950/30 pb-4">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-violet-200 to-fuchsia-200 bg-clip-text text-transparent">
              {activeTab === "dashboard" && "Tableau de Bord Commercial"}
              {activeTab === "prospection" && "Prospection Intelligente IA"}
              {activeTab === "leads" && "Base de Données Prospects"}
              {activeTab === "chat" && "Dialogue en temps réel avec l'Agent IA"}
              {activeTab === "followups" && "Campagnes de Relances Automatiques"}
              {activeTab === "templates" && "Gestion des Templates & Canaux"}
            </h1>
            <p className="text-slate-400 text-sm">Portail administrateur de gestion des campagnes et leads</p>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-xs font-semibold px-3 py-1 bg-violet-600/20 text-violet-300 rounded-full border border-violet-600/40">
              Admin Commercial
            </span>
          </div>
        </header>

        {/* ── TAB CONTENTS ── */}
        <div className="flex-1">
          
          {/* TAB 1: DASHBOARD */}
          {activeTab === "dashboard" && (
            <div className="space-y-8 animate-fadeIn">
              {/* KPI Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                
                <div className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-md hover:border-violet-500/40 transition-all">
                  <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider block mb-2">Total Prospects</span>
                  <div className="flex justify-between items-end">
                    <span className="text-4xl font-extrabold">{totalLeads}</span>
                    <span className="text-xs text-emerald-400 flex items-center font-medium bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">+18% ce mois</span>
                  </div>
                </div>

                <div className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-md hover:border-violet-500/40 transition-all">
                  <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider block mb-2">Prospects Qualifiés (Hot)</span>
                  <div className="flex justify-between items-end">
                    <span className="text-4xl font-extrabold text-rose-400">{hotLeads}</span>
                    <span className="text-xs text-rose-300 bg-rose-500/10 px-2 py-0.5 rounded-full border border-rose-500/20">
                      {totalLeads > 0 ? ((hotLeads / totalLeads) * 100).toFixed(0) : 0}% du total
                    </span>
                  </div>
                </div>

                <div className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-md hover:border-violet-500/40 transition-all">
                  <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider block mb-2">Score Moyen IA</span>
                  <div className="flex justify-between items-end">
                    <span className="text-4xl font-extrabold text-violet-400">{avgScore} / 100</span>
                    <span className="text-xs text-violet-300 bg-violet-500/10 px-2 py-0.5 rounded-full border border-violet-500/20">Algorithme V2</span>
                  </div>
                </div>

                <div className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-md hover:border-violet-500/40 transition-all">
                  <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider block mb-2">Relances Activement Planifiées</span>
                  <div className="flex justify-between items-end">
                    <span className="text-4xl font-extrabold text-amber-400">{contactedLeads}</span>
                    <span className="text-xs text-amber-300 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">Automatique</span>
                  </div>
                </div>
              </div>

              {/* Graphical Representation */}
              <div className="bg-white/5 border border-white/10 rounded-2xl p-8 backdrop-blur-md">
                <h3 className="font-bold text-lg mb-6">Répartition par Score & Intérêt</h3>
                <div className="space-y-6">
                  <div>
                    <div className="flex justify-between text-sm mb-2 font-medium">
                      <span>Prospects Hot (Score &ge; 80) — Prioritaires pour Appel</span>
                      <span className="text-rose-300 font-bold">{hotLeads} leads</span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-3 overflow-hidden">
                      <div className="bg-gradient-to-r from-rose-500 to-red-500 h-full rounded-full transition-all duration-500" style={{ width: `${totalLeads > 0 ? (hotLeads/totalLeads)*100 : 0}%` }}></div>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-sm mb-2 font-medium">
                      <span>Prospects Warm (Score 50 - 79) — À relancer / Écouter</span>
                      <span className="text-amber-300 font-bold">{prospects.filter(p => p.score >= 50 && p.score < 80).length} leads</span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-3 overflow-hidden">
                      <div className="bg-gradient-to-r from-amber-500 to-yellow-400 h-full rounded-full transition-all duration-500" style={{ width: `${totalLeads > 0 ? (prospects.filter(p => p.score >= 50 && p.score < 80).length/totalLeads)*100 : 0}%` }}></div>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-sm mb-2 font-medium">
                      <span>Prospects Cold (Score &lt; 50) — Archives / Froid</span>
                      <span className="text-sky-300 font-bold">{prospects.filter(p => p.score < 50).length} leads</span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-3 overflow-hidden">
                      <div className="bg-gradient-to-r from-sky-500 to-indigo-500 h-full rounded-full transition-all duration-500" style={{ width: `${totalLeads > 0 ? (prospects.filter(p => p.score < 50).length/totalLeads)*100 : 0}%` }}></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: PROSPECTION */}
          {activeTab === "prospection" && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-fadeIn">
              {/* Formulaire de scraping */}
              <div className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-md h-fit">
                <h3 className="font-bold text-lg mb-6">Paramètres de Recherche IA</h3>
                <form onSubmit={handleLaunchScraping} className="space-y-4">
                   <div>
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                      Mots-clés / Intitulés de poste
                    </label>
                    <input
                      type="text"
                      list="keywords-list"
                      value={searchKeywords}
                      onChange={(e) => setSearchKeywords(e.target.value)}
                      placeholder="Tapez pour voir les suggestions..."
                      className="w-full bg-slate-950/40 border border-violet-900/40 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-violet-500 text-slate-200"
                      required
                    />
                    <datalist id="keywords-list">
                      <option value="Directeur Commercial" />
                      <option value="Responsable Digital & E-Commerce" />
                      <option value="CEO & Co-Fondateur" />
                      <option value="Directeur Général (DG)" />
                      <option value="Responsable Ressources Humaines (DRH)" />
                      <option value="Directeur Technique & CTO" />
                      <option value="Directeur Financier & DAF (CFO)" />
                      <option value="Head of Sales & Business Development" />
                      <option value="Directeur Marketing & Communication" />
                      <option value="Directeur Achats & Sourcing" />
                      <option value="Directeur Logistique & Supply Chain" />
                      <option value="Directeur d'Usine & Production" />
                      <option value="Directeur DSI & IT Manager" />
                      <option value="Directeur de Filiale & Regional Manager" />
                      <option value="Responsable Service Client (CSM)" />
                      <option value="SaaS B2B & Éditeur de Logiciels" />
                      <option value="Services IT & Digital Consulting" />
                      <option value="Industrie & Transformation Digitale" />
                      <option value="Banque, Assurance & Finance" />
                      <option value="Automobile & Transport B2B" />
                    </datalist>

                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {["Directeur Commercial", "Responsable Digital", "CEO", "DG", "DRH", "CTO", "CFO", "Head of Sales", "Dir. Marketing", "SaaS B2B", "PME", "Industrie"].map(tag => (
                        <button
                          key={tag}
                          type="button"
                          onClick={() => setSearchKeywords(prev => prev ? `${prev}, ${tag}` : tag)}
                          className="text-[10px] px-2 py-0.5 rounded-full bg-violet-950/40 border border-violet-800/40 text-violet-300 hover:bg-violet-700/30 hover:border-violet-500/50 transition font-medium"
                        >
                          + {tag}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                      Localisation (Villes du Maroc)
                    </label>
                    <input
                      type="text"
                      list="morocco-cities-list"
                      value={searchLocation}
                      onChange={(e) => setSearchLocation(e.target.value)}
                      placeholder="Tapez pour voir les villes du Maroc..."
                      className="w-full bg-slate-950/40 border border-violet-900/40 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-violet-500 text-slate-200"
                      required
                    />
                    <datalist id="morocco-cities-list">
                      <option value="Casablanca" />
                      <option value="Rabat" />
                      <option value="Tanger" />
                      <option value="Marrakech" />
                      <option value="Fès" />
                      <option value="Agadir" />
                      <option value="Meknès" />
                      <option value="Oujda" />
                      <option value="Kénitra" />
                      <option value="Tétouan" />
                      <option value="Safi" />
                      <option value="El Jadida" />
                      <option value="Nador" />
                      <option value="Béni Mellal" />
                      <option value="Mohammedia" />
                      <option value="Témara" />
                      <option value="Khouribga" />
                      <option value="Settat" />
                      <option value="Laâyoune" />
                      <option value="Dakhla" />
                      <option value="Taza" />
                      <option value="Essaouira" />
                      <option value="Al Hoceïma" />
                      <option value="Larache" />
                      <option value="Guelmim" />
                      <option value="Berrechid" />
                      <option value="Tiznit" />
                      <option value="Ouarzazate" />
                    </datalist>

                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {["Casablanca", "Rabat", "Tanger", "Marrakech", "Fès", "Agadir", "Meknès", "Oujda", "Kénitra", "El Jadida", "Laâyoune", "Dakhla"].map(city => (
                        <button
                          key={city}
                          type="button"
                          onClick={() => setSearchLocation(city)}
                          className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800/60 border border-slate-700/40 text-slate-300 hover:bg-slate-700/40 hover:border-slate-500/50 transition font-medium"
                        >
                          {city}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Nombre maximum de leads ({searchLimit})</label>
                    <input
                      type="range"
                      min="1"
                      max="10"
                      value={searchLimit}
                      onChange={(e) => setSearchLimit(e.target.value)}
                      className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-violet-500"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white font-bold py-3 px-6 rounded-xl transition shadow-lg shadow-violet-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2 text-sm"
                  >
                    {loading ? (
                      <>
                        <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                        <span>Recherche en cours...</span>
                      </>
                    ) : (
                      <span>Lancer la recherche IA</span>
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={handleResetDatabase}
                    className="w-full mt-3 bg-rose-950/20 hover:bg-rose-900/30 text-rose-300 hover:text-rose-200 border border-rose-900/40 hover:border-rose-500/40 py-2.5 px-6 rounded-xl transition text-xs font-semibold text-center block"
                  >
                    Réinitialiser la Base (Vider)
                  </button>
                </form>

                {scrapingStatus && (
                  <div className="mt-6 p-4 rounded-xl bg-violet-950/30 border border-violet-500/30 text-xs text-violet-300">
                    {scrapingStatus}
                  </div>
                )}
              </div>

              {/* Récemment découverts — Pagination 4 par 4 avec filtrage par catégorie */}
              <div className="lg:col-span-2 bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-md flex flex-col justify-between">
                <div>
                  <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
                    <div>
                      <h3 className="font-bold text-lg">Derniers prospects découverts</h3>
                      <p className="text-xs text-slate-400">Filtrage combiné Catégorie + Ville & 4 par page</p>
                    </div>
                    <span className="text-xs text-violet-400 font-bold bg-violet-950/60 border border-violet-800/60 px-3 py-1 rounded-full">
                      {(() => {
                        const filtered = prospects.filter((p) => {
                          if (cityFilter !== "all") {
                            const loc = (p.location || "").toLowerCase();
                            if (!loc.includes(cityFilter.toLowerCase())) return false;
                          }
                          if (categoryFilter === "all") return true;
                          if (categoryFilter === "hot") return (p.score || 0) >= 80;
                          const title = (p.job_title || "").toLowerCase();
                          if (categoryFilter === "direction") return title.includes("ceo") || title.includes("dg") || title.includes("directeur général") || title.includes("fondateur") || title.includes("gérant") || title.includes("president");
                          if (categoryFilter === "sales") return title.includes("commercial") || title.includes("sales") || title.includes("vente") || title.includes("business dev") || title.includes("compte");
                          if (categoryFilter === "digital") return title.includes("digital") || title.includes("marketing") || title.includes("communication") || title.includes("growth") || title.includes("e-commerce");
                          if (categoryFilter === "tech") return title.includes("cto") || title.includes("technique") || title.includes("dsi") || title.includes("dev") || title.includes("it") || title.includes("système");
                          if (categoryFilter === "rh_finance") return title.includes("rh") || title.includes("ressources humaines") || title.includes("cfo") || title.includes("financier") || title.includes("daf") || title.includes("achats") || title.includes("logistique");
                          return true;
                        });
                        return `${filtered.length} / ${prospects.length} prospects`;
                      })()}
                    </span>
                  </div>

                  {/* Listes déroulantes de filtrage par Catégorie et par Ville (mises à jour auto) */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6 p-4 rounded-xl bg-slate-950/50 border border-violet-950/60 shadow-inner">
                    <div>
                      <label className="block text-xs font-semibold text-violet-300 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                        <span>📂</span>
                        <span>Filtrer par Catégorie / Poste</span>
                      </label>
                      <select
                        value={categoryFilter}
                        onChange={(e) => {
                          setCategoryFilter(e.target.value);
                          setProspectsPage(1);
                        }}
                        className="w-full bg-slate-900 border border-violet-800/60 text-slate-200 rounded-xl px-4 py-2.5 text-xs font-semibold focus:outline-none focus:border-violet-400 cursor-pointer shadow-sm"
                      >
                        <option value="all">🌐 Toutes les catégories ({prospects.length})</option>
                        <option value="hot">🔥 Haute Priorité — Score 80+</option>
                        <option value="direction">⚡ Direction, CEO & DG</option>
                        <option value="sales">💼 Commercial, Sales & Business Dev</option>
                        <option value="digital">📱 Digital, Marketing & Com</option>
                        <option value="tech">💻 IT, CTO & DSI</option>
                        <option value="rh_finance">📊 RH, Finance, DAF & Logistique</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-fuchsia-300 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                        <span>📍</span>
                        <span>Filtrer par Ville (Mise à jour auto)</span>
                      </label>
                      <select
                        value={cityFilter}
                        onChange={(e) => {
                          setCityFilter(e.target.value);
                          setProspectsPage(1);
                        }}
                        className="w-full bg-slate-900 border border-fuchsia-800/60 text-slate-200 rounded-xl px-4 py-2.5 text-xs font-semibold focus:outline-none focus:border-fuchsia-400 cursor-pointer shadow-sm"
                      >
                        <option value="all">📍 Toutes les villes ({prospects.length})</option>
                        {(() => {
                          const detectedCities = Array.from(
                            new Set(
                              prospects
                                .map((p) => (p.location ? p.location.split(",")[0].trim() : null))
                                .filter(Boolean)
                            )
                          ).sort();

                          return detectedCities.map((city) => {
                            const count = prospects.filter((p) => (p.location || "").toLowerCase().includes(city.toLowerCase())).length;
                            return (
                              <option key={city} value={city}>
                                📍 {city} ({count} prospect{count > 1 ? "s" : ""})
                              </option>
                            );
                          });
                        })()}
                      </select>
                    </div>
                  </div>

                  {prospects.length === 0 ? (
                    <div className="text-center py-16 text-slate-500">
                      <p className="text-sm mb-2 font-semibold">Aucun prospect disponible pour le moment.</p>
                      <p className="text-xs">Renseignez vos mots-clés et lancez la recherche pour ajouter des prospects.</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {(() => {
                        const filtered = prospects.filter((p) => {
                          if (cityFilter !== "all") {
                            const loc = (p.location || "").toLowerCase();
                            if (!loc.includes(cityFilter.toLowerCase())) return false;
                          }
                          if (categoryFilter === "all") return true;
                          if (categoryFilter === "hot") return (p.score || 0) >= 80;
                          const title = (p.job_title || "").toLowerCase();
                          if (categoryFilter === "direction") return title.includes("ceo") || title.includes("dg") || title.includes("directeur général") || title.includes("fondateur") || title.includes("gérant") || title.includes("president");
                          if (categoryFilter === "sales") return title.includes("commercial") || title.includes("sales") || title.includes("vente") || title.includes("business dev") || title.includes("compte");
                          if (categoryFilter === "digital") return title.includes("digital") || title.includes("marketing") || title.includes("communication") || title.includes("growth") || title.includes("e-commerce");
                          if (categoryFilter === "tech") return title.includes("cto") || title.includes("technique") || title.includes("dsi") || title.includes("dev") || title.includes("it") || title.includes("système");
                          if (categoryFilter === "rh_finance") return title.includes("rh") || title.includes("ressources humaines") || title.includes("cfo") || title.includes("financier") || title.includes("daf") || title.includes("achats") || title.includes("logistique");
                          return true;
                        });

                        if (filtered.length === 0) {
                          return (
                            <div className="text-center py-12 text-slate-400">
                              <p className="text-sm font-semibold mb-1">Aucun prospect ne correspond à cette combinaison de filtres.</p>
                              <p className="text-xs text-slate-500">Essayez de sélectionner une autre ville ou d'autre catégorie.</p>
                            </div>
                          );
                        }

                        const totalPages = Math.max(1, Math.ceil(filtered.length / prospectsPerPage));
                        const currentPage = Math.min(prospectsPage, totalPages);
                        const pageProspects = filtered.slice((currentPage - 1) * prospectsPerPage, currentPage * prospectsPerPage);

                        return pageProspects.map((p, index) => (
                          <div key={p.id} className="bg-slate-950/40 border border-violet-950/40 rounded-xl p-5 flex justify-between items-center hover:border-violet-500/40 transition shadow-sm">
                            <div>
                              <div className="flex items-center space-x-2">
                                <h4 className="font-bold text-base text-slate-200">{p.first_name} {p.last_name}</h4>
                                {(currentPage - 1) * prospectsPerPage + index < 3 && (
                                  <span className="text-[9px] uppercase font-extrabold px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800">
                                    Recent
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-slate-400 font-medium mb-2">{p.job_title} chez <span className="text-violet-400 font-bold">{p.company}</span></p>
                              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 mt-2">
                                <span className="flex items-center space-x-1 text-slate-300 font-medium">
                                  <svg className="w-3.5 h-3.5 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                                  <span>{p.location}</span>
                                </span>
                                {p.email && (
                                  <span className="flex items-center space-x-1">
                                    <svg className="w-3.5 h-3.5 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
                                    <span>{p.email}</span>
                                  </span>
                                )}
                                {p.phone && (
                                  <span className="flex items-center space-x-1 text-slate-400">
                                    <span>📞</span>
                                    <span>{p.phone}</span>
                                  </span>
                                )}
                                {p.annual_revenue && (
                                  <span className="px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800/80 text-[10px] font-bold">
                                    💰 CA: {p.annual_revenue}
                                  </span>
                                )}
                                {p.company_size && (
                                  <span className="px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-800/80 text-[10px] font-bold">
                                    👥 {p.company_size}
                                  </span>
                                )}
                                {p.technologies && (
                                  <span className="px-2 py-0.5 rounded bg-violet-950/80 text-violet-300 border border-violet-800/80 text-[10px] font-semibold">
                                    ⚡ {p.technologies}
                                  </span>
                                )}
                                {p.linkedin_url && (
                                  <a
                                    href={p.linkedin_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="flex items-center space-x-1 px-2 py-0.5 rounded bg-sky-950/80 text-sky-300 border border-sky-800/80 hover:bg-sky-900 transition text-[10px] font-bold"
                                  >
                                    <span>🔗 Profil LinkedIn</span>
                                  </a>
                                )}
                                {p.website && (
                                  <a
                                    href={p.website}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="flex items-center space-x-1 px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-700 hover:bg-slate-800 transition text-[10px] font-medium"
                                  >
                                    <span>🌐 Site Web</span>
                                  </a>
                                )}
                              </div>
                            </div>

                            <div className="flex flex-col items-end space-y-2">
                              <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full border ${getScoreBadgeColor(p.score)}`}>
                                Score: {p.score || 0}
                              </span>
                              <button
                                onClick={() => {
                                  setSelectedProspect(p);
                                  setActiveTab("chat");
                                }}
                                className="bg-violet-600 hover:bg-violet-500 text-white font-semibold text-xs py-1.5 px-3 rounded-lg transition shadow"
                              >
                                Parler avec
                              </button>
                            </div>
                          </div>
                        ));
                      })()}
                    </div>
                  )}
                </div>

                {/* Controls Pagination 4 par 4 dynamique selon filtre combiné */}
                {prospects.length > 0 && (
                  <div className="flex items-center justify-between mt-6 pt-4 border-t border-violet-950/40">
                    {(() => {
                      const filtered = prospects.filter((p) => {
                        if (cityFilter !== "all") {
                          const loc = (p.location || "").toLowerCase();
                          if (!loc.includes(cityFilter.toLowerCase())) return false;
                        }
                        if (categoryFilter === "all") return true;
                        if (categoryFilter === "hot") return (p.score || 0) >= 80;
                        const title = (p.job_title || "").toLowerCase();
                        if (categoryFilter === "direction") return title.includes("ceo") || title.includes("dg") || title.includes("directeur général") || title.includes("fondateur") || title.includes("gérant") || title.includes("president");
                        if (categoryFilter === "sales") return title.includes("commercial") || title.includes("sales") || title.includes("vente") || title.includes("business dev") || title.includes("compte");
                        if (categoryFilter === "digital") return title.includes("digital") || title.includes("marketing") || title.includes("communication") || title.includes("growth") || title.includes("e-commerce");
                        if (categoryFilter === "tech") return title.includes("cto") || title.includes("technique") || title.includes("dsi") || title.includes("dev") || title.includes("it") || title.includes("système");
                        if (categoryFilter === "rh_finance") return title.includes("rh") || title.includes("ressources humaines") || title.includes("cfo") || title.includes("financier") || title.includes("daf") || title.includes("achats") || title.includes("logistique");
                        return true;
                      });
                      const totalPages = Math.max(1, Math.ceil(filtered.length / prospectsPerPage));
                      const currentPage = Math.min(prospectsPage, totalPages);

                      return (
                        <>
                          <button
                            type="button"
                            onClick={() => setProspectsPage((p) => Math.max(1, p - 1))}
                            disabled={currentPage === 1}
                            className="px-4 py-2 rounded-xl bg-violet-950/50 border border-violet-800/50 text-violet-300 hover:bg-violet-900/60 disabled:opacity-30 disabled:cursor-not-allowed text-xs font-bold transition"
                          >
                            ← Précédent
                          </button>

                          <span className="text-xs text-slate-400 font-medium">
                            Page <strong className="text-white font-bold">{currentPage}</strong> sur{" "}
                            <strong className="text-white font-bold">{totalPages}</strong>
                          </span>

                          <button
                            type="button"
                            onClick={() => setProspectsPage((p) => Math.min(totalPages, p + 1))}
                            disabled={currentPage >= totalPages}
                            className="px-4 py-2 rounded-xl bg-violet-950/50 border border-violet-800/50 text-violet-300 hover:bg-violet-900/60 disabled:opacity-30 disabled:cursor-not-allowed text-xs font-bold transition"
                          >
                            Suivant →
                          </button>
                        </>
                      );
                    })()}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: LEADS & SCORING */}
          {activeTab === "leads" && (
            <div className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-md animate-fadeIn">
              <div className="flex justify-between items-center mb-6">
                <h3 className="font-bold text-lg">Base complète des prospects qualifiés</h3>
                <button
                  onClick={handleExportCSV}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2 px-4 rounded-xl text-xs flex items-center space-x-2 transition shadow-lg shadow-emerald-500/20"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                  <span>Exporter en CSV</span>
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-violet-950/40 text-slate-400 font-semibold text-xs uppercase tracking-wider">
                      <th className="py-4 px-6">Prospect</th>
                      <th className="py-4 px-6">Poste / Entreprise</th>
                      <th className="py-4 px-6">Coordonnées</th>
                      <th className="py-4 px-6">Ville</th>
                      <th className="py-4 px-6">Qualification</th>
                      <th className="py-4 px-6 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-violet-950/20">
                    {prospects.map((p) => (
                      <tr key={p.id} className="hover:bg-violet-950/10 transition">
                        <td className="py-4 px-6 font-bold text-slate-200">
                          {p.first_name} {p.last_name}
                        </td>
                        <td className="py-4 px-6">
                          <div className="font-medium text-slate-300">{p.job_title || "N/C"}</div>
                          <div className="text-xs text-violet-400">{p.company || "N/C"}</div>
                        </td>
                        <td className="py-4 px-6 text-xs space-y-1">
                          {p.email && <div className="text-slate-300 font-medium">{p.email}</div>}
                          {p.phone && <div className="text-slate-400 font-mono text-[11px]">{p.phone}</div>}
                          {p.linkedin_url && (
                            <a
                              href={p.linkedin_url}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center space-x-1 text-sky-400 hover:text-sky-300 font-bold text-[11px] hover:underline mt-0.5"
                            >
                              <span>🔗 Profil LinkedIn</span>
                            </a>
                          )}
                        </td>
                        <td className="py-4 px-6 text-slate-400">{p.location || "N/C"}</td>
                        <td className="py-4 px-6">
                          <div className="flex items-center space-x-2">
                            <span className={`w-2 h-2 rounded-full inline-block ${
                              p.score >= 80 ? "bg-rose-500" : p.score >= 50 ? "bg-amber-500" : "bg-sky-500"
                            }`}></span>
                            <span className="font-semibold text-xs">{getScoreText(p.score)} ({p.score || 0})</span>
                          </div>
                        </td>
                        <td className="py-4 px-6 text-right">
                          <button
                            onClick={() => {
                              setSelectedProspect(p);
                              setActiveTab("chat");
                            }}
                            className="bg-violet-600/20 hover:bg-violet-600 text-violet-300 hover:text-white font-bold py-1.5 px-3 rounded-lg border border-violet-600/30 transition text-xs"
                          >
                            Engager chat
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 4: CHAT */}
          {activeTab === "chat" && (
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8 h-[600px] border border-white/10 rounded-2xl overflow-hidden backdrop-blur-md animate-fadeIn">
              
              {/* Liste de selection de prospects */}
              <div className="bg-[#0c0822]/40 border-r border-violet-950/40 p-4 overflow-y-auto flex flex-col">
                <h3 className="font-bold text-sm text-slate-400 uppercase tracking-wider mb-4 px-2">Liste de discussion</h3>
                <div className="space-y-2 flex-1">
                  {prospects.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setSelectedProspect(p)}
                      className={`w-full text-left p-3 rounded-xl transition flex justify-between items-center ${
                        selectedProspect?.id === p.id
                          ? "bg-violet-600/30 border border-violet-500/30"
                          : "hover:bg-violet-950/20 border border-transparent"
                      }`}
                    >
                      <div>
                        <div className="font-bold text-slate-200 text-sm">{p.first_name} {p.last_name}</div>
                        <div className="text-xs text-slate-400">{p.company}</div>
                      </div>
                      <span className={`w-2.5 h-2.5 rounded-full ${
                        p.score >= 80 ? "bg-rose-500" : p.score >= 50 ? "bg-amber-500" : "bg-sky-500"
                      }`}></span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Chat messages */}
              <div className="lg:col-span-2 flex flex-col justify-between bg-slate-950/30">
                {selectedProspect ? (
                  <>
                    {/* Top chat bar */}
                    <div className="p-4 border-b border-violet-950/40 bg-[#0c0822]/40 flex justify-between items-center">
                      <div>
                        <h4 className="font-bold text-slate-200">{selectedProspect.first_name} {selectedProspect.last_name}</h4>
                        <p className="text-xs text-slate-400">Session ID: {selectedProspect.id}</p>
                      </div>
                      <button
                        onClick={handleClearHistory}
                        className="text-xs text-rose-300 hover:text-rose-400 font-semibold px-2 py-1 rounded bg-rose-900/10 border border-rose-500/20 transition"
                      >
                        Vider l'historique
                      </button>
                    </div>

                    {/* Messages Body */}
                    <div className="flex-1 p-6 overflow-y-auto space-y-4">
                      {chatMessages.length === 0 ? (
                        <div className="text-center text-slate-500 text-xs py-12">
                          Débutez la discussion. Envoyez un message ou dites bonjour.
                        </div>
                      ) : (
                        chatMessages.map((msg, index) => (
                          <div
                            key={index}
                            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                          >
                            <div
                              className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                                msg.role === "user"
                                  ? "bg-violet-600 text-white rounded-br-none"
                                  : "bg-slate-800 text-slate-200 border border-slate-700/50 rounded-bl-none"
                              }`}
                            >
                              <p>{msg.content}</p>
                            </div>
                          </div>
                        ))
                      )}
                      
                      {chatLoading && (
                        <div className="flex justify-start">
                          <div className="bg-slate-800 border border-slate-700/50 rounded-2xl rounded-bl-none px-4 py-3 text-sm flex items-center space-x-1.5">
                            <span className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                            <span className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                            <span className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Chat Input */}
                    <form onSubmit={handleSendMessage} className="p-4 border-t border-violet-950/40 bg-[#0c0822]/40 flex space-x-2">
                      <input
                        type="text"
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        placeholder="Écrivez votre message à l'agent IA..."
                        className="flex-1 bg-slate-950/60 border border-violet-900/40 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-violet-500 text-slate-200"
                        required
                      />
                      <button
                        type="submit"
                        disabled={chatLoading}
                        className="bg-violet-600 hover:bg-violet-500 text-white font-bold px-5 py-3 rounded-xl transition text-sm flex items-center"
                      >
                        Envoyer
                      </button>
                    </form>
                  </>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-slate-500 text-sm">
                    Sélectionnez un prospect sur la gauche pour commencer la discussion.
                  </div>
                )}
              </div>

              {/* Prospect Details */}
              <div className="bg-[#0c0822]/40 p-6 flex flex-col space-y-6 overflow-y-auto">
                {selectedProspect ? (
                  <>
                    <h3 className="font-bold text-sm text-slate-400 uppercase tracking-wider mb-2">Fiche Prospect</h3>
                    
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500">Nom & Prénom</span>
                      <div className="font-bold text-slate-200 text-lg leading-tight mt-0.5">{selectedProspect.first_name} {selectedProspect.last_name}</div>
                    </div>

                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500">Poste & Entreprise</span>
                      <div className="font-semibold text-slate-300 text-sm mt-0.5">{selectedProspect.job_title}</div>
                      <div className="text-violet-400 text-xs font-bold">{selectedProspect.company}</div>
                    </div>

                    <div className="bg-slate-950/30 border border-violet-950/40 rounded-xl p-4 space-y-3 text-xs">
                      <div>
                        <span className="text-[10px] uppercase font-bold text-slate-500 block">E-mail</span>
                        <a href={`mailto:${selectedProspect.email}`} className="text-slate-300 hover:underline">{selectedProspect.email || "Non renseigné"}</a>
                      </div>
                      <div>
                        <span className="text-[10px] uppercase font-bold text-slate-500 block">Téléphone</span>
                        <span className="text-slate-300">{selectedProspect.phone || "Non renseigné"}</span>
                      </div>
                      <div>
                        <span className="text-[10px] uppercase font-bold text-slate-500 block">Site Web</span>
                        <a href={selectedProspect.website} target="_blank" className="text-violet-400 hover:underline">{selectedProspect.website || "Non renseigné"}</a>
                      </div>
                      <div>
                        <span className="text-[10px] uppercase font-bold text-slate-500 block">LinkedIn</span>
                        <a href={selectedProspect.linkedin_url} target="_blank" className="text-violet-400 hover:underline">Profil LinkedIn</a>
                      </div>
                    </div>

                    <div className={`rounded-xl p-4 border text-center ${getScoreBadgeColor(selectedProspect.score)}`}>
                      <span className="text-[10px] uppercase font-bold tracking-wider block mb-1">Qualification IA</span>
                      <span className="text-base font-extrabold block">{getScoreText(selectedProspect.score)} ({selectedProspect.score || 0}/100)</span>
                    </div>

                    {/* Actions CRM */}
                    <div className="bg-slate-950/30 border border-violet-950/40 rounded-xl p-4 space-y-3">
                      <span className="text-[10px] uppercase font-bold text-slate-500 block">Actions CRM</span>
                      <div className="grid grid-cols-2 gap-2">
                        <button
                          onClick={() => handleCrmSync("hubspot")}
                          className="bg-violet-600/20 hover:bg-violet-600 text-violet-300 hover:text-white font-bold py-2 px-3 rounded-lg border border-violet-600/30 transition text-[11px]"
                        >
                          Sync HubSpot
                        </button>
                        <button
                          onClick={() => handleCrmSync("odoo")}
                          className="bg-violet-600/20 hover:bg-violet-600 text-violet-300 hover:text-white font-bold py-2 px-3 rounded-lg border border-violet-600/30 transition text-[11px]"
                        >
                          Sync Odoo
                        </button>
                      </div>
                      {crmSyncStatus && (
                        <div className="text-[11px] text-violet-300 bg-violet-950/30 border border-violet-500/20 p-2 rounded-lg text-center animate-pulse">
                          {crmSyncStatus}
                        </div>
                      )}
                    </div>

                    {/* Planification Calendrier */}
                    <div className="bg-slate-950/30 border border-violet-950/40 rounded-xl p-4 space-y-3">
                      <span className="text-[10px] uppercase font-bold text-slate-500 block">Créneaux Disponibles</span>
                      {availableSlots.length === 0 ? (
                        <div className="text-slate-500 text-[11px] text-center py-2">
                          Aucun créneau libre disponible.
                        </div>
                      ) : (
                        <div className="space-y-1.5">
                          {availableSlots.map((slot, index) => {
                            const dateStr = new Date(slot.start).toLocaleString('fr-FR', {
                              weekday: 'short',
                              day: 'numeric',
                              month: 'short',
                              hour: '2-digit',
                              minute: '2-digit'
                            });
                            return (
                              <button
                                key={index}
                                onClick={() => handleBookSlot(slot)}
                                className="w-full text-left bg-slate-950/40 hover:bg-violet-950/40 border border-violet-950/40 hover:border-violet-500/30 rounded-lg p-2.5 text-xs text-slate-300 flex justify-between items-center transition"
                              >
                                <span>{dateStr}</span>
                                <span className="text-[10px] text-violet-400 font-semibold uppercase">Réserver</span>
                              </button>
                            );
                          })}
                        </div>
                      )}
                      {bookingStatus && (
                        <div className="text-[11px] text-emerald-300 bg-emerald-950/30 border border-emerald-500/20 p-2 rounded-lg text-center font-medium">
                          {bookingStatus}
                        </div>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="text-slate-500 text-xs text-center py-12">
                    Aucun prospect sélectionné.
                  </div>
                )}
              </div>

            </div>
          )}

          {/* TAB 5: FOLLOWUPS */}
          {activeTab === "followups" && (
            <div className="space-y-6 animate-fadeIn">
              
              {/* Simulateur temporel */}
              <div className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-md">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                  <div>
                    <h3 className="font-bold text-lg">Simulateur Temporel de Relances</h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Décalez artificiellement le calendrier dans le futur pour tester la détection automatique des relances J3, J7, J15.
                    </p>
                  </div>
                  
                  <div className="flex items-center space-x-2 bg-slate-950/40 p-2 border border-violet-900/30 rounded-xl">
                    <button
                      onClick={() => setSimulatedDays(0)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${simulatedDays === 0 ? "bg-violet-600 text-white" : "text-slate-400 hover:text-slate-200"}`}
                    >
                      Aujourd'hui (J0)
                    </button>
                    <button
                      onClick={() => setSimulatedDays(3)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${simulatedDays === 3 ? "bg-violet-600 text-white" : "text-slate-400 hover:text-slate-200"}`}
                    >
                      +3 jours (Relance 1)
                    </button>
                    <button
                      onClick={() => setSimulatedDays(7)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${simulatedDays === 7 ? "bg-violet-600 text-white" : "text-slate-400 hover:text-slate-200"}`}
                    >
                      +7 jours (Relance 2)
                    </button>
                    <button
                      onClick={() => setSimulatedDays(15)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${simulatedDays === 15 ? "bg-violet-600 text-white" : "text-slate-400 hover:text-slate-200"}`}
                    >
                      +15 jours (Finale)
                    </button>
                  </div>
                </div>
              </div>

              {/* Status Alert */}
              {followupActionStatus && (
                <div className="bg-violet-950/40 border border-violet-500/30 text-violet-300 p-4 rounded-xl text-xs flex justify-between items-center animate-fadeIn">
                  <span>{followupActionStatus}</span>
                  <button onClick={() => setFollowupActionStatus("")} className="text-slate-400 hover:text-slate-200 font-bold">&times;</button>
                </div>
              )}

              {/* Tableau de suivi */}
              <div className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-md">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="font-bold text-base">État des relances par prospect</h3>
                  <span className="text-xs text-violet-400 font-semibold">Date simulée : {new Date(Date.now() + simulatedDays * 24 * 60 * 60 * 1000).toLocaleDateString('fr-FR')}</span>
                </div>

                {followupLoading ? (
                  <div className="text-center py-12">
                    <svg className="animate-spin h-8 w-8 text-violet-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                    <p className="text-slate-400 text-xs">Analyse du pipeline en cours...</p>
                  </div>
                ) : followupsList.length === 0 ? (
                  <div className="text-center py-12 text-slate-500 text-sm">
                    Aucun prospect actif dans le pipeline de relance.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-sm">
                      <thead>
                        <tr className="border-b border-violet-950/40 text-slate-400 font-semibold text-xs uppercase tracking-wider">
                          <th className="py-4 px-6">Prospect</th>
                          <th className="py-4 px-6">Dernier Échange</th>
                          <th className="py-4 px-6">Statut de Relance</th>
                          <th className="py-4 px-6">Action Suggérée</th>
                          <th className="py-4 px-6 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-violet-950/20">
                        {followupsList.map((f) => {
                          const isPending = f.state.endsWith("_PENDING");
                          const getBadgeClass = (state) => {
                            if (state.endsWith("_PENDING")) return "bg-rose-500/20 text-rose-300 border-rose-500/30 animate-pulse";
                            if (state.endsWith("_WAITING")) return "bg-amber-500/20 text-amber-300 border-amber-500/30";
                            if (state === "REPLIED") return "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
                            return "bg-slate-500/20 text-slate-400 border-slate-500/30";
                          };
                          
                          const getFriendlyStateName = (state) => {
                            if (state === "J0_PENDING") return "Premier contact (J0)";
                            if (state === "J3_PENDING") return "J3 : Relance Urgente";
                            if (state === "J3_WAITING") return "J3 : En attente";
                            if (state === "J7_PENDING") return "J7 : Relance Urgente";
                            if (state === "J7_WAITING") return "J7 : En attente";
                            if (state === "J15_PENDING") return "J15 : Relance Finale";
                            if (state === "J15_WAITING") return "J15 : En attente";
                            if (state === "REPLIED") return "Réponse reçue";
                            return "Cycle clos";
                          };

                          return (
                            <tr key={f.prospect_id} className="hover:bg-violet-950/10 transition">
                              <td className="py-4 px-6">
                                <div className="font-bold text-slate-200">{f.first_name} {f.last_name}</div>
                                <div className="text-xs text-violet-400">{f.company}</div>
                              </td>
                              <td className="py-4 px-6 text-slate-300 text-xs">
                                {f.last_message_date ? (
                                  <div>
                                    <div>{new Date(f.last_message_date).toLocaleDateString('fr-FR')}</div>
                                    <div className="text-slate-500 text-[10px]">Il y a {f.elapsed_days} jours (simulé)</div>
                                  </div>
                                ) : (
                                  <span className="text-slate-500 font-medium">Aucun historique</span>
                                )}
                              </td>
                              <td className="py-4 px-6">
                                <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full border ${getBadgeClass(f.state)}`}>
                                  {getFriendlyStateName(f.state)}
                                </span>
                              </td>
                              <td className="py-4 px-6 text-slate-300 text-xs font-medium">
                                {f.action}
                              </td>
                              <td className="py-4 px-6 text-right">
                                <button
                                  onClick={() => handleTriggerFollowup(f.prospect_id)}
                                  disabled={!isPending}
                                  className={`font-bold py-1.5 px-3 rounded-lg text-xs transition border ${
                                    isPending
                                      ? "bg-violet-600 text-white border-violet-500 hover:bg-violet-500"
                                      : "bg-slate-800 text-slate-500 border-slate-700/50 cursor-not-allowed"
                                  }`}
                                >
                                  Relancer
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}

              </div>
            </div>
          )}

          {/* TAB 6: TEMPLATES & CANAUX */}
          {activeTab === "templates" && (
            <div className="space-y-6 animate-fadeIn">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Liste des templates */}
                <div className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-md space-y-4">
                  <h3 className="font-bold text-lg mb-4">Modèles de Messages</h3>
                  <div className="space-y-2">
                    {templatesList.map((tpl) => (
                      <div
                        key={tpl.id}
                        onClick={() => setSelectedTemplate(tpl)}
                        className={`p-4 rounded-xl border cursor-pointer transition ${
                          selectedTemplate?.id === tpl.id
                            ? "bg-violet-600/30 border-violet-500 text-slate-100"
                            : "bg-slate-950/40 border-violet-950/40 text-slate-400 hover:border-violet-500/30"
                        }`}
                      >
                        <div className="flex justify-between items-center mb-1">
                          <span className="font-bold text-sm">{tpl.name}</span>
                          <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-md bg-violet-950/60 border border-violet-800/40 text-violet-300">
                            {tpl.channel}
                          </span>
                        </div>
                        {tpl.subject && (
                          <p className="text-xs text-slate-300 font-medium truncate mb-1">Obj: {tpl.subject}</p>
                        )}
                        <p className="text-xs text-slate-400 line-clamp-2">{tpl.content}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Éditeur et Test */}
                <div className="lg:col-span-2 bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-md space-y-6">
                  {selectedTemplate ? (
                    <>
                      <div className="flex justify-between items-center border-b border-violet-950/40 pb-4">
                        <div>
                          <h3 className="font-bold text-lg">{selectedTemplate.name}</h3>
                          <span className="text-xs text-violet-400 uppercase font-semibold">Canal d'envoi : {selectedTemplate.channel}</span>
                        </div>
                      </div>

                      {/* Aperçu / Formulaire de Test */}
                      <div className="space-y-4">
                        {selectedTemplate.subject && (
                          <div>
                            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Objet du Message</label>
                            <input
                              type="text"
                              value={selectedTemplate.subject}
                              onChange={(e) => setSelectedTemplate({ ...selectedTemplate, subject: e.target.value })}
                              className="w-full bg-slate-950/40 border border-violet-900/40 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-violet-500 text-slate-200"
                            />
                          </div>
                        )}

                        <div>
                          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Contenu du Modèle (Supporte {"{first_name}"}, {"{company}"}, {"{job_title}"})</label>
                          <textarea
                            rows={8}
                            value={selectedTemplate.content}
                            onChange={(e) => setSelectedTemplate({ ...selectedTemplate, content: e.target.value })}
                            className="w-full bg-slate-950/40 border border-violet-900/40 rounded-xl p-4 text-sm focus:outline-none focus:border-violet-500 text-slate-200 font-mono"
                          />
                        </div>

                        {/* Test d'envoi */}
                        <div className="bg-slate-950/40 border border-violet-900/30 rounded-xl p-4 space-y-3">
                          <h4 className="font-bold text-xs uppercase tracking-wider text-slate-300">Tester l'envoi en direct</h4>
                          <div className="flex space-x-3">
                            <input
                              type="text"
                              placeholder={selectedTemplate.channel === "email" ? "test@exemple.com" : "+33612345678"}
                              value={testRecipient}
                              onChange={(e) => setTestRecipient(e.target.value)}
                              className="flex-1 bg-slate-900 border border-violet-900/40 rounded-xl px-4 py-2 text-xs focus:outline-none focus:border-violet-500 text-slate-200"
                            />
                            <button
                              onClick={() => handleTestSendTemplate(selectedTemplate)}
                              className="bg-violet-600 hover:bg-violet-500 text-white font-bold text-xs px-4 py-2 rounded-xl transition shadow-lg shadow-violet-500/20"
                            >
                              Envoyer un message de test
                            </button>
                          </div>
                          {templateStatus && (
                            <p className="text-xs text-violet-300 mt-2 font-medium">{templateStatus}</p>
                          )}
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="text-center py-12 text-slate-500 text-sm">
                      Sélectionnez un modèle à gauche pour le personnaliser ou le tester.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

        </div>

        {/* Footer */}
        <footer className="text-center text-xs text-slate-500 border-t border-violet-950/20 pt-4 mt-8 flex justify-between">
          <span>&copy; 2026 Sales AI Agent — Stage IKSATECH.</span>
          <span>Développé avec Next.js 15 & Tailwind CSS.</span>
        </footer>

      </main>
    </div>
  );
}
