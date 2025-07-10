from odoo import models, fields, api,_
class ESGDataEntry(models.Model):
    _name = 'esg.data.entry'
    _description = 'ESG Data Entry'
    _inherit = ['mail.thread']

    metric_id = fields.Many2one('esg.metric', required=True)
    entry_date = fields.Date(default=fields.Date.today)
    value = fields.Float(required=True)
    supporting_document = fields.Binary()
    document_name = fields.Char()
    submitted_by = fields.Many2one('res.users', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
