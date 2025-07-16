from odoo import models, fields,api

class EmergencyResponseMaster(models.Model):
    _name = 'emergency.response.master'
    _description = 'Emergency Response Master'

    # company = fields.Many2one('res.company', string='Company')
    team_member_ids = fields.One2many('emergency.response.team', 'master_id', string='Team Members')

class EmergencyResponseTeam(models.Model):
    _name = 'emergency.response.team'
    _description = 'Emergency Response Team'

    master_id = fields.Many2one('emergency.response.master', string='Master List', ondelete='cascade')
    sl_no = fields.Integer(string='Sl No', required=True)
    name = fields.Many2one('hr.employee', string='Name')
    department = fields.Many2one('hr.department', related='name.department_id', store=True, string='Department')

    remarks = fields.Char(string='Remarks')
    team_type = fields.Selection([
        ('auxiliary', 'Auxiliary/Evacuation'),
        ('first_aid', 'First Aid'),
        ('fire_fighting', 'Fire Fighting')
    ], string='Team Type', required=True, default='auxiliary')


    @api.depends('master_id', 'master_id.team_member_ids')
    def _compute_sl_no(self):
        """Compute sl_no based on position in master's team members"""
        for master in self.mapped('master_id'):
            team_members = self.env['emergency.response.team'].search([
                ('master_id', '=', master.id)
            ], order='id')
            for i, member in enumerate(team_members, 1):
                member.sl_no = i