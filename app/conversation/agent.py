"""
Agent IA Commercial d'élite (BDR) basé sur LangGraph.
Gère la recherche RAG, la détection et le traitement des objections (ObjectionNode),
la détection d'intention de rendez-vous (check_meeting_intent),
la réservation de créneaux réels (CalendarClient), la synchro CRM, l'anonymisation PII et le tracing Langfuse.
"""
import logging
import asyncio
import operator
import re
from typing import Any, Dict, List, TypedDict, Annotated

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.conversation.rag import RAGPipeline
from app.conversation.memory import ConversationMemory
from app.conversation.objection_handler import ObjectionHandler
from app.scheduling.calendar_client import CalendarClient
from app.crm.hubspot_adapter import HubSpotAdapter
from app.crm.odoo_adapter import OdooAdapter
from app.shared.pii_redactor import pii_redactor
from app.shared.config import settings

logger = logging.getLogger("sales_ai.agent")


class AgentState(TypedDict):
    """Etat de l'agent LangGraph."""
    session_id: str
    messages: Annotated[list, operator.add]
    context: str
    context_status: str
    objection_detected: bool
    objection_type: str
    meeting_intent: bool
    slots_suggested: List[Dict[str, Any]]
    response: str


class ConversationAgent:
    """
    Agent de vente IA basé sur LangGraph connecté à des actions réelles (Calendrier & CRM).
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.rag = RAGPipeline()
        self.memory = ConversationMemory(session_id=session_id)
        self.objection_handler = ObjectionHandler()
        self.calendar_client = CalendarClient()
        self.hubspot_adapter = HubSpotAdapter()
        self.odoo_adapter = OdooAdapter()
        self.callbacks = self._init_langfuse_callbacks()

        try:
            if settings.LLM_PROVIDER == "openai":
                if not settings.OPENAI_API_KEY or len(settings.OPENAI_API_KEY) < 20:
                    raise ValueError(
                        "LLM_PROVIDER='openai' mais OPENAI_API_KEY est vide ou trop court."
                    )
                logger.info(f"Initialisation du LLM OpenAI ({settings.OPENAI_MODEL})")
                self.llm = ChatOpenAI(
                    model=settings.OPENAI_MODEL,
                    temperature=0.3,
                    max_tokens=150,
                    openai_api_key=settings.OPENAI_API_KEY,
                )
            else:
                logger.info(
                    f"Initialisation du LLM local Ollama ({settings.OLLAMA_MODEL}) "
                    f"sur {settings.OLLAMA_BASE_URL}"
                )
                self.llm = ChatOpenAI(
                    model=settings.OLLAMA_MODEL,
                    temperature=0.3,
                    max_tokens=150,
                    openai_api_key="ollama",
                    base_url=settings.OLLAMA_BASE_URL,
                )
            self.graph = self._build_graph()
        except Exception as e:
            logger.warning(f"Erreur d'initialisation LLM (fallback actif) : {e}")
            self.llm = None
            self.graph = None

    def _init_langfuse_callbacks(self) -> list:
        """Initialise le CallbackHandler Langfuse si configuré."""
        callbacks = []
        if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
            try:
                from langfuse.callback import CallbackHandler
                cb = CallbackHandler(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST,
                )
                callbacks.append(cb)
                logger.info("Langfuse CallbackHandler initialisé pour le tracing LLM.")
            except Exception as e:
                logger.warning(f"Langfuse indisponible : {e}")
        return callbacks

    def _build_graph(self):
        """Construit le graphe LangGraph avec nœud d'objection et détection d'intention de RDV."""
        graph = StateGraph(AgentState)

        graph.add_node("retrieve_context", self._retrieve_context)
        graph.add_node("detect_objection", self._detect_objection)
        graph.add_node("handle_objection", self._handle_objection)
        graph.add_node("check_meeting_intent", self._check_meeting_intent)
        graph.add_node("generate_response", self._generate_response)

        graph.set_entry_point("retrieve_context")
        graph.add_edge("retrieve_context", "detect_objection")

        def route_after_objection(state: AgentState) -> str:
            if state.get("objection_detected", False):
                return "handle_objection"
            return "check_meeting_intent"

        graph.add_conditional_edges(
            "detect_objection",
            route_after_objection,
            {
                "handle_objection": "handle_objection",
                "check_meeting_intent": "check_meeting_intent",
            },
        )

        graph.add_edge("handle_objection", END)
        graph.add_edge("check_meeting_intent", "generate_response")
        graph.add_edge("generate_response", END)

        return graph.compile()

    async def _retrieve_context(self, state: AgentState) -> Dict[str, Any]:
        messages = state.get("messages", [])
        last_message = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                last_message = m.content
                break

        if not last_message:
            return {"context": "", "context_status": "unavailable"}

        result = await self.rag.retrieve(last_message)
        return {
            "context": result.get("context", ""),
            "context_status": result.get("status", "unavailable"),
        }

    async def _detect_objection(self, state: AgentState) -> Dict[str, Any]:
        """Nœud LangGraph : Détecte si le message contient une objection commerciale."""
        messages = state.get("messages", [])
        last_message = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                last_message = m.content
                break

        objection_type = self.objection_handler.detect(last_message) if last_message else None
        detected = objection_type is not None
        return {"objection_detected": detected, "objection_type": objection_type or ""}

    async def _handle_objection(self, state: AgentState) -> Dict[str, Any]:
        """Nœud LangGraph : Génère la réponse à l'objection détectée."""
        messages = state.get("messages", [])
        context = state.get("context", "")
        last_message = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                last_message = m.content
                break

        response = self.objection_handler.handle(last_message, context=context)
        return {"response": response}

    async def _check_meeting_intent(self, state: AgentState) -> Dict[str, Any]:
        messages = state.get("messages", [])
        last_message = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                last_message = m.content.lower()
                break

        meeting_keywords = ["rendez-vous", "rdv", "créneau", "disponible", "d'accord", "oui", "15 minutes", "échange", "réserver", "agenda"]
        intent_detected = any(k in last_message for k in meeting_keywords)

        slots = []
        if intent_detected:
            try:
                slots = await self.calendar_client.get_available_slots()
            except Exception as e:
                logger.error(f"Erreur récupération créneaux : {e}")

        return {"meeting_intent": intent_detected, "slots_suggested": slots}

    @staticmethod
    def detect_language(text: str) -> str:
        """
        Détecte la langue du message entrant avec support natif de la Darija marocaine (Arabizi et caractères arabes),
        du Français et de l'Anglais via détection de mots-clés et langdetect.
        """
        if not text or not text.strip():
            return "Français"

        cleaned_text = text.lower().strip()

        # 1. Détection Caractères Arabes (Darija / Arabe)
        if any("\u0600" <= char <= "\u06ff" for char in text):
            return "Darija marocaine"

        # 2. Mots-clés Darija marocaine courants (Arabizi et Chiffres 3/7/9)
        darija_keywords = [
            "wach", "wesh", "bghit", "bghina", "chno", "chnow", "kifach", "kifa3ch",
            "bezaf", "bzaf", "mzyan", "mziyan", "chhal", "bch7al", "bchhal", "nta", "nti",
            "bikhir", "daba", "khadma", "afak", "ch3ad", "choufe", "chouf", "khoya",
            "khti", "n7am", "dial", "dialna", "dialk", "kayn", "makaynch", "marhaba",
            "labas", "fain", "tbarkallah", "wakha"
        ]

        words = set(re.findall(r'\w+', cleaned_text))
        if any(keyword in cleaned_text.split() or keyword in cleaned_text for keyword in darija_keywords):
            return "Darija marocaine"

        # 3. Fallback sur langdetect pour l'Anglais, le Français ou l'Arabe
        try:
            from langdetect import detect
            code = detect(cleaned_text)
            if code == "en":
                return "Anglais"
            elif code == "ar":
                return "Darija marocaine"
            elif code == "fr":
                return "Français"
        except Exception:
            pass

        # 4. Mots-clés Anglais de secours
        english_keywords = ["hello", "hi", "hey", "price", "website", "cost", "how", "what", "service", "company", "can", "do", "you", "offer", "software"]
        if any(w in words for w in english_keywords):
            return "Anglais"

        return "Français"

    async def _generate_response(self, state: AgentState) -> Dict[str, Any]:
        messages = state.get("messages", [])
        context = state.get("context", "")
        context_status = state.get("context_status", "unavailable")
        meeting_intent = state.get("meeting_intent", False)
        slots = state.get("slots_suggested", [])

        if meeting_intent and slots:
            slot_str = "\n".join([f"- {s.get('start_time')} (Duree: {s.get('duration_minutes', 15)} min)" for s in slots[:3]])
            response = (
                f"Parfait ! Voici nos creneaux libres pour une demo ou un echange de 15 minutes :\n"
                f"{slot_str}\n\n"
                f"Lequel de ces creneaux vous convient le mieux ?"
            )
            return {"response": response, "objection_detected": False}

        if not self.llm:
            fallback_res = "Marhaba ! IKSATECH propose des agents IA vocaux, des chatbots WhatsApp et du developpement sur-mesure a partir de 4 900 DH. Souhaitez-vous planifier une demo de 15 minutes ?"
            return {"response": fallback_res, "objection_detected": False}

        try:
            recent_messages = messages[-8:] if len(messages) > 8 else messages

            # Extraire le dernier message utilisateur pour détecter la langue
            last_user_text = ""
            for m in reversed(messages):
                if isinstance(m, HumanMessage):
                    last_user_text = m.content
                    break

            detected_lang = self.detect_language(last_user_text)
            logger.info(f"Langue détectée pour le message ('{last_user_text}') : {detected_lang}")

            rag_block = ""
            if context_status == "ok" and context:
                rag_block = f"\nContexte entreprise (RAG) :\n{context}\n"

            if detected_lang == "Anglais":
                system_instruction = (
                    "You are Alex, a warm, friendly and professional commercial advisor for IKSATECH in Morocco.\n"
                    "CRITICAL RULE: ALWAYS RESPOND IN ENGLISH ONLY. NEVER USE FRENCH OR ARABIC IN YOUR RESPONSE.\n"
                    "YOUR PERSONALITY:\n"
                    "- You speak naturally and conversationally, like a real human advisor — not a robot.\n"
                    "- You are warm, empathetic, and genuinely interested in helping the prospect.\n"
                    "- You adapt your tone: casual for small talk, professional for business questions.\n"
                    "RULES:\n"
                    "1. GREETINGS & SMALL TALK: If the user says hi, asks how you are, or chats casually — respond naturally and warmly first, then gently introduce IKSATECH.\n"
                    "2. BUSINESS QUESTIONS: If the user asks about services, pricing, websites, apps, or AI — present IKSATECH's solutions clearly:\n"
                    "   - Custom websites & mobile apps\n"
                    "   - AI agents & voice assistants\n"
                    "   - WhatsApp chatbots\n"
                    "   - Starting from 4,900 MAD\n"
                    "   Then invite them to a free 15-minute discovery call.\n"
                    "3. Keep answers SHORT and NATURAL: 1 to 2 sentences max. No bullet points in voice responses.\n"
                    f"{rag_block}"
                )
                prompt_messages = [
                    SystemMessage(content=system_instruction),
                    *recent_messages,
                ]
            elif detected_lang == "Darija marocaine":
                system_instruction = (
                    "Nta agent commercial mzyan w 9rib l-nas dial IKSATECH f l-Maghrib.\n"
                    "INSTRUCTION DE LANGUE: JAWB GHIR B DARIJA MAROCAINE (Arabizi b 3/7/9 ou carac. arabes). MATJAWBCH B D-FRANÇAIS !\n"
                    "CAPACITÉS :\n"
                    "1. Ila slem 3lik l-client aw swlak 'kif dayer / labas', jawbo b Darija marocaine mziyana w dahlia.\n"
                    "2. Ila swlak 3la les services, sites web, l-khedma aw l-prix, hdarlho 3la IKSATECH (sites web sur-mesure, agents IA, chatbots WhatsApp b 4 900 DH) w 9tarah 15 min f telfon.\n"
                    "Jawb b jomla aw jomlatayn mziyanin w concis."
                )
                prompt_messages = [
                    SystemMessage(content=system_instruction),
                    HumanMessage(content=last_user_text)
                ]
            else:
                system_instruction = (
                    "Tu es un conseiller commercial d'élite, chaleureux et professionnel pour IKSATECH au Maroc.\n"
                    "Réponds en Français clair et naturel.\n"
                    "CAPACITÉS :\n"
                    "1. Si le prospect entame une discussion normale (salutations, politesse), réponds de manière chaleureuse et naturelle.\n"
                    "2. S'il demande des informations sur les services, prix ou projets, présente IKSATECH (sites web sur-mesure, agents IA, chatbots WhatsApp à partir de 4 900 DH) et propose un échange de 15 minutes.\n"
                    "Sois concis (1 à 2 phrases max).\n"
                    f"{rag_block}"
                )
                prompt_messages = [
                    SystemMessage(content=system_instruction),
                    HumanMessage(content=last_user_text)
                ]
            try:
                config = {"callbacks": self.callbacks} if self.callbacks else {}
                llm_response = await asyncio.wait_for(self.llm.ainvoke(prompt_messages, config=config), timeout=30.0)
                res_text = llm_response.content
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"Fallback actif suite au delai ou erreur LLM : {e}")
                res_text = "Salam ! Marhaba bikom f IKSATECH. Nos experts en developpement web et IA peuvent vous accompagner. Seriez-vous disponible cette semaine pour un court echange de 15 minutes ?"

            return {"response": res_text, "objection_detected": False}
        except Exception as e:
            logger.error(f"Erreur d'appel LLM : {e}")
            return {
                "response": "Salam ! Marhaba bikom f IKSATECH. Nos experts peuvent vous accompagner sur ce sujet. Auriez-vous 10 minutes a nous accorder cette semaine ?",
                "objection_detected": False
            }

    async def process(self, user_message: str) -> str:
        """Traite un message utilisateur avec anonymisation PII, fenêtrage et LangGraph."""
        # 1. Redaction PII
        sanitized_user_message = pii_redactor.sanitize(user_message)

        history = await self.memory.get_history()

        graph_messages = []
        for msg in history[-8:]:
            role = msg.get("role")
            content = msg.get("content")
            if role == "user":
                graph_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                graph_messages.append(AIMessage(content=content))

        graph_messages.append(HumanMessage(content=sanitized_user_message))
        self.memory.add_message("user", sanitized_user_message)

        if self.graph:
            initial_state = {
                "session_id": self.session_id,
                "messages": graph_messages,
                "context": "",
                "context_status": "unavailable",
                "objection_detected": False,
                "objection_type": "",
                "meeting_intent": False,
                "slots_suggested": [],
                "response": ""
            }
            try:
                final_state = await self.graph.ainvoke(initial_state)
                response = final_state.get("response", "")
            except Exception as e:
                logger.error(f"Erreur exécution graphe : {e}")
                response = "Merci pour votre message. Seriez-vous disponible cette semaine pour un court échange de 15 minutes ?"
        else:
            objection_type = self.objection_handler.detect(sanitized_user_message)
            if objection_type:
                response = self.objection_handler.handle(sanitized_user_message)
            else:
                response = f"Merci pour votre message. Quand seriez-vous disponible pour en échanger ?"

        self.memory.add_message("assistant", response)
        await self.memory.save()
        return response

    async def save_state(self):
        """Persiste l'état courant de la session."""
        await self.memory.save()
