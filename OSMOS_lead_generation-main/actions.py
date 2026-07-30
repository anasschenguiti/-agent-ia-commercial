import asyncio
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

# Set up logging to a local file for debugging purposes
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("server.log", mode="a"),
        logging.StreamHandler()
    ]
)

from pydantic import BaseModel
from browser_use.llm.messages import SystemMessage, UserMessage
from browser_use import Agent, Browser
from browser_use.llm.ollama.chat import ChatOllama

class TaskPlan(BaseModel):
    steps: list[str]

# Monkeypatch BrowserSession to re-register standard event handlers on event_bus reassignment (fixes loop execution issues)
from browser_use.browser.session import BrowserSession
from browser_use.browser.watchdog_base import BaseWatchdog
from browser_use.browser.events import (
    BrowserStartEvent, BrowserStopEvent, NavigateToUrlEvent,
    SwitchTabEvent, TabCreatedEvent, TabClosedEvent,
    AgentFocusChangedEvent, FileDownloadedEvent, CloseTabEvent
)

_original_post_init = BrowserSession.model_post_init
def _patched_post_init(self, *args, **kwargs):
    _original_post_init(self, *args, **kwargs)
    self._post_init_done = True
BrowserSession.model_post_init = _patched_post_init

_original_setattr = BrowserSession.__setattr__
def _patched_setattr(self, name, value):
    _original_setattr(self, name, value)
    if name == 'event_bus' and value is not None and getattr(self, '_post_init_done', False):
        try:
            BaseWatchdog.attach_handler_to_session(self, BrowserStartEvent, self.on_BrowserStartEvent)
            BaseWatchdog.attach_handler_to_session(self, BrowserStopEvent, self.on_BrowserStopEvent)
            BaseWatchdog.attach_handler_to_session(self, NavigateToUrlEvent, self.on_NavigateToUrlEvent)
            BaseWatchdog.attach_handler_to_session(self, SwitchTabEvent, self.on_SwitchTabEvent)
            BaseWatchdog.attach_handler_to_session(self, TabCreatedEvent, self.on_TabCreatedEvent)
            BaseWatchdog.attach_handler_to_session(self, TabClosedEvent, self.on_TabClosedEvent)
            BaseWatchdog.attach_handler_to_session(self, AgentFocusChangedEvent, self.on_AgentFocusChangedEvent)
            BaseWatchdog.attach_handler_to_session(self, FileDownloadedEvent, self.on_FileDownloadedEvent)
            BaseWatchdog.attach_handler_to_session(self, CloseTabEvent, self.on_CloseTabEvent)
        except Exception:
            pass
BrowserSession.__setattr__ = _patched_setattr

import platform
import sys
import functools
from types import ModuleType
from browser_use.dom.views import SerializedDOMState
from browser_use.tools.registry.service import Registry
from browser_use import Controller

# -------------------------------------------------------------
# ADDITIONAL MONKEY-PATCHES FOR DOM EXTRACTION & PLAYWRIGHT CONTEXT INJECTION
# -------------------------------------------------------------

# 1. Dynamic Mock for browser_use.browser.context to support BrowserContextConfig
context_module = ModuleType("browser_use.browser.context")
class BrowserContextConfig:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
context_module.BrowserContextConfig = BrowserContextConfig
sys.modules["browser_use.browser.context"] = context_module

# Global variable to hold token cap limit
MAXIMUM_EXTRACT_CONTENT_LENGTH = 6000

# 2. Patch BrowserSession.__init__ to handle custom config parameters
_original_session_init = BrowserSession.__init__
def _patched_session_init(self, *args, **kwargs):
    global MAXIMUM_EXTRACT_CONTENT_LENGTH
    # Extract config to avoid Pydantic validation errors
    max_len = kwargs.pop("maximum_extract_content_length", None)
    context_cfg = kwargs.pop("context_config", None)
    
    if context_cfg:
        kwargs["wait_for_network_idle_page_load_time"] = getattr(context_cfg, "wait_for_network_idle_page_load_time", 2.0)
        kwargs["minimum_wait_page_load_time"] = getattr(context_cfg, "minimum_wait_page_load_time", 1.5)
        max_len_cfg = getattr(context_cfg, "maximum_extract_content_length", None)
        if max_len_cfg is not None:
            max_len = max_len_cfg
            
    _original_session_init(self, *args, **kwargs)
    
    if max_len is not None:
        MAXIMUM_EXTRACT_CONTENT_LENGTH = max_len
        object.__setattr__(self, "maximum_extract_content_length", max_len)

BrowserSession.__init__ = _patched_session_init

# 3. Patch SerializedDOMState.llm_representation removed to prevent cutting off lower page elements

# 4. Disable BrowserProfile's automatic "copy profile to a temp dir" behavior.
# browser_use silently copies user_data_dir into a fresh tempfile.mkdtemp() directory on every
# launch (see BrowserProfile._copy_profile in browser_use/browser/profile.py) as a safety measure
# against concurrent Chrome instances locking the same profile. Since this Hub always runs a single
# dedicated automation Chrome instance against chrome_profile/, that safety copy is unwanted: it is
# what caused every run to start from a throwaway "/tmp/browser-use-user-data-dir-..." profile and
# lose the LinkedIn session on each restart. Disabling it makes Chrome launch directly against
# chrome_profile_path, so cookies/localStorage written during a run persist for the next run.
from browser_use.browser.profile import BrowserProfile
BrowserProfile._copy_profile = lambda self: None

# 5. Give Chrome more time to open its CDP debug port on first launch.
# browser_use hardcodes a 30s timeout waiting for the CDP port (LocalBrowserWatchdog._wait_for_cdp_url)
# before giving up on the whole browser session. On Windows, the *first* execution of a given Chrome/
# Chromium binary can take longer than that if antivirus does a synchronous on-access scan of the
# executable (observed: manual launch of the same binary/profile took ~2s once already "warmed", but
# the very first automated launch timed out at 30s). Widening this only affects the one-time wait for
# the debug port to open, not normal page/action timeouts.
import browser_use.browser.watchdogs.local_browser_watchdog as _local_browser_watchdog
_original_wait_for_cdp_url = _local_browser_watchdog.LocalBrowserWatchdog._wait_for_cdp_url
async def _patched_wait_for_cdp_url(port, timeout: float = 90):
    return await _original_wait_for_cdp_url(port, timeout=timeout)
_local_browser_watchdog.LocalBrowserWatchdog._wait_for_cdp_url = staticmethod(_patched_wait_for_cdp_url)

# Initialize the shared Controller
controller = Controller()

# -------------------------------------------------------------
# LINKEDIN CONTROLLER MACROS
# -------------------------------------------------------------
@controller.action(description="Like the first LinkedIn post on the feed. This is a macro action specifically for LinkedIn.")
async def like_linkedin_post(browser_session: BrowserSession) -> str:
    try:
        page = await browser_session.must_get_current_page()
        
        # Target the first visible feed item container
        post = page.locator("div[data-urn], div.feed-shared-update-v2").first
        
        # Within that specific post container, locate the reaction button
        like_btn = post.locator("button[aria-label^='React Like'], button[aria-label^='Like ']")
        
        if not await like_btn.count():
            return "Failed: Could not find any visible Like button on the first post."
            
        # Inspect the state before interacting
        aria_pressed = await like_btn.get_attribute("aria-pressed")
        aria_label = await like_btn.get_attribute("aria-label") or ""
        aria_label_lower = aria_label.strip().lower()
        
        if aria_pressed == "true" or aria_label_lower.startswith("un-react") or aria_label_lower.startswith("unlike"):
            return "Success: Already liked"
            
        await like_btn.click()
        return "Success: Clicked"
    except Exception as e:
        return f"Failed: Error clicking Like button: {str(e)}"

@controller.action(description="Login to LinkedIn securely and robustly. Use this immediately when you need to connect to LinkedIn.")
async def login_linkedin(email: str, password: str, browser_session: BrowserSession) -> str:
    try:
        page = await browser_session.get_current_page()
        await page.goto("https://www.linkedin.com/login")
        await page.wait_for_selector("#username", timeout=10000)
        await page.fill("#username", email)
        await page.fill("#password", password)
        await page.click("button[type='submit']")
        
        # Wait a bit to let navigation or CAPTCHA appear
        await asyncio.sleep(3)
        return "Login credentials submitted. If you see a CAPTCHA, call request_human_help."
    except Exception as e:
        return f"Failed to login: {str(e)}"

@controller.action(description="Directly navigate to the LinkedIn messaging page.")
async def navigate_to_linkedin_messaging(browser_session: BrowserSession) -> str:
    try:
        await browser_session.navigate_to("https://www.linkedin.com/messaging/")
        return "Success: Navigated to LinkedIn messaging page."
    except Exception as e:
        return f"Failed: Navigation failed with error: {str(e)}"

@controller.action(description="Search for a company on LinkedIn using the search URL.")
async def search_linkedin_company(company_name: str, browser_session: BrowserSession) -> str:
    try:
        page = await browser_session.get_current_page()
        import urllib.parse
        encoded_name = urllib.parse.quote(company_name)
        url = f"https://www.linkedin.com/search/results/companies/?keywords={encoded_name}"
        await page.goto(url)
        
        import asyncio
        await asyncio.sleep(4) # Wait for page to settle
        
        try:
            # Attempt to click the first company profile link in the search results
            # The selector looks for an anchor tag with href containing /company/
            company_link_selector = 'a.app-aware-link[href*="linkedin.com/company/"]'
            await page.wait_for_selector(company_link_selector, timeout=5000)
            await page.click(company_link_selector)
            await asyncio.sleep(4) # Wait for the company page to load
            return f"Success: Navigated directly to the profile page of {company_name}."
        except Exception as e:
            return f"Partial Success: Navigated to search results for {company_name}, but could not auto-click the first result. Please click it manually. Error: {str(e)}"
    except Exception as e:
        return f"Failed: Navigation failed with error: {str(e)}"

# 1. Configure the browser to use your existing local Chrome profile
# To prevent conflicts with your active Chrome browser (since the Web UI requires a running browser),
# we use a dedicated automation Chrome profile directory within the project folder.
# This prevents lock errors and keeps your automation session clean.
# Absolute + fixed so the persisted session (LinkedIn login, cookies) is found regardless of the
# working directory app.py/actions.py is launched from, and is never recreated between launches.
chrome_profile_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_profile")
os.makedirs(chrome_profile_path, exist_ok=True)
logging.getLogger(__name__).info(f"🗂️  Chrome persistent profile directory (user_data_dir): {chrome_profile_path}")
print(f"🗂️  Chrome persistent profile directory (user_data_dir): {chrome_profile_path}")

from browser_use.browser.context import BrowserContextConfig

context_config = BrowserContextConfig(
    wait_for_network_idle_page_load_time=1.0,
    minimum_wait_page_load_time=0.5,
    maximum_extract_content_length=12000,
    locale="en-US"
)

browser = Browser(
    headless=False,  # Keep visible so you can monitor what the agent is doing
    user_data_dir=chrome_profile_path,
    keep_alive=True,
    context_config=context_config
)

# Confirm what Chrome will actually be launched with (post BrowserProfile resolution),
# so a stale/temp path here is immediately visible in the startup logs instead of only
# showing up later as "you got logged out again".
_resolved_user_data_dir = str(browser.browser_profile.user_data_dir)
logging.getLogger(__name__).info(f"✅ Resolved Chrome user_data_dir actually in use: {_resolved_user_data_dir}")
print(f"✅ Resolved Chrome user_data_dir actually in use: {_resolved_user_data_dir}")
if "temp" in _resolved_user_data_dir.lower() or "tmp" in _resolved_user_data_dir.lower():
    logging.getLogger(__name__).warning("⚠️ user_data_dir resolved to a temp directory — session will NOT persist across restarts!")

# 2. Initialize the local model via Ollama using the native browser-use wrapper
# We expand the context window (num_ctx) so the model can process the web page DOM
llm_provider = os.environ.get("LLM_PROVIDER", "ollama").lower()
llm_provider_log_message = ""

if llm_provider == "groq":
    from browser_use.llm.groq.chat import ChatGroq
            
    groq_api_key = os.environ.get("GROQ_API_KEY", "")
    # We choose openai/gpt-oss-120b as the default Groq model
    # for tool-use and navigation reasoning, while being extremely fast.
    groq_model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
    
    if not groq_api_key:
        print("WARNING: GROQ_API_KEY is missing. Falling back to Ollama.")
        llm_provider = "ollama"
    else:
        llm = ChatGroq(
            model=groq_model,
            temperature=0.0,
            api_key=groq_api_key
        )
        llm_provider_log_message = f"🤖 LLM Provider actif : GROQ ({groq_model})"

if llm_provider == "ollama":
    llm = ChatOllama(
        model="qwen3:8b",
        timeout=180.0,  # Increase from 300.0 or standard limits to give processing overhead
        ollama_options={
            "temperature": 0.0,
            "num_ctx": 16000  # Lowering from 32k to 16k directly cuts processing times in half
        }
    )
    llm_provider_log_message = "🤖 LLM Provider actif : OLLAMA (qwen3:8b)"


async def ask_agent(prompt):
    """Initializes and runs the agent for a specific manual command."""
    from skills.loader import load_skills
    skill_prompt = load_skills()

    plan_prompt = (
        f"You are a web automation planner. Based on the following skills:\n\n"
        f"{skill_prompt}\n\n"
        f"Create a clear, sequential step-by-step list of actions required to complete the user's task.\n"
        f"Task: {prompt}\n"
        f"Respond ONLY with a JSON array of strings representing the steps. Do not include any other text."
    )
    
    print("\n[Planning] Querying local LLM to generate the execution plan...")
    try:
        system_msg = SystemMessage(content="You are a web automation planner. Create a sequential step-by-step list of actions.")
        user_msg = UserMessage(content=plan_prompt)
        response = await llm.ainvoke([system_msg, user_msg], output_format=TaskPlan)
        plan = response.completion.steps
    except Exception as e:
        print(f"[Warning] Failed to auto-generate plan: {e}")
        # Default fallback to original task description
        plan = [prompt]
        
    print("\n=== Generated Execution Plan ===")
    for idx, step in enumerate(plan):
        print(f"  {idx+1}. {step}")
    print("================================\n")
    
    print("Review and correct the plan. Press Enter to accept each step as-is,")
    print("type new text to replace it, 'del' to delete it, or 'add <text>' to insert a new step after it.")
    print("-------------------------------------------------------------------------------------------")
    
    i = 0
    while i < len(plan):
        step_text = plan[i]
        user_input = input(f"Step {i+1} of {len(plan)} [Current: \"{step_text}\"]\nAction: ").strip()
        
        if not user_input:
            # Accepted step as is
            i += 1
        elif user_input.lower() == 'del':
            plan.pop(i)
            if not plan:
                plan = [prompt]
            # Show updated plan
            print("\nUpdated Plan:")
            for idx, step in enumerate(plan):
                print(f"  {idx+1}. {step}")
            print()
        elif user_input.lower().startswith('add '):
            new_step = user_input[4:].strip()
            plan.insert(i + 1, new_step)
            print("\nUpdated Plan:")
            for idx, step in enumerate(plan):
                print(f"  {idx+1}. {step}")
            print()
            i += 1
        else:
            # Edit step
            plan[i] = user_input
            print("\nUpdated Plan:")
            for idx, step in enumerate(plan):
                print(f"  {idx+1}. {step}")
            print()
            i += 1
            
    print("\n=== Final Approved Plan ===")
    for idx, step in enumerate(plan):
        print(f"  {idx+1}. {step}")
    print("===========================\n")
    
    confirm = input("Execute this plan? (Y/n): ").strip().lower()
    if confirm == 'n':
        print("Execution cancelled.")
        return
        
    approved_plan_str = "\n".join(f"Step {idx+1}: {step}" for idx, step in enumerate(plan))
    
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
    
    system_message_extension = (
        "<json_schema>\n"
        "IMPORTANT: You must output ONLY valid JSON matching this schema:\n"
        "{\n"
        '  "evaluation_previous_goal": "brief analysis of previous action",\n'
        '  "memory": "chronological checklist of successfully completed steps (e.g., \'COMPLETED: Step 1, Step 2. CURRENT: Step 3\')",\n'
        '  "next_goal": "brief description of next goal",\n'
        '  "action": [\n'
        '    {"login_linkedin": {"email": "...", "password": "..."}}\n'
        '  ]\n'
        "}\n"
        "Do not include any other keys. Make sure 'action' is a non-empty list.\n"
        "</json_schema>\n"
        "<action_rules>\n"
        "CRITICAL: When using click, scroll, or any other element interaction, the 'index' MUST be an integer >= 1. NEVER use index 0.\n"
        "</action_rules>\n"
        "<macro_handling_rules>\n"
        "Whenever the task requires logging into LinkedIn with provided credentials, you MUST call the custom tool login_linkedin with the email and password as its very first action. NEVER perform login via separate navigate/click/type actions on the accessibility tree — that risks navigating to the login page and then moving on without ever submitting the credentials. Do not call any other LinkedIn macro (e.g. search_linkedin_company) before login_linkedin has been called and has returned its result for this task, unless the task explicitly does not require login.\n"
        "If you called request_human_help because LinkedIn credentials were missing from the task input, its result will be a string starting with \"User replied: \" followed by whatever the human typed (the exact format may vary). Three cases: (1) it contains a usable email/password -> your VERY NEXT action MUST be login_linkedin with them, do not ask again. (2) it explicitly tells you to proceed/continue without logging in -> do NOT ask again and do NOT stop; perform every part of the task that does not require authentication, and only for the specific sub-step that inherently requires login (e.g. clicking Connect/Message/Like) call done with success=False explaining that step was skipped due to missing credentials. (3) the reply has neither credentials nor a clear instruction -> you may ask request_human_help once more, then if still unusable call done with success=False. In no case should you just stop without calling done.\n"
        "If the custom tool like_linkedin_post returns a string containing \"Success: Clicked\" OR \"Success: Already liked\", the task is 100% completed. You must record this success in your memory and move directly to the next step. You must NEVER call the macro twice in a row on the same page.\n"
        "If the custom like_linkedin_post tool returns a 'Failed' string, you must execute a small 'scroll_down' action exactly ONCE to load the feed layout elements cleanly into the DOM, then execute the like_linkedin_post tool a second time. Do not attempt to click random screen indices manually.\n"
        "</macro_handling_rules>\n"
        "<output_format>\n"
        "Do not wrap your output in markdown code blocks. Output the raw JSON text directly.\n"
        "</output_format>"
    )
    
    agent = Agent(
        task=full_task,
        llm=llm,
        browser=browser,
        use_vision=False,    # Disable vision (screenshots) to significantly speed up local LLM processing
        use_thinking=False,  # Disable inner-monologue thinking to speed up text generation
        extend_system_message=system_message_extension,
        controller=controller,
    )
    
    await agent.run()

async def main():
    print("\n--- LinkedIn Accessibility Agent (Manual Prompt Mode) ---")
    print("Type your command. If your command has multiple lines, press Enter on a blank line to submit.")
    print("Type 'exit' or 'quit' to stop the program.\n")
    
    try:
        while True:
            # Capture manual text input (supporting multi-line pastes)
            print("Enter command (press Enter on an empty line to submit):")
            lines = []
            while True:
                try:
                    line = input()
                    if not line and len(lines) > 0:
                        break
                    if not line and len(lines) == 0:
                        # Allow exit/quit directly
                        continue
                    if line.strip().lower() in ['exit', 'quit']:
                        lines = [line]
                        break
                    lines.append(line)
                except EOFError:
                    break
            user_prompt = "\n".join(lines).strip()
            
            if user_prompt.lower() in ['exit', 'quit']:
                print("Shutting down agent...")
                break
                
            if not user_prompt:
                continue
                
            # Run the asynchronous agent loop for this specific command
            await ask_agent(user_prompt)
            print("\nAction cycle complete. Ready for next command.\n")
            
    finally:
        # Ensure the browser instance is closed properly on exit
        await browser.close()

if __name__ == "__main__":
    # Run the main loop
    asyncio.run(main())