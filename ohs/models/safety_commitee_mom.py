from odoo import models, fields

class SafetyCommitteeMom(models.Model):
    _name = 'safety.committee.mom'
    _description = 'Safety Committee MOM'

    name = fields.Char(string="Meeting Title", default="Safety Committee MOM ")
    date = fields.Date(string="Meeting Title")
    attendee_ids = fields.Many2many('res.partner', string="Attendees")
    line_ids = fields.One2many('safety.committee.mom.line', 'mom_id', string="Action Points")

class SafetyCommitteeMomLine(models.Model):
    _name = 'safety.committee.mom.line'
    _description = 'MOM Action Point'

    mom_id = fields.Many2one('safety.committee.mom', string="MOM Reference")
    sr_no = fields.Integer(string="S. No")
    point = fields.Text(string="Point")
    area_related = fields.Char(string="Area Related")
    responsibility = fields.Many2one('res.users', string="Responsibility")
    target_date = fields.Date(string="Target Date")  # Can be Date if needed
    action_taken = fields.Char(string="Action Taken")
