from odoo import models, fields,api

class OHSIncidentInvestigation(models.Model):
    _name = 'ohs.incident.investigation'
    _description = 'OHS Incident Investigation'

    report_no = fields.Char(string='Report No', help='As mentioned in OHS Incident Report')
    nature_type_injury = fields.Char(string='Nature and Type of Injury')
    date_incident = fields.Date(string='Date of Incident')
    date_investigation = fields.Date(string='Date of Investigation', default=fields.Date.today)
    team_ids = fields.One2many('ohs.incident.team', 'investigation_id', string='Team Involved in Investigation')
    detail_incident = fields.Text(string='Detail of Incident')
    unsafe_condition = fields.Boolean(string='Is there any Unsafe Condition')
    unsafe_action = fields.Boolean(string='Is there any Unsafe Action')
    past_history = fields.Boolean(string='Is there any Past History of Accidents related to that')
    malfunction_equipment = fields.Boolean(string='Is there any Malfunction of any Safety Equipments')
    property_loss = fields.Boolean(string='Is Injury Associated with Loss of Property')
    injury_extent = fields.Selection([
        ('no', 'No'),
        ('minor', 'Minor'),
        ('major', 'Major')
    ], string='At what extent injury affected Person')
    conclusion = fields.Text(string='Conclusion')
    corrective_action = fields.Text(string='Corrective Action')
    root_cause = fields.Text(string='Root Cause')
    preventive_action = fields.Text(string='Preventive Action (if Possible)')
    measure_effectiveness = fields.Text(string='Method of Measuring Effectiveness of above actions')
    learnings = fields.Text(string='Learnings')
    horizontal_deployment = fields.Text(string='Horizontal Deployment')
    she_incharge_signature = fields.Text(string='SHE In-Charge Signature')
    she_incharge_date = fields.Date(string='SHE In-Charge Date')
    plant_head_signature = fields.Text(string='Plant Head Signature')
    plant_head_date = fields.Date(string='Plant Head Date')
    company = fields.Many2one('res.company', string='Company')

class OHSIncidentTeam(models.Model):
    _name = 'ohs.incident.team'
    _description = 'OHS Incident Investigation Team'

    investigation_id = fields.Many2one('ohs.incident.investigation', string='Investigation', ondelete='cascade')
    name = fields.Many2one('hr.employee', string='Name')
    designation = fields.Many2one('hr.department',related='name.department_id',store=True,string='Designation')
    signature = fields.Binary(string='Signature')