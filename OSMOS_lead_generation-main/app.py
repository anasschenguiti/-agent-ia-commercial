import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv(override=True)

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse, HTMLResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from browser_use.llm.messages import SystemMessage, UserMessage
from browser_use.agent.views import ActionResult
from browser_use.tools.views import DoneAction
# Import configuration and monkey patches from actions.py to stay DRY
from actions import browser, llm, TaskPlan, controller
from skills.loader import load_skills

app_state = {
    "running": False,
    "prompt": "",
    "plan": [],
    "logs": [],
    "current_step": 0,
    "error": None,
    "success": False,
    "waiting_for_help": False,
    "help_question": None,
    "help_response": None,
    "last_intervention_step": 0,
    "extracted_content": [],
    "final_result": None,
    "stop_requested": False,
    "pending_new_task": None
}

@controller.action(description="Request help from the human user when blocked or needing input/validation. Provide a description of what you need help with.")
async def request_human_help(question: str) -> str:
    app_state["waiting_for_help"] = True
    app_state["help_question"] = question
    app_state["help_response"] = None
    
    # Wait until help_response is set
    while app_state["help_response"] is None:
        await asyncio.sleep(0.5)
        
    response = app_state["help_response"]
    app_state["waiting_for_help"] = False
    app_state["help_question"] = None
    app_state["help_response"] = None
    return f"User replied: {response}"

@controller.action(
    description="Complete the current task and report the outcome. Use this when the current plan is finished.",
    param_model=DoneAction
)
async def done(params: DoneAction):
    # Log the completion step to the UI progress panel
    app_state["logs"].append({
        "step": app_state["current_step"],
        "evaluation": f"Task completed: {params.text} (Success: {params.success})",
        "memory": "Finished task.",
        "next_goal": "Returning final result"
    })
    
    # Return immediately to unblock the frontend API
    return ActionResult(
        is_done=True,
        success=params.success,
        extracted_content=params.text,
        long_term_memory=f"Task status: {params.success} - {params.text}"
    )

async def homepage(request):
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Web Automation Agent</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-glow-1: #4f46e5;
            --bg-glow-2: #06b6d4;
            --glass-bg: rgba(17, 24, 39, 0.7);
            --glass-border: rgba(255, 255, 255, 0.08);
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --accent-violet: #6366f1;
            --accent-cyan: #22d3ee;
            --danger: #ef4444;
            --success: #10b981;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Inter', sans-serif;
        }

        body {
            background-color: #030712;
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow-x: hidden;
            position: relative;
        }

        /* Ambient background glow */
        .bg-glow {
            position: absolute;
            width: 600px;
            height: 600px;
            border-radius: 50%;
            filter: blur(140px);
            opacity: 0.15;
            z-index: 0;
            pointer-events: none;
        }
        .glow-1 {
            background: var(--bg-glow-1);
            top: -10%;
            left: -10%;
        }
        .glow-2 {
            background: var(--bg-glow-2);
            bottom: -10%;
            right: -10%;
        }

        .container {
            width: 100%;
            max-width: 900px;
            padding: 2rem;
            z-index: 1;
        }

        header {
            margin-bottom: 2rem;
            text-align: center;
        }

        h1 {
            font-family: 'Outfit', sans-serif;
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #ffffff 40%, #a5b4fc 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
            letter-spacing: -0.03em;
        }

        p.subtitle {
            color: var(--text-secondary);
            font-size: 1.1rem;
            font-weight: 300;
        }

        /* Glassmorphic Panel */
        .panel {
            background: var(--glass-bg);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            padding: 2.5rem;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        /* Form elements */
        .input-group {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            margin-bottom: 2rem;
        }

        label {
            font-family: 'Outfit', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-primary);
            letter-spacing: -0.01em;
        }

        textarea {
            width: 100%;
            height: 120px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 1rem;
            color: var(--text-primary);
            font-size: 1rem;
            resize: none;
            outline: none;
            transition: all 0.2s ease;
        }

        textarea:focus {
            border-color: var(--accent-violet);
            background: rgba(255, 255, 255, 0.05);
            box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.15);
        }

        /* Buttons */
        .btn {
            background: linear-gradient(135deg, var(--accent-violet) 0%, #4f46e5 100%);
            color: #ffffff;
            border: none;
            border-radius: 14px;
            padding: 1rem 2rem;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.75rem;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 20px rgba(99, 102, 241, 0.3);
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(99, 102, 241, 0.5);
            background: linear-gradient(135deg, #7c3aed 0%, #6366f1 100%);
        }

        .btn:active {
            transform: translateY(0);
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--glass-border);
            color: var(--text-primary);
            box-shadow: none;
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.2);
            box-shadow: none;
        }

        .btn-danger {
            background: var(--danger);
            box-shadow: 0 4px 20px rgba(239, 68, 68, 0.3);
        }

        .btn-danger:hover {
            background: #dc2626;
            box-shadow: 0 8px 30px rgba(239, 68, 68, 0.5);
        }

        /* Step Editor card styles */
        .plan-section {
            margin-top: 2rem;
            border-top: 1px solid var(--glass-border);
            padding-top: 2rem;
            display: none;
        }

        .section-title {
            font-family: 'Outfit', sans-serif;
            font-size: 1.3rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .steps-list {
            display: flex;
            flex-direction: column;
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .step-card {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 1rem 1.25rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            animation: slideIn 0.3s ease forwards;
            transition: all 0.2s ease;
        }

        .step-card:hover {
            background: rgba(255, 255, 255, 0.04);
            border-color: rgba(255, 255, 255, 0.12);
        }

        .step-number {
            background: rgba(99, 102, 241, 0.15);
            color: var(--accent-cyan);
            font-weight: 600;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.9rem;
        }

        .step-input {
            flex: 1;
            background: transparent;
            border: none;
            border-bottom: 1px solid transparent;
            color: var(--text-primary);
            font-size: 1rem;
            outline: none;
            padding: 0.25rem 0;
            transition: border-color 0.2s ease;
        }

        .step-input:focus {
            border-color: var(--accent-cyan);
        }

        .step-actions {
            display: flex;
            gap: 0.5rem;
        }

        .icon-btn {
            background: transparent;
            border: none;
            cursor: pointer;
            color: var(--text-secondary);
            padding: 0.5rem;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.15s ease;
        }

        .icon-btn:hover {
            color: var(--text-primary);
            background: rgba(255, 255, 255, 0.05);
        }

        .icon-btn.delete-btn:hover {
            color: var(--danger);
            background: rgba(239, 68, 68, 0.1);
        }

        /* Execution Section */
        .execution-section {
            margin-top: 2rem;
            border-top: 1px solid var(--glass-border);
            padding-top: 2rem;
            display: none;
        }

        .status-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }

        .status-badge {
            background: rgba(99, 102, 241, 0.15);
            color: var(--accent-violet);
            padding: 0.35rem 0.85rem;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }

        .status-badge.running {
            background: rgba(34, 211, 238, 0.15);
            color: var(--accent-cyan);
            animation: pulse 2s infinite;
        }

        .status-badge.success {
            background: rgba(16, 185, 129, 0.15);
            color: var(--success);
        }

        .logs-panel {
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            height: 250px;
            overflow-y: auto;
            padding: 1.25rem;
            font-family: monospace;
            font-size: 0.9rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }

        .log-entry {
            border-left: 2px solid var(--accent-violet);
            padding-left: 0.75rem;
            margin-bottom: 0.5rem;
            animation: fadeIn 0.2s ease forwards;
        }

        .log-step {
            color: var(--accent-cyan);
            font-weight: bold;
            margin-bottom: 0.25rem;
        }

        .log-eval {
            color: var(--text-primary);
        }

        .log-goal {
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-top: 0.15rem;
        }

        /* Spinner animation */
        .spinner {
            width: 20px;
            height: 20px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: #ffffff;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }

        @keyframes slideIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        /* Scrollbar styles */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: transparent;
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.2);
        }
    </style>
</head>
<body>
    <div class="bg-glow glow-1"></div>
    <div class="bg-glow glow-2"></div>

    <div class="container">
        <header>
            <h1>Web Automation Hub</h1>
            <p class="subtitle">Enter a task, customize the steps, and watch the agent run</p>
        </header>

        <div class="panel">
            <div class="input-group">
                <label for="prompt">What would you like the agent to do?</label>
                <textarea id="prompt" placeholder="Example: Go to LinkedIn, log in with credentials, and like the first post."></textarea>
                <button id="generate-btn" class="btn" onclick="generatePlan()">
                    Generate Plan
                </button>
            </div>

            <!-- Proposed Plan Editing Section -->
            <div id="plan-section" class="plan-section">
                <div class="section-title">
                    <span>Proposed Execution Plan</span>
                    <button class="btn btn-secondary" style="padding: 0.5rem 1rem; font-size: 0.9rem;" onclick="addStep()">
                        + Add Step
                    </button>
                </div>
                <div id="steps-list" class="steps-list">
                    <!-- Steps will be injected dynamically -->
                </div>
                <div style="display: flex; gap: 1rem;">
                    <button id="execute-btn" class="btn" style="flex: 1;" onclick="executePlan()">
                        Start Execution
                    </button>
                    <button class="btn btn-secondary" onclick="resetUI()">
                        Cancel
                    </button>
                </div>
            </div>

            <!-- Execution Status Section -->
            <div id="execution-section" class="execution-section">
                <div class="status-header">
                    <span class="section-title" style="margin-bottom: 0;">Execution Progress</span>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <button id="stop-btn" class="btn btn-secondary" style="display: none; padding: 0.35rem 0.85rem; font-size: 0.85rem; background: rgba(239, 68, 68, 0.1); color: var(--danger); border-color: rgba(239, 68, 68, 0.3);" onclick="stopAgent()">Stop / Next</button>
                        <span id="status-badge" class="status-badge">Ready</span>
                    </div>
                </div>
                <div id="logs-panel" class="logs-panel">
                    <div style="color: var(--text-secondary);">No logs yet. Waiting for run to start...</div>
                </div>
            </div>

            <!-- Extracted Results Section -->
            <div id="results-section" class="execution-section" style="display: none; margin-top: 1.5rem; border-top: 1px solid var(--glass-border); padding-top: 1.5rem;">
                <div class="status-header">
                    <span class="section-title" style="margin-bottom: 0; color: var(--accent-cyan);">Extracted Content & Results</span>
                </div>
                <div id="results-content" style="background: rgba(255, 255, 255, 0.03); border: 1px solid var(--glass-border); border-radius: 12px; padding: 1.2rem; color: var(--text-primary); font-size: 0.95rem; line-height: 1.6; max-height: 400px; overflow-y: auto;">
                </div>
            </div>
        </div>
    </div>

    <script>
        function escapeHTML(str) {
            if (!str) return "";
            return str.replace(/&/g, "&amp;")
                      .replace(/</g, "&lt;")
                      .replace(/>/g, "&gt;")
                      .replace(/"/g, "&quot;")
                      .replace(/'/g, "&#039;");
        }

        let currentPrompt = "";
        let pollInterval = null;
        let wasStartedThisSession = false;

        async function generatePlan() {
            const promptInput = document.getElementById("prompt");
            const generateBtn = document.getElementById("generate-btn");
            const prompt = promptInput.value.trim ? promptInput.value.trim() : promptInput.value;

            if (!prompt) {
                alert("Please enter a command.");
                return;
            }

            currentPrompt = prompt;
            generateBtn.disabled = true;
            generateBtn.innerHTML = '<div class="spinner"></div> Generating plan...';

            try {
                const response = await fetch("/generate-plan", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ prompt })
                });
                const data = await response.json();
                
                if (data.error) {
                    alert("Error: " + data.error);
                } else {
                    renderPlan(data.steps);
                    document.getElementById("plan-section").style.display = "block";
                }
            } catch (err) {
                alert("Failed to communicate with server: " + err);
            } finally {
                generateBtn.disabled = false;
                generateBtn.innerHTML = 'Generate Plan';
            }
        }

        function renderPlan(steps) {
            const list = document.getElementById("steps-list");
            list.innerHTML = "";
            
            steps.forEach((step, idx) => {
                const card = document.createElement("div");
                card.className = "step-card";
                card.innerHTML = `
                    <div class="step-number">${idx + 1}</div>
                    <input type="text" class="step-input" value="${step.replace(/"/g, '&quot;')}" />
                    <div class="step-actions">
                        <button class="icon-btn delete-btn" onclick="deleteStep(this)" title="Delete Step">
                            <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                                <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </button>
                    </div>
                `;
                list.appendChild(card);
            });
        }

        function deleteStep(btn) {
            const card = btn.closest(".step-card");
            card.remove();
            reorderSteps();
        }

        function addStep() {
            const list = document.getElementById("steps-list");
            const newIndex = list.children.length + 1;
            const card = document.createElement("div");
            card.className = "step-card";
            card.innerHTML = `
                <div class="step-number">${newIndex}</div>
                <input type="text" class="step-input" value="" placeholder="New step description" />
                <div class="step-actions">
                    <button class="icon-btn delete-btn" onclick="deleteStep(this)" title="Delete Step">
                        <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                            <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </button>
                </div>
            `;
            list.appendChild(card);
            card.querySelector(".step-input").focus();
        }

        function reorderSteps() {
            const list = document.getElementById("steps-list");
            Array.from(list.children).forEach((card, idx) => {
                card.querySelector(".step-number").innerText = idx + 1;
            });
        }

        async function executePlan() {
            const list = document.getElementById("steps-list");
            const inputs = list.querySelectorAll(".step-input");
            const steps = Array.from(inputs).map(inp => inp.value.trim()).filter(val => val);

            if (steps.length === 0) {
                alert("Plan must contain at least one step.");
                return;
            }

            const executeBtn = document.getElementById("execute-btn");
            executeBtn.disabled = true;
            wasStartedThisSession = true;
            
            document.getElementById("execution-section").style.display = "block";
            const badge = document.getElementById("status-badge");
            badge.innerText = "Running";
            badge.className = "status-badge running";

            try {
                const response = await fetch("/run-agent", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        prompt: currentPrompt,
                        steps: steps
                    })
                });
                
                const data = await response.json();
                if (data.error) {
                    alert("Error starting agent: " + data.error);
                    badge.innerText = "Error";
                    badge.className = "status-badge";
                    executeBtn.disabled = false;
                } else {
                    // Start status polling
                    if (pollInterval) clearInterval(pollInterval);
                    pollInterval = setInterval(pollStatus, 1000);
                }
            } catch (err) {
                alert("Failed to send run request: " + err);
                badge.innerText = "Error";
                badge.className = "status-badge";
                executeBtn.disabled = false;
            }
        }

        async function pollStatus() {
            try {
                const response = await fetch("/status");
                const data = await response.json();
                
                const badge = document.getElementById("status-badge");
                const logsPanel = document.getElementById("logs-panel");

                if (data.running) {
                    document.getElementById("execution-section").style.display = "block";
                    document.getElementById("execute-btn").disabled = true;
                    document.getElementById("generate-btn").disabled = true;
                    document.getElementById("stop-btn").style.display = "block";
                    badge.innerText = `Running (Step ${data.current_step})`;
                    badge.className = "status-badge running";
                } else {
                    clearInterval(pollInterval);
                    document.getElementById("execute-btn").disabled = false;
                    document.getElementById("generate-btn").disabled = false;
                    document.getElementById("stop-btn").style.display = "none";
                    if (data.success) {
                        badge.innerText = "Completed";
                        badge.className = "status-badge success";
                    } else if (data.error) {
                        badge.innerText = "Failed";
                        badge.className = "status-badge";
                        if (wasStartedThisSession) {
                            alert("Agent run failed: " + data.error);
                            wasStartedThisSession = false;
                        }
                    } else {
                        badge.innerText = "Idle";
                        badge.className = "status-badge";
                    }
                }

                // Render logs
                if (data.logs.length > 0) {
                    logsPanel.innerHTML = "";
                    data.logs.forEach(log => {
                        const entry = document.createElement("div");
                        entry.className = "log-entry";
                        entry.innerHTML = `
                            <div class="log-step">Step ${log.step}</div>
                            <div class="log-eval">Eval: ${log.evaluation || 'Executing action...'}</div>
                            <div class="log-goal">Goal: ${log.next_goal || ''}</div>
                        `;
                        logsPanel.appendChild(entry);
                    });
                    logsPanel.scrollTop = logsPanel.scrollHeight;
                }

                // Render Extracted Results
                const resultsSection = document.getElementById("results-section");
                const resultsContent = document.getElementById("results-content");
                let resultsHTML = "";

                if (data.extracted_content && data.extracted_content.length > 0) {
                    data.extracted_content.forEach((item, index) => {
                        resultsHTML += `<div style="margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px dashed var(--glass-border);">
                            <div style="font-weight: 700; color: var(--accent-cyan); font-size: 0.85rem; margin-bottom: 0.4rem; text-transform: uppercase;">Extraction ${index + 1}</div>
                            <div style="white-space: pre-wrap; font-family: 'Outfit', sans-serif;">${escapeHTML(item)}</div>
                        </div>`;
                    });
                }

                if (data.final_result) {
                    resultsHTML += `<div style="margin-top: 1rem; padding: 1rem; border-radius: 8px; background: rgba(34, 211, 238, 0.05); border: 1px solid rgba(34, 211, 238, 0.15);">
                        <div style="font-weight: 700; color: var(--accent-cyan); font-size: 0.85rem; margin-bottom: 0.4rem; text-transform: uppercase;">Final Outcome</div>
                        <div style="white-space: pre-wrap; font-family: 'Outfit', sans-serif;">${escapeHTML(data.final_result)}</div>
                    </div>`;
                }

                if (resultsHTML) {
                    resultsSection.style.display = "block";
                    resultsContent.innerHTML = resultsHTML;
                } else {
                    resultsSection.style.display = "none";
                }

                // Check for help request
                const helpModal = document.getElementById("help-modal");
                if (data.waiting_for_help) {
                    document.getElementById("help-question-text").innerText = data.help_question;
                    helpModal.style.display = "flex";
                } else {
                    helpModal.style.display = "none";
                }
            } catch (err) {
                console.error("Error polling status: ", err);
            }
        }

        async function submitHelp() {
            const input = document.getElementById("help-reply-input");
            const responseText = input.value.trim();
            if (!responseText) return;
            
            try {
                await fetch("/submit-help", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ response: responseText })
                });
                input.value = "";
                document.getElementById("help-modal").style.display = "none";
            } catch (err) {
                alert("Failed to submit response: " + err);
            }
        }

        function resetUI() {
            document.getElementById("plan-section").style.display = "none";
            document.getElementById("execution-section").style.display = "none";
            document.getElementById("results-section").style.display = "none";
            document.getElementById("results-content").innerHTML = "";
            document.getElementById("prompt").value = "";
            document.getElementById("stop-btn").style.display = "none";
            if (pollInterval) {
                clearInterval(pollInterval);
                pollInterval = null;
            }
        }

        async function stopAgent() {
            try {
                const response = await fetch("/stop-agent", { method: "POST" });
                const data = await response.json();
                console.log(data.status);
            } catch (err) {
                console.error("Failed to request stop: ", err);
            }
        }

        window.addEventListener("DOMContentLoaded", () => {
            // Check status on load to see if agent is already running
            pollStatus();
            pollInterval = setInterval(pollStatus, 1000);
        });
    </script>

    <!-- Human Help Modal -->
    <div id="help-modal" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6); backdrop-filter: blur(10px); z-index: 100; align-items: center; justify-content: center; padding: 2rem;">
        <div class="panel" style="max-width: 500px; width: 100%; border-color: var(--accent-cyan); box-shadow: 0 0 40px rgba(34, 211, 238, 0.2);">
            <h3 style="font-family: 'Outfit', sans-serif; font-size: 1.3rem; font-weight: 700; color: var(--accent-cyan); margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
                <svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                Agent Needs Assistance
            </h3>
            <p id="help-question-text" style="color: var(--text-primary); margin-bottom: 1.5rem; line-height: 1.5;"></p>
            <div class="input-group" style="margin-bottom: 1.5rem;">
                <input type="text" id="help-reply-input" placeholder="Type your response or instructions..." style="width:100%; padding:1rem; border-radius:12px; background:rgba(255,255,255,0.03); border:1px solid var(--glass-border); color:var(--text-primary); outline:none;" />
            </div>
            <button class="btn" style="width: 100%; background: linear-gradient(135deg, var(--accent-cyan) 0%, var(--bg-glow-2) 100%); box-shadow: 0 4px 20px rgba(34, 211, 238, 0.3);" onclick="submitHelp()">
                Submit Response
            </button>
        </div>
    </div>
</body>
</html>"""
    return HTMLResponse(html_content)

async def generate_plan(request):
    try:
        data = await request.json()
        prompt = data.get("prompt", "")
        if not prompt:
            return JSONResponse({"error": "Prompt cannot be empty"}, status_code=400)

        # Single source of truth: the skill files, not a hardcoded prompt.
        # This keeps plan generation consistent with what the execution agent
        # will actually see and do (macro registry, targeting rules, etc.)
        # defined in skills/*.md  no behavior duplicated here.
        skill_prompt = load_skills()

        plan_prompt = (
            f"{skill_prompt}\n\n"
            "<planning_instructions>\n"
            "You are the planning phase of the agent described above. Create a clear, sequential "
            "step-by-step list of actions required to complete the user's task below, strictly "
            "following the rules, macros, and targeting requirements defined in the skills above "
            "(see SUPPORTED ACTIONS and the Macro Registry). Each step should be a single, "
            "concrete action. Do not invent macros or steps that are not covered by the skills. "
            "If the task references credentials, search terms, or target identifiers, carry them "
            "through into the plan exactly as given by the user  never substitute example or "
            "placeholder values of your own.\n"
            "</planning_instructions>\n"
            f"<user_command>\n{prompt}\n</user_command>\n"
            "Respond ONLY with a JSON array of strings representing the steps. Do not include any other text."
        )

        system_msg = SystemMessage(content="You are a web automation planner. Create a sequential step-by-step list of actions.")
        user_msg = UserMessage(content=plan_prompt)
        response = await llm.ainvoke([system_msg, user_msg], output_format=TaskPlan)
        steps = response.completion.steps
        return JSONResponse({"steps": steps})
    except Exception as e:
        return JSONResponse({"steps": [prompt], "warning": str(e)})

async def run_agent(request):
    try:
        if app_state["running"]:
            return JSONResponse({"error": "Agent is already running in the background. Please wait for it to finish."}, status_code=400)

        data = await request.json()
        prompt = data.get("prompt", "")
        steps = data.get("steps", [])
        if not steps:
            return JSONResponse({"error": "Steps cannot be empty"}, status_code=400)

        # Reset app_state
        app_state["running"] = True
        app_state["prompt"] = prompt
        app_state["plan"] = steps
        app_state["logs"] = []
        app_state["current_step"] = 0
        app_state["last_intervention_step"] = 0
        app_state["error"] = None
        app_state["success"] = False
        app_state["waiting_for_help"] = False
        app_state["help_question"] = None
        app_state["help_response"] = None
        app_state["extracted_content"] = []
        app_state["final_result"] = None

        approved_plan_str = "\n".join(f"Step {idx+1}: {step}" for idx, step in enumerate(steps))

        skill_prompt = load_skills()

        full_task = (
            f"{skill_prompt}\n\n"
            "<user_command>\n"
            f"{prompt}\n"
            "</user_command>\n"
            "<execution_plan>\n"
            f"{approved_plan_str}\n"
            "</execution_plan>\n"
            "Please execute the user command by strictly following the execution plan and the skills provided."
        )

        # This extension carries ONLY output-format/schema constraints, which are a
        # technical contract with the calling code (not agent behavior/policy).
        # All behavior, macro usage, retry policy, and human-in-the-loop rules
        # live exclusively in skills/*.md and are loaded via `skill_prompt` above.
        # Do not add behavioral rules here  edit the relevant skill file instead.
        system_message_extension = (
            "<json_schema>\n"
            "IMPORTANT: You must output ONLY valid JSON matching this schema:\n"
            "{\n"
            '  "evaluation_previous_goal": "brief analysis of previous action",\n'
            '  "memory": "chronological checklist of successfully completed steps (e.g., \'COMPLETED: Step 1, Step 2. CURRENT: Step 3\')",\n'
            '  "next_goal": "brief description of next goal",\n'
            '  "action": [\n'
            '    {"navigate": {"url": "https://www.linkedin.com/login"}}\n'
            '  ]\n'
            "}\n"
            "Do not include any other keys. Make sure 'action' is a non-empty list.\n"
            "</json_schema>\n"
            "<action_rules>\n"
            "CRITICAL: When using click, scroll, or any other element interaction, the 'index' MUST be an integer >= 1. NEVER use index 0.\n"
            "</action_rules>\n"
            "<output_format>\n"
            "Do not wrap your output in markdown code blocks. Output the raw JSON text directly.\n"
            "</output_format>"
        )

        from browser_use import Agent

        async def step_callback(state, output, step_number):
            app_state["current_step"] = step_number
            app_state["logs"].append({
                "step": step_number,
                "evaluation": output.evaluation_previous_goal,
                "memory": output.memory,
                "next_goal": output.next_goal
            })
            
            # Update extracted content in real-time
            if hasattr(agent, "history") and agent.history:
                extracted = agent.history.extracted_content()
                if extracted:
                    app_state["extracted_content"] = extracted

            if app_state.get("stop_requested"):
                app_state["stop_requested"] = False
                app_state["waiting_for_help"] = True
                app_state["help_question"] = "⏹ Agent stopped manually. What would you like me to do next? (Type 'stop' or 'exit' to end the session)"
                app_state["help_response"] = None

                while app_state["help_response"] is None:
                    await asyncio.sleep(0.5)

                response = app_state["help_response"]
                app_state["waiting_for_help"] = False
                app_state["help_question"] = None
                app_state["help_response"] = None

                # Inject is_done=True to make agent.run() return cleanly right now.
                # The execute() loop will then check pending_new_task and restart.
                if agent.history.history:
                    agent.history.history[-1].result.append(ActionResult(
                        is_done=True,
                        success=True,
                        extracted_content="[STOP] User interrupted the agent."
                    ))

                if response.strip().lower() in ["stop", "exit", "done", "quit"]:
                    app_state["pending_new_task"] = None  # Clean exit — no restart
                else:
                    app_state["pending_new_task"] = response  # Restart with this task

            # Auto-request help if the agent experiences consecutive action failures
            last_intervention = app_state.get("last_intervention_step", 0)
            consecutive_failures = 0
            if hasattr(agent, "history") and agent.history.history:
                for idx, item in enumerate(reversed(agent.history.history)):
                    step_idx = len(agent.history.history) - idx
                    if step_idx <= last_intervention:
                        break
                    # Check execution errors
                    has_error = any(getattr(r, "error", None) is not None for r in item.result)
                    # Check LLM self-eval text for failure keywords
                    if not has_error and item.model_output:
                        eval_str = (getattr(item.model_output, "evaluation_previous_goal", "") or "").lower()
                        if any(k in eval_str for k in ["fail", "error", "stale", "cannot", "could not", "unable"]):
                            has_error = True
                            
                    if has_error:
                        consecutive_failures += 1
                    else:
                        break

            if consecutive_failures >= 2:
                # Collect actual failure reasons to present to the user
                failure_reasons = []
                for idx, item in enumerate(reversed(agent.history.history)):
                    step_idx = len(agent.history.history) - idx
                    if step_idx <= last_intervention:
                        break
                    # Get errors from action results
                    errors = [getattr(r, "error", "") for r in item.result if getattr(r, "error", None)]
                    if errors:
                        failure_reasons.extend(errors)
                    elif item.model_output:
                        eval_str = getattr(item.model_output, "evaluation_previous_goal", "")
                        if eval_str:
                            failure_reasons.append(eval_str)
                    if len(failure_reasons) >= 2:
                        break
                
                reason_bullets = "\n".join(f"- {r}" for r in failure_reasons[:2])

                app_state["waiting_for_help"] = True
                app_state["help_question"] = (
                    f"The agent has failed {consecutive_failures} consecutive steps.\n"
                    f"Recent issues/errors:\n{reason_bullets}\n\n"
                    f"Please provide guidance or correct the path:"
                )
                app_state["help_response"] = None

                while app_state["help_response"] is None:
                    await asyncio.sleep(0.5)

                response = app_state["help_response"]
                app_state["waiting_for_help"] = False
                app_state["help_question"] = None
                app_state["help_response"] = None

                # Mark this step as the last human intervention step
                app_state["last_intervention_step"] = step_number

                if len(agent.history.history) > 3:
                    agent.history.history = [agent.history.history[0], agent.history.history[-1]]

                if agent.history.history:
                    from browser_use.agent.views import ActionResult
                    agent.history.history[-1].result.append(ActionResult(
                        is_done=False,
                        extracted_content=f"CRITICAL OVERRIDE DIRECTIVE FROM USER: {response}. Forget previous failures and execute this command immediately."
                    ))

        # Build the agent factory so execute() can restart it with a new task
        def make_agent(task_str):
            return Agent(
                task=task_str,
                llm=llm,
                browser=browser,
                use_vision=False,
                use_thinking=False,
                extend_system_message=system_message_extension,
                register_new_step_callback=step_callback,
                controller=controller
            )

        agent = make_agent(full_task)

        async def execute():
            nonlocal agent
            while True:
                app_state["pending_new_task"] = None
                try:
                    history = await agent.run(max_steps=1000)
                    if history:
                        app_state["extracted_content"] = history.extracted_content()
                        app_state["final_result"] = history.final_result()
                except Exception as e:
                    app_state["error"] = str(e)
                    break

                # Check if the stop button injected a new task to restart with
                new_task_text = app_state.get("pending_new_task")
                if not new_task_text:
                    # Natural completion — trust the agent's own `done(success=...)` verdict
                    # instead of assuming success just because no Python exception was raised.
                    # is_successful() is None if the agent never reached a `done` call at all
                    # (e.g. it stalled or ran out of steps) — treat that as failure too.
                    outcome = history.is_successful() if history else None
                    app_state["success"] = bool(outcome)
                    if not outcome:
                        app_state["error"] = app_state["final_result"] or "L'agent s'est arrêté sans accomplir la tâche (aucun done(success=True))."
                    break

                # Restart: build a fresh agent with the redirected task
                app_state["logs"].append({
                    "step": app_state["current_step"],
                    "evaluation": f"Restarting with new task: {new_task_text}",
                    "memory": "",
                    "next_goal": new_task_text
                })
                app_state["last_intervention_step"] = 0
                app_state["pending_new_task"] = None

                redirected_task = (
                    f"{skill_prompt}\n\n"
                    "<user_command>\n"
                    f"{new_task_text}\n"
                    "</user_command>\n"
                    "Please execute this new task immediately."
                )
                agent = make_agent(redirected_task)
                continue  # Run the new agent

            app_state["running"] = False

        # Run execution asynchronously in background
        asyncio.create_task(execute())

        return JSONResponse({"status": "started"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

async def get_status(request):
    return JSONResponse(app_state)

async def submit_help(request):
    try:
        data = await request.json()
        response_text = data.get("response", "")
        app_state["help_response"] = response_text
        return JSONResponse({"status": "submitted"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

routes = [
    Route("/", homepage, methods=["GET"]),
    Route("/generate-plan", generate_plan, methods=["POST"]),
    Route("/run-agent", run_agent, methods=["POST"]),
    Route("/stop-agent", lambda r: (app_state.update({"stop_requested": True}), JSONResponse({"status": "stop requested"}))[1], methods=["POST"]),
    Route("/status", get_status, methods=["GET"]),
    Route("/submit-help", submit_help, methods=["POST"])
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
]

app = Starlette(routes=routes, middleware=middleware)

if __name__ == "__main__":
    import socket
    port = 8000
    print(f"Starting Web Automation Hub server at http://localhost:{port} ...")
    from actions import llm_provider_log_message
    print(llm_provider_log_message)
    uvicorn.run(app, host="0.0.0.0", port=port)
