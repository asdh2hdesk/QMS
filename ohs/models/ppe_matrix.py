from odoo import models, fields

class PpeMatrix(models.Model):
    _name = 'ppe.matrix'
    _description = 'PPE Matrix'

    # name = fields.Char(string="Title", default="PPE Matrix")
    doc_no = fields.Char("Doc. No.")
    rev_no = fields.Char("Rev. No.")
    date = fields.Date("Date")
    line_ids = fields.One2many('ppe.matrix.line', 'matrix_id', string="PPE Lines")

class PpeMatrixLine(models.Model):
    _name = 'ppe.matrix.line'
    _description = 'PPE Matrix Line'

    matrix_id = fields.Many2one('ppe.matrix', string="PPE Matrix")
    serial_no = fields.Integer(string="S. No")
    activity = fields.Char(string="Activity")
    activity_hindi = fields.Char(string="Activity (Hindi)")
    ppe_description = fields.Text(string="PPE Description")
    ppe_image_1 = fields.Binary(string="Image 1")
    ppe_image_2 = fields.Binary(string="Image 2")
    ppe_image_3 = fields.Binary(string="Image 3")
