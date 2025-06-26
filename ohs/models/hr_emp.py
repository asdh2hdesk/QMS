from odoo import models, fields


class EnvironmentalProgramme(models.Model):
    _name = 'environmental.programme'
    _description = 'Environmental Management Programme'

    doc_no = fields.Char("Doc. No.")
    rev_no = fields.Char("Rev. No.")
    date = fields.Date("Date")
    name = fields.Char(string="Subject", required=True)
    area = fields.Char(string="Area")
    present_status = fields.Char(string="Present Status")
    objective = fields.Char(string="Objective & Targets")
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    duration = fields.Char(string="Duration")
    reviewed_frequency = fields.Char(string="Reviewed Frequency")
    prepared_by = fields.Many2one('res.users', string='Prepared By')
    approved_by = fields.Many2one('res.users', string='Approved By')

    team_member_ids = fields.One2many(
        'environmental.programme.team', 'programme_id', string="Team Members"
    )
    programme_element_ids = fields.One2many(
        'environmental.programme.element', 'programme_id', string="Programme Elements"
    )


class EnvironmentalProgrammeTeam(models.Model):
    _name = 'environmental.programme.team'
    _description = 'Programme Team Member'

    programme_id = fields.Many2one('environmental.programme', string="Programme")
    sr_no = fields.Integer(string="Sr No")
    name = fields.Char(string="Team Member")
    signature = fields.Binary(string="Signature")  # Optional if digital signature is required


class EnvironmentalProgrammeElement(models.Model):
    _name = 'environmental.programme.element'
    _description = 'Programme Element'

    programme_id = fields.Many2one('environmental.programme', string="Programme")
    sr_no = fields.Integer(string="Sr No")
    element = fields.Text(string="Programme Elements")
    responsibility = fields.Many2many('res.users', string="Responsibility")
    target_date = fields.Date(string="Target Date")
    status = fields.Selection([
        ('done', 'Done'),
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('not_started', 'Not Started'),
    ], string="Status")
