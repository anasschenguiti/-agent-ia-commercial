import os
from flask import Flask, render_template, request, redirect, url_for, flash
from database import init_db
from models import Campaign, db

from dotenv import load_dotenv

# Load env variables
load_dotenv(override=True)

from engines.llm_engine import extract_company_info
from engines.hub_client import HubClient

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'osmos-secret-key-change-in-production')

# Database Initialization
init_db(app)

USE_REAL_ACTIONNEUR = os.environ.get('USE_REAL_ACTIONNEUR', 'false').lower() == 'true'
hub_client = HubClient("http://127.0.0.1:8000", request_timeout=300.0)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', use_real_actionneur=USE_REAL_ACTIONNEUR)

@app.route('/analyze', methods=['POST'])
def analyze():
    company_name = request.form.get('company_name', 'Inconnu')
    linkedin_email = request.form.get('linkedin_email')
    linkedin_password = request.form.get('linkedin_password')
    
    info = extract_company_info(company_name, hub_client, USE_REAL_ACTIONNEUR, linkedin_email, linkedin_password)
    
    # Credentials are no longer referenced after this point

    
    is_fallback = "Fallback" in info.get("sector", "") or "Fallback" in info.get("size", "") or "Fallback" in info.get("description", "")
    
    if USE_REAL_ACTIONNEUR and is_fallback:
        flash("⚠️ Extraction réelle indisponible, données de démonstration utilisées", "warning")
    elif not USE_REAL_ACTIONNEUR:
        flash("Mode simulé : Données de démonstration générées", "info")
    else:
        flash("Extraction réussie depuis LinkedIn !", "success")
        
    campaign = Campaign(
        company_name=company_name,
        company_sector=info.get('sector', ''),
        company_size=info.get('size', ''),
        company_description=info.get('description', ''),
        linkedin_url=info.get('linkedin_url', ''),
        value_proposition=info.get('value_proposition', '')
    )
    
    db.session.add(campaign)
    db.session.commit()
    
    return redirect(url_for('analysis', campaign_id=campaign.id))

import requests

@app.route('/hub-help', methods=['GET', 'POST'])
def hub_help():
    """Route de secours pour envoyer un code 2FA au Hub sans utiliser le terminal."""
    if request.method == 'POST':
        user_response = request.form.get('response')
        try:
            requests.post("http://127.0.0.1:8000/submit-help", json={"response": user_response}, timeout=5)
            return '''
            <div style="font-family:sans-serif; text-align:center; padding:50px;">
                <h2 style="color: #10b981;">✅ Code envoyé au Hub !</h2>
                <p>Vous pouvez fermer cet onglet et revenir à l'onglet principal.</p>
            </div>
            '''
        except Exception as e:
            return f"<p style='color:red;'>Erreur : {e}</p>"
        
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Aide au Hub (2FA)</title>
        <style>
            body { font-family: 'Inter', sans-serif; background: #0f172a; color: white; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .box { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); padding: 40px; border-radius: 16px; text-align: center; width: 400px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
            input { padding: 12px; font-size: 16px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.2); margin-bottom: 20px; width: 90%; background: transparent; color: white; outline: none; text-align: center; }
            input:focus { border-color: #6366f1; }
            button { background: #6366f1; color: white; border: none; padding: 12px 24px; font-size: 16px; font-weight: 600; border-radius: 8px; cursor: pointer; width: 100%; transition: all 0.2s; }
            button:hover { background: #4f46e5; transform: translateY(-2px); }
        </style>
    </head>
    <body>
        <div class="box">
            <h2 style="margin-top:0;">🔒 Vérification LinkedIn</h2>
            <p style="color: #9ca3af; margin-bottom: 25px;">Le navigateur a besoin de votre code de sécurité reçu par email ou SMS pour continuer.</p>
            <form method="POST">
                <input type="text" name="response" placeholder="Ex: 123456" required autocomplete="off"><br>
                <button type="submit">Débloquer le Hub</button>
            </form>
        </div>
    </body>
    </html>
    '''

from engines.search_engine import find_prospects_for_campaign, ExtractionError
from engines.ahp_topsis import rank_prospects
import json

@app.route('/analysis/<int:campaign_id>', methods=['GET'])
def analysis(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    return render_template('analysis.html', campaign=campaign, step=1)
    
@app.route('/find_prospects/<int:campaign_id>', methods=['POST'])
def find_prospects(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    
    if not USE_REAL_ACTIONNEUR:
        flash("Mode simulé activé : l'extraction réelle n'est pas activée. Veuillez activer USE_REAL_ACTIONNEUR.", "warning")
        return redirect(url_for('analysis', campaign_id=campaign_id))
        
    try:
        raw_prospects = find_prospects_for_campaign(campaign, hub_client)
        
        # S'il y a succès, rank_prospects classe les prospects
        ranked_prospects, ahp_result = rank_prospects(raw_prospects)
        
        from models import Prospect
        for rp in ranked_prospects:
            p = Prospect(
                campaign_id=campaign.id,
                prospect_info=json.dumps(rp),
                topsis_score=rp.get("topsis_score"),
                topsis_rank=rp.get("topsis_rank"),
                priority_label=rp.get("priority_label")
            )
            db.session.add(p)
            
        db.session.commit()
        flash(f"{len(ranked_prospects)} prospects extraits et classés avec succès.", "success")
        return redirect(url_for('prospects', campaign_id=campaign.id))
        
    except ExtractionError as e:
        flash(f"Échec de l'extraction : {str(e)}", "error")
        return redirect(url_for('analysis', campaign_id=campaign_id))

@app.route('/prospects/<int:campaign_id>', methods=['GET'])
def prospects(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    from models import Prospect
    # Only active prospects, ordered by their score
    db_prospects = Prospect.query.filter_by(campaign_id=campaign_id, is_active=True).order_by(Prospect.topsis_score.desc()).all()
    
    prospects_list = []
    for i, p in enumerate(db_prospects):
        try:
            info = json.loads(p.prospect_info)
            info['id'] = p.id
            # Re-adjust rank purely for display
            info['topsis_rank'] = i + 1
            prospects_list.append(info)
        except Exception:
            pass
            
    from engines.ahp_topsis import calculate_ahp_weights
    ahp_result = calculate_ahp_weights()

    return render_template('prospects.html', campaign=campaign, prospects=prospects_list, ahp_result=ahp_result, step=3)

@app.route('/prospects/<int:campaign_id>/remove/<int:prospect_id>', methods=['POST'])
def remove_prospect(campaign_id, prospect_id):
    from models import Prospect
    prospect = Prospect.query.get_or_404(prospect_id)
    
    # Check if it was the top prospect
    was_top = prospect.topsis_rank == 1
    
    # Soft delete
    prospect.is_active = False
    db.session.commit()
    
    if was_top:
        flash("Vous avez retiré le prospect prioritaire — le classement va se réajuster automatiquement au rang suivant.", "warning")
    else:
        flash("Prospect retiré de la campagne.", "success")
        
    return redirect(url_for('prospects', campaign_id=campaign_id))

from engines.persona_engine import generate_persona, PersonaGenerationError

@app.route('/create_persona/<int:campaign_id>', methods=['POST'])
def create_persona(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    from models import Prospect, Persona
    
    # Retrieve real prospects to feed to the persona generator
    db_prospects = Prospect.query.filter_by(campaign_id=campaign_id).order_by(Prospect.topsis_rank).all()
    prospects_list = []
    for p in db_prospects:
        try:
            prospects_list.append(json.loads(p.prospect_info))
        except Exception:
            pass
            
    try:
        persona_data = generate_persona(campaign, prospects_list)
        
        # Save to DB
        persona = Persona(
            campaign_id=campaign.id,
            virtual_sales_identity=persona_data.get("full_name", ""),
            headline=persona_data.get("headline", ""),
            bio=persona_data.get("bio", ""),
            persona_data=json.dumps(persona_data)
        )
        db.session.add(persona)
        db.session.commit()
        
        flash("Persona généré avec succès.", "success")
        return redirect(url_for('persona_view', campaign_id=campaign.id))
        
    except PersonaGenerationError as e:
        flash(f"Échec de la génération du persona : {str(e)}", "error")
        return redirect(url_for('prospects', campaign_id=campaign.id))

@app.route('/persona/<int:campaign_id>', methods=['GET'])
def persona_view(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    from models import Persona
    
    # Get the latest persona for this campaign
    persona = Persona.query.filter_by(campaign_id=campaign_id).order_by(Persona.id.desc()).first()
    
    persona_dict = {}
    if persona and persona.persona_data:
        try:
            persona_dict = json.loads(persona.persona_data)
        except Exception:
            pass
            
    return render_template('persona.html', campaign=campaign, persona=persona, persona_dict=persona_dict, step=5)

from engines.plan_engine import generate_action_plan, generate_content, PlanGenerationError, ContentGenerationError

@app.route('/prospects/<int:campaign_id>/plan/<int:prospect_id>', methods=['POST'])
def generate_plan(campaign_id, prospect_id):
    from flask import request
    campaign = Campaign.query.get_or_404(campaign_id)
    from models import Persona, Prospect, ActionPlan, GeneratedPost
    
    # Check if a plan already exists
    force_regenerate = request.args.get('force', '0') == '1'
    if not force_regenerate:
        existing_plan = ActionPlan.query.filter_by(campaign_id=campaign_id, prospect_id=prospect_id).first()
        if existing_plan:
            # Cache hit
            return redirect(url_for('plan_view', campaign_id=campaign_id, prospect_id=prospect_id))
    
    # Needs generation
    persona = Persona.query.filter_by(campaign_id=campaign_id).order_by(Persona.id.desc()).first()
    if not persona:
        flash("Veuillez d'abord générer un Persona.", "warning")
        return redirect(url_for('persona_view', campaign_id=campaign_id))
        
    persona_dict = {}
    if persona.persona_data:
        try:
            persona_dict = json.loads(persona.persona_data)
        except Exception:
            pass

    prospect_db = Prospect.query.get_or_404(prospect_id)
    if not prospect_db.is_active:
        flash("Ce prospect a été retiré de la campagne.", "warning")
        return redirect(url_for('prospects', campaign_id=campaign_id))
        
    prospect_dict = {}
    if prospect_db.prospect_info:
        try:
            prospect_dict = json.loads(prospect_db.prospect_info)
        except Exception:
            pass
            
    try:
        plan_data = generate_action_plan(campaign, persona_dict, prospect_dict)
        content_data = generate_content(campaign, persona_dict, prospect_dict, plan_data)
        
        # Save or update Plan
        action_plan = ActionPlan.query.filter_by(campaign_id=campaign_id, prospect_id=prospect_id).first()
        if not action_plan:
            action_plan = ActionPlan(campaign_id=campaign.id, prospect_id=prospect_id)
            db.session.add(action_plan)
        action_plan.ordered_list_6_steps = json.dumps(plan_data.get("steps", []))
        
        # Save or update Content
        gen_post = GeneratedPost.query.filter_by(campaign_id=campaign_id, prospect_id=prospect_id).first()
        if not gen_post:
            gen_post = GeneratedPost(campaign_id=campaign.id, prospect_id=prospect_id)
            db.session.add(gen_post)
        gen_post.post_text = content_data.get("post_text", "")
        gen_post.short_comment = content_data.get("short_comment", "")
        gen_post.direct_message = content_data.get("direct_message", "")
        
        db.session.commit()
        
        flash("Plan d'action et contenus générés avec succès.", "success")
        return redirect(url_for('plan_view', campaign_id=campaign.id, prospect_id=prospect_id))
        
    except (PlanGenerationError, ContentGenerationError) as e:
        flash(f"Échec de la génération : {str(e)}", "error")
        return redirect(url_for('prospects', campaign_id=campaign.id))

@app.route('/plan/<int:campaign_id>/<int:prospect_id>/save_content', methods=['POST'])
def save_plan_content(campaign_id, prospect_id):
    from flask import request
    from models import GeneratedPost
    
    gen_post = GeneratedPost.query.filter_by(campaign_id=campaign_id, prospect_id=prospect_id).first()
    if gen_post:
        gen_post.post_text = request.form.get('post_text', '')
        gen_post.short_comment = request.form.get('short_comment', '')
        gen_post.direct_message = request.form.get('direct_message', '')
        db.session.commit()
        flash("Modifications sauvegardées avec succès.", "success")
    
    return redirect(url_for('plan_view', campaign_id=campaign_id, prospect_id=prospect_id))

@app.route('/plan/<int:campaign_id>/<int:prospect_id>', methods=['GET'])
def plan_view(campaign_id, prospect_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    from models import ActionPlan, GeneratedPost, Prospect
    
    prospect_db = Prospect.query.get_or_404(prospect_id)
    prospect_dict = {}
    if prospect_db.prospect_info:
        try:
            prospect_dict = json.loads(prospect_db.prospect_info)
        except Exception:
            pass

    contact_name = prospect_dict.get("contact_name") or "Contact Inconnu"
    company_name = prospect_dict.get("name") or "Entreprise Inconnue"
    display_name = f"{contact_name} chez {company_name}"

    action_plan_db = ActionPlan.query.filter_by(campaign_id=campaign_id, prospect_id=prospect_id).first()
    gen_post_db = GeneratedPost.query.filter_by(campaign_id=campaign_id, prospect_id=prospect_id).first()
    
    steps = []
    if action_plan_db and action_plan_db.ordered_list_6_steps:
        try:
            steps = json.loads(action_plan_db.ordered_list_6_steps)
        except Exception:
            pass
            
    return render_template('plan.html', campaign=campaign, prospect_id=prospect_id, steps=steps, content=gen_post_db, display_name=display_name, step=6)

from engines.action_executor import execute_planned_action
from engines.hub_client import HubClient

@app.route('/prospects/<int:campaign_id>/action/<int:prospect_id>/<int:step_number>', methods=['POST'])
def launch_action(campaign_id, prospect_id, step_number):
    campaign = Campaign.query.get_or_404(campaign_id)
    from models import Prospect, ActionPlan, GeneratedPost, ActionExecution
    
    prospect_db = Prospect.query.get_or_404(prospect_id)
    action_plan_db = ActionPlan.query.filter_by(campaign_id=campaign_id, prospect_id=prospect_id).first()
    gen_post_db = GeneratedPost.query.filter_by(campaign_id=campaign_id, prospect_id=prospect_id).first()
    
    if not action_plan_db or not action_plan_db.ordered_list_6_steps:
        flash("Aucun plan d'action trouvé pour ce prospect.", "error")
        return redirect(url_for('plan_view', campaign_id=campaign_id, prospect_id=prospect_id))
        
    prospect_dict = json.loads(prospect_db.prospect_info) if prospect_db.prospect_info else {}
    steps = json.loads(action_plan_db.ordered_list_6_steps)
    
    # Trouver l'étape
    if step_number < 1 or step_number > len(steps):
        flash("Étape invalide.", "error")
        return redirect(url_for('action_view', campaign_id=campaign_id, prospect_id=prospect_id))
        
    plan_step = steps[step_number - 1]
    
    content_dict = {
        "post_text": gen_post_db.post_text if gen_post_db else "",
        "short_comment": gen_post_db.short_comment if gen_post_db else "",
        "direct_message": gen_post_db.direct_message if gen_post_db else ""
    }
    
    # Vérifier ou créer l'ActionExecution
    execution = ActionExecution.query.filter_by(campaign_id=campaign_id, prospect_id=prospect_id, step_number=step_number).first()
    if not execution:
        execution = ActionExecution(
            campaign_id=campaign_id,
            prospect_id=prospect_id,
            step_number=step_number,
            action_type=plan_step.get("action_type", "unknown")
        )
        db.session.add(execution)
    
    execution.status = "running"
    db.session.commit()
    
    # Exécuter l'action via le Hub (bloquant)
    hub_client = HubClient()
    result = execute_planned_action(prospect_dict, plan_step, content_dict, hub_client)
    
    execution.status = result.get("status")
    execution.result_detail = result.get("result_detail")
    execution.human_question = result.get("human_question")
    db.session.commit()
    
    if execution.status == "success":
        flash(f"L'étape {step_number} a été exécutée avec succès.", "success")
    elif execution.status == "needs_human_help":
        flash(f"Le Hub a besoin d'aide pour l'étape {step_number}.", "warning")
    else:
        flash(f"Échec de l'étape {step_number} : {execution.result_detail}", "error")
        
    return redirect(url_for('action_view', campaign_id=campaign_id, prospect_id=prospect_id))

@app.route('/action/<int:campaign_id>/<int:prospect_id>', methods=['GET'])
def action_view(campaign_id, prospect_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    from models import ActionPlan, ActionExecution, Prospect
    
    prospect_db = Prospect.query.get_or_404(prospect_id)
    prospect_dict = json.loads(prospect_db.prospect_info) if prospect_db.prospect_info else {}
    contact_name = prospect_dict.get("contact_name") or prospect_dict.get("name") or "Contact Inconnu"
    display_name = f"{contact_name} chez {prospect_dict.get('name', '')}"
    
    action_plan_db = ActionPlan.query.filter_by(campaign_id=campaign_id, prospect_id=prospect_id).first()
    steps = json.loads(action_plan_db.ordered_list_6_steps) if action_plan_db and action_plan_db.ordered_list_6_steps else []
    
    executions = ActionExecution.query.filter_by(campaign_id=campaign_id, prospect_id=prospect_id).all()
    executions_dict = {ex.step_number: ex for ex in executions}
    
    # Enrichir les steps avec l'état d'exécution
    for i, step in enumerate(steps):
        step_idx = i + 1
        step['step_number'] = step_idx
        if step_idx in executions_dict:
            ex = executions_dict[step_idx]
            step['status'] = ex.status
            step['result_detail'] = ex.result_detail
            step['human_question'] = ex.human_question
        else:
            step['status'] = 'pending'
            step['result_detail'] = ''
            step['human_question'] = ''
            
    return render_template('action.html', campaign=campaign, prospect_id=prospect_id, steps=steps, display_name=display_name, step=7)

@app.route('/prospects/<int:campaign_id>/action/<int:prospect_id>/<int:step_number>/help', methods=['POST'])
def submit_action_help(campaign_id, prospect_id, step_number):
    from flask import request
    human_response = request.form.get("human_response", "")
    
    from models import ActionExecution
    execution = ActionExecution.query.filter_by(campaign_id=campaign_id, prospect_id=prospect_id, step_number=step_number).first_or_404()
    
    if execution.status != "needs_human_help":
        flash("Cette action n'attend plus de réponse humaine.", "info")
        return redirect(url_for('action_view', campaign_id=campaign_id, prospect_id=prospect_id))
        
    hub_client = HubClient()
    hub_client.submit_help(human_response)
    
    execution.status = "running"
    execution.human_question = None
    db.session.commit()
    
    status_info = hub_client.wait_for_completion(timeout=300.0)
    status_state = status_info.get("status")
    
    if status_state == "success":
        execution.status = "success"
        execution.result_detail = "Action exécutée avec succès par le Hub (après intervention)."
    elif status_state == "failed":
        execution.status = "failed"
        execution.result_detail = f"Échec après intervention : {status_info.get('error')}"
    elif status_state == "human_intervention_needed":
        execution.status = "needs_human_help"
        execution.human_question = status_info.get("human_question")
        execution.result_detail = "Le Hub est de nouveau bloqué."
    
    db.session.commit()
    return redirect(url_for('action_view', campaign_id=campaign_id, prospect_id=prospect_id))

if __name__ == '__main__':
    # Run on port 5000 to not conflict with the Hub on 8000
    app.run(port=5000, debug=True)
