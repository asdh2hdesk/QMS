from odoo import models, fields


class NearMissIncident(models.Model):
    _name = 'near.miss.incident'
    _description = 'Near Miss Incident Recording'

    serial_no = fields.Char("Serial No.")
    employee_id = fields.Many2one('hr.employee', string="Employee Name")
    employee_code = fields.Char( string="Employee Code")
    department = fields.Char(related='employee_id.department_id.name', string="Department")
    incident_date = fields.Date("Date & Time of Incident")
    incident_location = fields.Char("Incident Location")
    incident_description = fields.Text("Incident Description")
    incident_root_cause = fields.Text("Root Cause")
    discussion_with_employee = fields.Text("Discussion with Employee")
    reported_by = fields.Many2many('res.users', string="Reported By")
    corrective_action = fields.Text("Corrective Action & Recommendation")
    remark = fields.Text("Remark (For Management Use)")
    prepared_by = fields.Many2one('res.users', string="Prepared By")
    approved_by = fields.Many2one('res.users', string="Approved By")
    date = fields.Date("Date", default=fields.Date.today)
