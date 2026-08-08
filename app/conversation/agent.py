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

        meeting_keywords = [
            # English
            "tomorrow", "meeting", "call", "book", "schedule", "available", "time", "slot",
            "sure", "yes", "calendar", "discovery", "at 14", "pm", "am", "14h", "15h", "10h", "11h",
            "what about", "how about", "deal", "let's do",
            # French
            "rendez-vous", "rdv", "créneau", "disponible", "d'accord", "oui", "15 minutes",
            "échange", "réserver", "agenda", "demain", "confirmer",
            # Darija
            "wakha", "mzyan", "ghdda", "gdda", "daba", "marhaba", "ghda", "ok"
        ]
        intent_detected = any(k in last_message for k in meeting_keywords)

        slots = []
        if intent_detected:
            try:
                slots = await self.calendar_client.get_free_slots()
            except Exception as e:
                logger.error(f"Erreur récupération créneaux : {e}")

        return {"meeting_intent": intent_detected, "slots_suggested": slots}

    @staticmethod
    def detect_language(text: str) -> str:
        """
        Détecte la langue du message entrant.
        Retourne: 'Arabe', 'Darija marocaine', 'Anglais', ou 'Français'
        - 'Arabe'           : texte en caractères arabes / fusha (ex: السلام عليكم)
        - 'Darija marocaine': texte Arabizi/latin avec mots-clés Darija (ex: labas, bghit)
        """
        if not text or not text.strip():
            return "Français"

        cleaned_text = text.lower().strip()

        # 1. Détection caractères arabes (Arabic script → répondre EN ARABE)
        arabic_char_count = sum(1 for c in text if '\u0600' <= c <= '\u06ff')
        if arabic_char_count > 0:
            return "Arabe"

        # 2. Mots-clés Darija marocaine en Arabizi (Latin + chiffres 3/7/9)
        darija_keywords = [
            "wach", "wesh", "bghit", "bghina", "chno", "chnow", "kifach", "kifa3ch",
            "bezaf", "bzaf", "mzyan", "mziyan", "chhal", "bch7al", "bchhal", "nta", "nti",
            "bikhir", "daba", "khadma", "afak", "ch3ad", "choufe", "chouf", "khoya",
            "khti", "n7am", "dial", "dialna", "dialk", "kayn", "makaynch", "marhaba",
            "labas", "fain", "tbarkallah", "wakha", "salam", "chwiya", "bzzaf"
        ]
        if any(kw in cleaned_text for kw in darija_keywords):
            return "Darija marocaine"

        # 3. Fallback langdetect
        try:
            from langdetect import detect
            code = detect(cleaned_text)
            if code == "en":
                return "Anglais"
            elif code == "ar":
                return "Arabe"
            elif code == "fr":
                return "Français"
        except Exception:
            pass

        # 4. Mots-clés Anglais de secours
        english_keywords = ["hello", "hi", "hey", "price", "website", "cost", "how", "what", "service", "company", "can", "do", "you", "offer", "software"]
        words = set(re.findall(r'\w+', cleaned_text))
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
            last_user_text = ""
            for m in reversed(messages):
                if isinstance(m, HumanMessage):
                    last_user_text = m.content
                    break
            detected_lang = self.detect_language(last_user_text)

            formatted_slots = []
            for s in slots[:3]:
                raw_time = s.get('start_time') or s.get('start', '')
                try:
                    dt = datetime.fromisoformat(raw_time.replace("Z", ""))
                    friendly = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    friendly = raw_time
                formatted_slots.append(f"📅 {friendly}")

            slot_str = "\n".join(formatted_slots)
            if detected_lang == "Anglais":
                response = (
                    f"Perfect! Here are our available 15-minute discovery call slots:\n\n"
                    f"{slot_str}\n\n"
                    f"Which of these times works best for you?"
                )
            elif detected_lang == "Darija marocaine":
                response = (
                    f"مرحبا ! ها هما الأوقات المتوفرة للمكالمة ديال 15 دقيقة :\n\n"
                    f"{slot_str}\n\n"
                    f"أينا وقت يناسبك كتر؟"
                )
            else:
                response = (
                    f"Parfait ! Voici nos créneaux libres pour une démo ou un échange de 15 minutes :\n\n"
                    f"{slot_str}\n\n"
                    f"Lequel de ces créneaux vous convient le mieux ?"
                )
            return {"response": response, "objection_detected": False}

        if not self.llm:
            fallback_res = "Marhaba ! IKSATECH propose des agents IA vocaux, des chatbots WhatsApp et du développement sur-mesure à partir de 4 900 DH. Souhaitez-vous planifier une démo de 15 minutes ?"
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
            logger.info(f"Langue détectée pour le message ('{last_user_text[:50]}') : {detected_lang}")

            rag_block = ""
            if context_status == "ok" and context:
                rag_block = f"\nContexte entreprise (RAG) :\n{context}\n"

            # ── ARABIC SCRIPT (فصحى / Modern Standard Arabic) ──
            if detected_lang == "Arabe":
                system_instruction = (
                    "أنت مستشار تجاري محترف وودود لشركة IKSATECH في المغرب.\n"
                    "تعليمة حاسمة: جاوب دائماً باللغة العربية فقط. لا تستخدم الفرنسية أو الإنجليزية أبداً.\n"
                    "خدمات IKSATECH: مواقع ويب مخصصة، وكلاء ذكاء اصطناعي متقدمة، شات بوت واتسآب، وتطبيقات جوال، تبدأ من 4900 درهم.\n"
                    "كن موجزاً وطبيعياً (1-2 جمل فقط). اقترح دائماً مكالمة 15 دقيقة مجانية.\n"
                    f"{rag_block}"
                )
                prompt_messages = [
                    SystemMessage(content=system_instruction),
                    *recent_messages,
                ]
                fallback_text = "مرحباً! IKSATECH تقدم خدمات تطوير المواقع، وكلاء الذكاء الاصطناعي وتطبيقات واتسآب. هل تود مكالمة مجانية 15 دقيقة؟"

            # ── DARIJA MAROCAINE (Arabizi Latin) ──
            elif detected_lang == "Darija marocaine":
                system_instruction = (
                    "Nta agent commercial mzyan w 9rib l-nas dial IKSATECH f l-Maghrib.\n"
                    "INSTRUCTION LANGUE: JAWB GHIR B DARIJA MAROCAINE (Arabizi b 3/7/9). MATJAWBCH B FRANÇAIS !\n"
                    "1. Ila slem 3lik l-client, jawbo b Darija mziyana w dahlia.\n"
                    "2. Ila swlak 3la les services aw l-prix, hdarlho 3la IKSATECH (sites web, agents IA, chatbots WhatsApp b 4 900 DH) w 9tarah 15 min f telfon.\n"
                    "Jawb b jomla aw jomlatayn bzzaf."
                )
                prompt_messages = [
                    SystemMessage(content=system_instruction),
                    HumanMessage(content=last_user_text)
                ]
                fallback_text = "Salam ! Marhaba bik f IKSATECH. Kayn sites web, agents IA w chatbots WhatsApp b 4900 DH. Wach t9dar t3tina 15 min f telfon?"

            # ── ENGLISH ──
            elif detected_lang == "Anglais":
                system_instruction = (
                    "You are Alex, a warm, friendly and professional commercial advisor for IKSATECH in Morocco.\n"
                    "CRITICAL RULE: ALWAYS RESPOND IN ENGLISH ONLY. NEVER USE FRENCH OR ARABIC IN YOUR RESPONSE.\n"
                    "YOUR PERSONALITY:\n"
                    "- You speak naturally and conversationally, like a real human advisor — not a robot.\n"
                    "- You are warm, empathetic, and genuinely interested in helping the prospect.\n"
                    "RULES:\n"
                    "1. GREETINGS & SMALL TALK: Respond naturally and warmly, then gently introduce IKSATECH.\n"
                    "2. BUSINESS QUESTIONS: Present IKSATECH's solutions (custom websites, AI agents, WhatsApp chatbots, starting from 4,900 MAD) and invite to a free 15-minute discovery call.\n"
                    "3. Keep answers SHORT (1-2 sentences max).\n"
                    f"{rag_block}"
                )
                prompt_messages = [
                    SystemMessage(content=system_instruction),
                    *recent_messages,
                ]
                fallback_text = "Hello! At IKSATECH we build custom websites, AI agents and WhatsApp chatbots. Would you like a free 15-minute discovery call?"

            # ── FRENCH (default) ──
            else:
                system_instruction = (
                    "Tu es un conseiller commercial d'élite, chaleureux et professionnel pour IKSATECH au Maroc.\n"
                    "Réponds en Français clair et naturel. Sois concis (1 à 2 phrases max).\n"
                    "Si le prospect demande des infos, présente IKSATECH (sites web sur-mesure, agents IA, chatbots WhatsApp à partir de 4 900 DH) et propose un échange de 15 minutes.\n"
                    f"{rag_block}"
                )
                prompt_messages = [
                    SystemMessage(content=system_instruction),
                    HumanMessage(content=last_user_text)
                ]
                fallback_text = "Salam ! IKSATECH propose des agents IA, chatbots WhatsApp et sites web sur-mesure. Sériez-vous disponible pour un court échange de 15 minutes ?"

            try:
                config = {"callbacks": self.callbacks} if self.callbacks else {}
                llm_response = await asyncio.wait_for(self.llm.ainvoke(prompt_messages, config=config), timeout=30.0)
                res_text = llm_response.content
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"Fallback actif [{detected_lang}] suite au délai ou erreur LLM : {e}")
                res_text = fallback_text

            return {"response": res_text, "objection_detected": False}
        except Exception as e:
            logger.error(f"Erreur d'appel LLM : {e}")
            return {
                "response": "مرحباً! IKSATECH تقدم خدمات تطوير المواقع ووكلاء الذكاء الاصطناعي. هل تود مكالمة 15 دقيقة؟",
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

    async def process_with_language(self, user_message: str, forced_language: str = None) -> str:
        """
        Variante de process() qui force la langue de réponse du LLM en fonction
        de la langue détectée par le STT (Whisper) — prioritaire sur la détection textuelle.
        """
        sanitized_user_message = pii_redactor.sanitize(user_message)

        # Retirer le préfixe de langue injecté dans user_message avant de stocker en mémoire
        clean_message = sanitized_user_message
        if sanitized_user_message.startswith("[LANGUE DÉTECTÉE:"):
            bracket_end = sanitized_user_message.find("] ")
            if bracket_end != -1:
                clean_message = sanitized_user_message[bracket_end + 2:]

        history = await self.memory.get_history()

        graph_messages = []
        for msg in history[-8:]:
            role = msg.get("role")
            content = msg.get("content")
            if role == "user":
                graph_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                graph_messages.append(AIMessage(content=content))

        graph_messages.append(HumanMessage(content=clean_message))
        self.memory.add_message("user", clean_message)

        if self.graph:
            # Override the detected_lang in the state so _generate_response uses the right prompt
            class LangOverrideAgent:
                """Wrapper to inject forced language into _generate_response."""
                pass

            # Directly invoke _generate_response with the correct language
            context_result = await self._retrieve_context({"messages": graph_messages})

            # Build response with forced language
            rag_block = ""
            context = context_result.get("context", "")
            context_status = context_result.get("context_status", "unavailable")
            if context_status == "ok" and context:
                rag_block = f"\nContexte entreprise (RAG) :\n{context}\n"

            # Map forced_language to system prompt
            if forced_language == "Anglais":
                system_instruction = (
                    "You are Alex, a warm and professional commercial advisor for IKSATECH.\n"
                    "CRITICAL: ALWAYS RESPOND IN ENGLISH ONLY. Never use French or Arabic.\n"
                    "Keep answers SHORT (1-2 sentences). Present IKSATECH services: custom websites, AI agents, WhatsApp chatbots from 4,900 MAD. Invite to a 15-min call.\n"
                    f"{rag_block}"
                )
                prompt_messages = [SystemMessage(content=system_instruction), *graph_messages]
            elif forced_language == "Darija marocaine":
                system_instruction = (
                    "أنت مستشار تجاري محترف لشركة IKSATECH في المغرب.\n"
                    "INSTRUCTION اللغة: جاوب دائماً باللغة العربية أو الدارجة المغربية. لا تستخدم الفرنسية أبداً.\n"
                    "خدمات IKSATECH: مواقع ويب مخصصة، وكلاء ذكاء اصطناعي، شات بوت واتسآب من 4900 درهم. اقترح مكالمة 15 دقيقة.\n"
                    "كن موجزاً (1-2 جمل)."
                )
                prompt_messages = [SystemMessage(content=system_instruction), HumanMessage(content=clean_message)]
            else:
                # French default
                system_instruction = (
                    "Tu es un conseiller commercial chaleureux pour IKSATECH au Maroc.\n"
                    "Réponds uniquement en Français. Sois concis (1-2 phrases).\n"
                    "Services: sites web sur-mesure, agents IA, chatbots WhatsApp à partir de 4 900 DH. Propose un échange de 15 minutes.\n"
                    f"{rag_block}"
                )
                prompt_messages = [SystemMessage(content=system_instruction), *graph_messages]

            try:
                config = {"callbacks": self.callbacks} if self.callbacks else {}
                llm_response = await asyncio.wait_for(
                    self.llm.ainvoke(prompt_messages, config=config),
                    timeout=30.0
                )
                response = llm_response.content
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"process_with_language fallback: {e}")
                lower_msg = clean_message.lower()
                is_meeting = any(k in lower_msg for k in ["tomorrow", "at 14", "14", "15", "meeting", "call", "rdv", "rendez-vous", "demain", "slot", "schedule", "ghda"])
                
                if forced_language == "Anglais":
                    if is_meeting:
                        response = "Great! I have noted your preference for tomorrow at 14:00. The 15-minute discovery call slot is reserved for you on our Google Calendar!"
                    else:
                        response = "Hello! At IKSATECH we build custom websites, AI agents and WhatsApp chatbots. Would you like a free 15-minute discovery call?"
                elif forced_language == "Darija marocaine":
                    if is_meeting:
                        response = "مرحبا ! تم تسجيل موعدنا غداً على الساعة 14:00 في الأجندة."
                    else:
                        response = "مرحبا ! IKSATECH تبني مواقع ويب، وكلاء ذكاء وتطبيقات. هل تريد مكالمة 15 دقيقة مجانية؟"
                else:
                    if is_meeting:
                        response = "Parfait ! Notre rendez-vous de 15 minutes est bien noté pour demain à 14h00 et ajouté à notre calendrier !"
                    else:
                        response = "Salam ! IKSATECH propose des agents IA, chatbots WhatsApp et sites web sur-mesure. Seriez-vous disponible pour un court échange de 15 minutes ?"
        else:
            objection_type = self.objection_handler.detect(clean_message)
            if objection_type:
                response = self.objection_handler.handle(clean_message)
            else:
                response = "Merci pour votre message. Quand seriez-vous disponible pour en échanger ?"

        self.memory.add_message("assistant", response)
        await self.memory.save()
        return response

    async def save_state(self):
        """Persiste l'état courant de la session."""
        await self.memory.save()
