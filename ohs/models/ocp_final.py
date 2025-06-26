from odoo import models, fields, api,_


class OcpFinal(models.Model):
    _name = 'ocp.final'
    _description = 'HR OCP Final'

    doc_no = fields.Char("Doc. No.")
    rev_no = fields.Char("Rev. No.")
    date = fields.Date("Date")
    purpose = fields.Text("Purpose")
    responsibility = fields.Many2one('res.users', string="Responsibility")
    prepared_by = fields.Many2one('res.users', string='Prepared By')
    approved_by = fields.Many2one('res.users', string='Approved By')

    ocp_line_ids = fields.One2many('ocp.final.line', 'ocp_final_id', string="OCP Lines")

class OcpFinalLine(models.Model):
    _name = 'ocp.final.line'
    _description = 'HR OCP Final Line'

    ocp_final_id = fields.Many2one('ocp.final', string='OCP Final')
    sr_no = fields.Integer("Sr. No.")
    description = fields.Text("Description")
    resp = fields.Many2one('res.users', string='Resp.')
    ref_doc_no = fields.Char("Ref. Doc. No.")