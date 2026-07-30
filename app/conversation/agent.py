"""
Agent IA Commercial d'élite (BDR) basé sur LangGraph (Module 4, 5 & 6).
Gère la recherche RAG, la détection des objections, la détection d'intention de rendez-vous (check_meeting_intent),
la réservation de créneaux réels (CalendarClient) et la synchro CRM (HubSpot/Odoo).
"""
import logging
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
from app.shared.config import settings

logger = logging.getLogger("sales_ai.agent")


class AgentState(TypedDict):
    """État de l'agent LangGraph."""
    session_id: str
    messages: Annotated[list, operator.add]
    context: str
    objection_detected: bool
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

        try:
            self.llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                temperature=0.3,
                openai_api_key=settings.OPENAI_API_KEY,
            )
            self.graph = self._build_graph()
        except Exception as e:
            logger.warning(f"Erreur d'initialisation LLM (fallback actif) : {e}")
            self.llm = None
            self.graph = None

    def _build_graph(self):
        """Construit le graphe LangGraph avec détection d'intention de RDV."""
        graph = StateGraph(AgentState)

        graph.add_node("retrieve_context", self._retrieve_context)
        graph.add_node("check_meeting_intent", self._check_meeting_intent)
        graph.add_node("generate_response", self._generate_response)

        graph.set_entry_point("retrieve_context")
        graph.add_edge("retrieve_context", "check_meeting_intent")
        graph.add_edge("check_meeting_intent", "generate_response")
        graph.add_edge("generate_response", END)

        return graph.compile()

    async def _retrieve_context(self, state: AgentState) -> Dict[str, Any]:
        """Récupère le contexte RAG."""
        messages = state.get("messages", [])
        last_message = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                last_message = m.content
                break

        context = ""
        if last_message:
            context = await self.rag.retrieve(last_message)
        return {"context": context}

    async def _check_meeting_intent(self, state: AgentState) -> Dict[str, Any]:
        """Nœud LangGraph : Détecte l'intention de réservation de rendez-vous."""
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

    async def _generate_response(self, state: AgentState) -> Dict[str, Any]:
        """Gère les objections, la planification réelle de RDV ou génère la réponse LLM."""
        messages = state.get("messages", [])
        context = state.get("context", "")
        meeting_intent = state.get("meeting_intent", False)
        slots = state.get("slots_suggested", [])

        last_message = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                last_message = m.content
                break

        # 1. Objections
        objection_type = self.objection_handler.detect(last_message)
        if objection_type:
            response = self.objection_handler.handle(last_message, context)
            return {"response": response, "objection_detected": True}

        # 2. Proposition ou confirmation de créneaux réels
        if meeting_intent and slots:
            slot_str = "\n".join([f"- {s.get('start_time')} (Durée: {s.get('duration_minutes', 15)} min)" for s in slots[:3]])
            response = (
                f"Parfait ! Voici les créneaux disponibles dans notre agenda pour un échange de 15 minutes :\n"
                f"{slot_str}\n\n"
                f"Lequel de ces créneaux vous convient le mieux ?"
            )
            return {"response": response, "objection_detected": False}

        # 3. LLM OpenAI
        if not self.llm or not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("sk-..."):
            fallback_res = "Merci pour votre intérêt. Nos experts IKSATECH peuvent vous accompagner. Seriez-vous disponible cette semaine pour un échange de 15 minutes ?"
            return {"response": fallback_res, "objection_detected": False}

        try:
            # Fenêtrage de l'historique (garder les 8 derniers messages)
            recent_messages = messages[-8:] if len(messages) > 8 else messages

            system_instruction = (
                "Tu es un agent d'intelligence artificielle commercial d'élite (BDR) pour IKSATECH.\n"
                "Ton rôle est d'engager une conversation naturelle en français (ou la langue du prospect),\n"
                "qualifier ses besoins en transformation digitale, développement logiciel et cybersécurité,\n"
                "et obtenir un rendez-vous de 15 minutes.\n\n"
                f"Contexte sur notre entreprise et services (RAG) :\n{context}\n\n"
                "Consignes :\n"
                "- Sois concis, professionnel, empathique et chaleureux.\n"
                "- Pose une seule question claire à la fois.\n"
                "- Si le prospect est intéressé, propose de réserver un créneau."
            )
            prompt_messages = [SystemMessage(content=system_instruction)] + recent_messages
            llm_response = await self.llm.ainvoke(prompt_messages)
            return {"response": llm_response.content, "objection_detected": False}
        except Exception as e:
            logger.error(f"Erreur d'appel LLM : {e}")
            return {
                "response": "Je comprends tout à fait. Nos experts peuvent vous accompagner sur ce sujet. Auriez-vous 10 minutes à nous accorder cette semaine ?",
                "objection_detected": False
            }

    async def process(self, user_message: str) -> str:
        """Traite un message utilisateur avec fenêtrage d'historique et logging structuré."""
        history = await self.memory.get_history()

        graph_messages = []
        for msg in history[-8:]:  # Fenêtrage mémoire
            role = msg.get("role")
            content = msg.get("content")
            if role == "user":
                graph_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                graph_messages.append(AIMessage(content=content))

        graph_messages.append(HumanMessage(content=user_message))
        self.memory.add_message("user", user_message)

        if self.graph:
            initial_state = {
                "session_id": self.session_id,
                "messages": graph_messages,
                "context": "",
                "objection_detected": False,
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
            objection_type = self.objection_handler.detect(user_message)
            if objection_type:
                response = self.objection_handler.handle(user_message)
            else:
                response = f"Merci pour votre message concernant '{user_message}'. Quand seriez-vous disponible pour en échanger ?"

        self.memory.add_message("assistant", response)
        await self.memory.save()
        return response

    async def save_state(self):
        """Persiste l'état courant de la session."""
        await self.memory.save()
