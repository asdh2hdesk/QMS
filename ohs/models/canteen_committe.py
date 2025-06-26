from odoo import models, fields, api, _

class CanteenCommittee(models.Model):
    _name = 'canteen.committee'
    _description = 'Canteen Committee'

    employee_id = fields.Many2one('hr.employee', string="Name")
    department = fields.Char(related='employee_id.department_id.name', string="Department")
    name = fields.Char(string='Name', required=True)
    department1 = fields.Many2one('canteen.department', string='Department', required=True)

class CanteenDepartment(models.Model):
    _name = 'canteen.department'
    _description = 'Canteen Department'

    name = fields.Char(string='Department Name', required=True)
    
