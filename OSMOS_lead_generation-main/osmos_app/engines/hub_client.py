"""
client.py
=========
Client HTTP synchrone pour communiquer avec l'Actionneur Hub (web-actions-qwen).

Contrat d'interface couvert :
  POST /generate-plan    {"prompt": str}               -> {"steps": list[str]}
  POST /run-agent        {"prompt": str, "steps": [...]} -> {"status": "started"}
  GET  /status           ->  dict complet de l'état d'exécution
  POST /submit-help      {"response": str}             -> dict

Usage minimal :
    from cerveau.hub_client import HubClient

    client = HubClient("http://localhost:8000")
    steps  = client.generate_plan("Extraire le profil LinkedIn d'Acme Corp")
    client.run_agent("Extraire le profil LinkedIn d'Acme Corp", steps)
    result = client.wait_for_completion(timeout=180.0)
"""
from __future__ import annotations

import time
from typing import Optional

import requests
from requests.exceptions import ConnectionError, Timeout


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class HubConnectionError(RuntimeError):
    """Levée quand le Hub est inaccessible (non démarré, port incorrect…)."""


class HubHumanInterventionRequired(RuntimeError):
    """
    Levée par wait_for_completion quand le Hub signale waiting_for_help=True
    et qu'aucun auto_help_response n'a été fourni.

    L'attribut `question` contient le texte de la demande d'aide du Hub.
    """
    def __init__(self, question: str):
        self.question = question
        super().__init__(
            f"Le Hub a besoin d'une intervention humaine.\n"
            f"Question : {question}\n"
            f"Appelez client.submit_help(votre_réponse) puis relancez le polling."
        )


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class HubClient:
    """
    Client HTTP vers l'Actionneur Hub OSMOS.

    Args:
        base_url:        URL de base du Hub (ex: "http://localhost:8000").
        request_timeout: Timeout réseau en secondes pour chaque requête individuelle.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        request_timeout: float = 600.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.request_timeout = request_timeout

    # ── Méthodes privées ─────────────────────────────────────────────────

    def _get(self, path: str) -> dict:
        url = f"{self.base_url}{path}"
        try:
            resp = requests.get(url, timeout=self.request_timeout)
            resp.raise_for_status()
            return resp.json()
        except (ConnectionError, Timeout) as exc:
            raise HubConnectionError(
                f"Impossible de joindre le Hub à {url}.\n"
                f"Assurez-vous d'avoir lancé : python3 app.py  (dans le dossier du Hub)\n"
                f"Détail : {exc}"
            ) from exc

    def _post(self, path: str, payload: dict) -> dict:
        url = f"{self.base_url}{path}"
        try:
            resp = requests.post(
                url,
                json=payload,
                timeout=self.request_timeout,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()
        except (ConnectionError, Timeout) as exc:
            raise HubConnectionError(
                f"Impossible de joindre le Hub à {url}.\n"
                f"Assurez-vous d'avoir lancé : python3 app.py  (dans le dossier du Hub)\n"
                f"Détail : {exc}"
            ) from exc

    # ── API publique ──────────────────────────────────────────────────────

    def is_alive(self) -> bool:
        """Vérifie rapidement que le Hub répond (GET /status)."""
        try:
            requests.get(
                f"{self.base_url}/status",
                timeout=5.0,
            )
            return True
        except Exception:
            return False

    def generate_plan(self, prompt: str) -> list[str]:
        """
        Génère un plan d'exécution depuis le Hub.

        Args:
            prompt: Commande en langage naturel (ex: "Extraire le profil LinkedIn de…").

        Returns:
            Liste ordonnée d'étapes (strings) à passer à run_agent.

        Raises:
            HubConnectionError: Si le Hub est inaccessible.
        """
        data = self._post("/generate-plan", {"prompt": prompt})
        if "error" in data:
            raise RuntimeError(f"Erreur Hub /generate-plan : {data['error']}")
        return data.get("steps", [])

    def run_agent(self, prompt: str, steps: list[str]) -> dict:
        """
        Lance l'agent en tâche de fond sur le Hub.

        Args:
            prompt: Commande originale en langage naturel.
            steps:  Plan d'exécution obtenu via generate_plan.

        Returns:
            Réponse JSON du Hub ({"status": "started"} ou {"error": …}).

        Raises:
            HubConnectionError: Si le Hub est inaccessible.
            RuntimeError:       Si le Hub renvoie une erreur métier.
        """
        data = self._post("/run-agent", {"prompt": prompt, "steps": steps})
        if "error" in data:
            raise RuntimeError(f"Erreur Hub /run-agent : {data['error']}")
        return data

    def get_status(self) -> dict:
        """
        Récupère l'état courant de l'exécution.

        Returns:
            Dict complet : running, success, error, logs, current_step,
            waiting_for_help, help_question, extracted_content, final_result…

        Raises:
            HubConnectionError: Si le Hub est inaccessible.
        """
        return self._get("/status")

    def submit_help(self, response: str) -> dict:
        """
        Répond à une demande d'assistance de l'agent (2FA, CAPTCHA, guidance…).

        Args:
            response: Texte de réponse à envoyer à l'agent.

        Returns:
            Réponse JSON du Hub.
        """
        return self._post("/submit-help", {"response": response})

    def wait_for_completion(
        self,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
        auto_help_response: Optional[str] = None,
    ) -> dict:
        """
        Poll /status en boucle jusqu'à la fin de l'exécution (running=False)
        ou jusqu'au timeout.

        Args:
            poll_interval:      Intervalle de polling en secondes.
            timeout:            Durée maximale d'attente en secondes.
            auto_help_response: Si fourni et que waiting_for_help=True,
                                appelle automatiquement submit_help avec cette
                                réponse et continue le polling.
                                Si None et que waiting_for_help=True, lève
                                HubHumanInterventionRequired.

        Returns:
            Dernier dict /status complet (succès, erreur ou timeout).

        Raises:
            HubConnectionError:             Si le Hub devient inaccessible.
            HubHumanInterventionRequired:   Si le Hub demande de l'aide et
                                            qu'aucun auto_help_response n'est fourni.
            TimeoutError:                   Si le timeout est dépassé avant la fin.
        """
        start = time.monotonic()
        help_handled_at: Optional[str] = None  # évite de spammer submit_help

        while True:
            elapsed = time.monotonic() - start
            if elapsed >= timeout:
                raise TimeoutError(
                    f"Timeout atteint ({timeout:.0f}s) — l'agent tourne toujours. "
                    f"Augmentez le timeout ou vérifiez les logs du Hub."
                )

            status = self.get_status()

            # ── Assistance humaine requise ────────────────────────────────
            if status.get("waiting_for_help"):
                question = status.get("help_question", "(aucune question fournie)")
                if auto_help_response is not None:
                    # Évite de soumettre la même réponse en boucle
                    if help_handled_at != question:
                        print(
                            f"  [HubClient] ⚠️  Aide requise par le Hub :\n"
                            f"     {question}\n"
                            f"  → Réponse automatique : {auto_help_response!r}"
                        )
                        self.submit_help(auto_help_response)
                        help_handled_at = question
                else:
                    if help_handled_at != question:
                        print(f"\n" + "="*60)
                        print(f"⚠️ [ACTION REQUISE] Le Hub est bloqué sur une vérification ! ⚠️")
                        print(f"Question du Hub : {question}")
                        print(f"👉 Le processus est en pause. Pour fournir le code LinkedIn (2FA),")
                        print(f"👉 Ouvrez un NOUVEAU terminal et tapez cette commande :")
                        print(f"\ncurl -X POST http://localhost:8000/submit-help -H \"Content-Type: application/json\" -d '{{\"response\": \"VOTRE_CODE_ICI\"}}'\n")
                        print(f"="*60 + "\n")
                        help_handled_at = question

            # ── Terminé ───────────────────────────────────────────────────
            if not status.get("running", True):
                return status

            # ── Toujours en cours ─────────────────────────────────────────
            step = status.get("current_step", "?")
            print(
                f"  [HubClient] ⏳  Étape {step} — "
                f"en cours… ({elapsed:.0f}s / {timeout:.0f}s max)"
            )
            time.sleep(poll_interval)
