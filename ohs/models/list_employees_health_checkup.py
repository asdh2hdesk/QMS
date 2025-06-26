from odoo import models, fields

class HealthCheckupRegister(models.Model):
    _name = 'health.checkup.register'
    _description = 'Health Checkup Register'

    name = fields.Char(string="Title", default="List of Employees for Health Checkup")
    checkup_line_ids = fields.One2many('health.checkup.line', 'register_id', string="Checkup Line Items")

class HealthCheckupLine(models.Model):
    _name = 'health.checkup.line'
    _description = 'Health Checkup Line'

    register_id = fields.Many2one('health.checkup.register', string="Health Checkup Register")
    serial_no = fields.Integer(string="SL. N")
    emp_no = fields.Char(string="EMP. N")
    employee_id = fields.Many2one('hr.employee', string="Name")
    department = fields.Char(related='employee_id.department_id.name', string="Department")
    remarks = fields.Char(string="Remarks")
    category = fields.Selection([
        ('non_hazardous', 'Non Hazardous'),
        ('hazardous', 'Hazardous'),
        ('executive_checkup', 'Executive Checkup')
    ], string="Category")
    test_to_be_done = fields.Text(string="Test to be done")

