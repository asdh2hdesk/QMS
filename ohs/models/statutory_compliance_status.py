from odoo import models, fields

class StatutoryApproval(models.Model):
    _name = 'statutory.approval'
    _description = 'Statutory Approval and NOC Status'

    # name = fields.Char(string="Name")
    statutory_approval_line_ids = fields.One2many('statutory.approval.line', 'statutory_approval_id', string="Statutory Approval Line")


class StatutoryApprovalLine(models.Model):
    _name = 'statutory.approval.line'
    _description = 'Statutory Approval Line'

    statutory_approval_id = fields.Many2one('statutory.approval', string="Statutory Approval")
    sr_no = fields.Integer(string="Sr. No")
    document_name = fields.Char(string="Document")
    when_to_apply = fields.Char(string="When to be Applied")
    responsibility = fields.Many2one('res.users', string="Responsibility")
    status = fields.Selection([
        ('done', 'Done'),
        ('pending', 'Pending'),
        ('under_process', 'Under Process'),
        ('applied', 'Applied'),
        ('in_process', 'In Process'),
        ('future', 'Future Activity'),
        ('other', 'Other')
    ], string="Status")