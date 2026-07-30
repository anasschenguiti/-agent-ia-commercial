from database import db
from sqlalchemy import Column, Integer, String, Float, Text, DateTime
import datetime

class Campaign(db.Model):
    __tablename__ = 'campaigns'
    id = Column(Integer, primary_key=True)
    company_name = Column(String(255))
    company_sector = Column(String(255))
    company_size = Column(String(255))
    company_description = Column(Text)
    linkedin_url = Column(String(500))
    value_proposition = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Prospect(db.Model):
    __tablename__ = 'prospects'
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, db.ForeignKey('campaigns.id'))
    prospect_info = Column(Text) # JSON structure containing name, sector, etc.
    topsis_score = Column(Float)
    topsis_rank = Column(Integer)
    priority_label = Column(String(50)) # Top, High, Medium, Low
    difficulty_score = Column(Float) # Legacy field
    difficulty_label = Column(String(50)) # Legacy field
    is_active = Column(db.Boolean, default=True)

class Persona(db.Model):
    __tablename__ = 'personas'
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, db.ForeignKey('campaigns.id'))
    virtual_sales_identity = Column(String(255))
    headline = Column(String(255))
    bio = Column(Text)
    persona_data = Column(Text) # Stores full JSON (role, age, skills, projects, etc.)

class ActionPlan(db.Model):
    __tablename__ = 'action_plans'
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, db.ForeignKey('campaigns.id'))
    prospect_id = Column(Integer, db.ForeignKey('prospects.id'))
    ordered_list_6_steps = Column(Text) # JSON structure as Text for now

class GeneratedPost(db.Model):
    __tablename__ = 'generated_posts'
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, db.ForeignKey('campaigns.id'))
    prospect_id = Column(Integer, db.ForeignKey('prospects.id'))
    post_text = Column(Text)
    short_comment = Column(Text)
    direct_message = Column(Text)

class ActionExecution(db.Model):
    __tablename__ = 'action_executions'
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, db.ForeignKey('campaigns.id'))
    prospect_id = Column(Integer, db.ForeignKey('prospects.id'))
    step_number = Column(Integer) # Index in the action plan (1 to 6)
    action_type = Column(String(50))
    status = Column(String(50), default="pending") # pending, running, success, failed, needs_human_help
    result_detail = Column(Text)
    human_question = Column(Text)
    executed_at = Column(DateTime, default=datetime.datetime.utcnow)
