from odoo import models, fields, api
from odoo.exceptions import ValidationError

class DGSetProcedure(models.Model):
    _name = 'dg.set.procedure'
    _description = 'DG Set Procedure'

    issue_no = fields.Char(string='Issue No/Ref No')
    issue_date = fields.Date(string='Issue Date')
    rev_no = fields.Char(string='Rev No')
    rev_date = fields.Date(string='Rev Date')
    purpose = fields.Char(string='Purpose')
    scope = fields.Char(string='Scope')
    responsibilities = fields.Many2many('res.users', string='Responsibilities')

    instruction_ids = fields.One2many('dg.set.process', 'procedure_id', string='Instructions',
                                      domain=[('category', '=', 'instruction')])
    change_over_ids = fields.One2many('dg.set.process', 'procedure_id', string='Change Over',
                                      domain=[('category', '=', 'change_over')])
    impact_deviation_ids = fields.One2many('dg.set.process', 'procedure_id', string='Impact in Case of Deviation',
                                           domain=[('category', '=', 'impact_deviation')])
    corrective_action_ids = fields.One2many('dg.set.process', 'procedure_id', string='Corrective Actions',
                                           domain=[('category', '=', 'corrective_action')])
    cross_reference_ids = fields.One2many('dg.set.process', 'procedure_id', string='Cross References',
                                         domain=[('category', '=', 'cross_reference')])
    key_characteristic_ids = fields.One2many('dg.set.process', 'procedure_id', string='Key Characteristics',
                                            domain=[('category', '=', 'key_characteristic')])

class DGSetProcess(models.Model):
    _name = 'dg.set.process'
    _description = 'DG Set Instruction Process'

    procedure_id = fields.Many2one('dg.set.procedure', string='Procedure', ondelete='cascade')
    category = fields.Selection([
        ('instruction', 'Instructions'),
        ('change_over', 'Change Over from DG to MSEB Supply'),
        ('impact_deviation', 'Impact in Case of Deviation'),
        ('corrective_action', 'Corrective Action in Case of Deviation'),
        ('cross_reference', 'Cross Reference'),
        ('key_characteristic', 'Key Characteristics to be Monitored'),
    ], required=True, string='Category', default=lambda self: self._context.get('default_category'))
    sequence = fields.Integer(string='Sequence', compute='_compute_sequence', store=True)
    instruction = fields.Text(string='Instruction')
    photos = fields.Many2many('ir.attachment', string='Photos')

    @api.depends('procedure_id', 'procedure_id.instruction_ids', 'procedure_id.change_over_ids',
                 'procedure_id.impact_deviation_ids', 'procedure_id.corrective_action_ids',
                 'procedure_id.cross_reference_ids', 'procedure_id.key_characteristic_ids')
    def _compute_sequence(self):
        """Compute sequence number based on category within the same procedure"""
        for procedure in self.mapped('procedure_id'):
            for category in self.env['dg.set.process']._fields['category'].selection:
                category_key = category[0]
                field_map = {
                    'instruction': 'instruction_ids',
                    'change_over': 'change_over_ids',
                    'impact_deviation': 'impact_deviation_ids',
                    'corrective_action': 'corrective_action_ids',
                    'cross_reference': 'cross_reference_ids',
                    'key_characteristic': 'key_characteristic_ids',
                }
                field_name = field_map[category_key]
                # Get processes, handling both saved and unsaved records
                processes = procedure[field_name]
                # Split into saved and unsaved records
                saved_processes = processes.filtered(lambda r: r.id and not isinstance(r.id, models.NewId))
                unsaved_processes = processes - saved_processes
                # Sort saved processes by ID, keep unsaved processes in their order
                sorted_processes = saved_processes.sorted(key=lambda r: r.id) + unsaved_processes
                # Assign sequence numbers
                for i, process in enumerate(sorted_processes, 1):
                    process.sequence = i

    @api.constrains('category', 'procedure_id')
    def _check_category_consistency(self):
        """Ensure category matches the One2many field it belongs to"""
        for record in self:
            if not record.procedure_id:
                continue
            expected_category = None
            field_map = {
                record.procedure_id.instruction_ids: 'instruction',
                record.procedure_id.change_over_ids: 'change_over',
                record.procedure_id.impact_deviation_ids: 'impact_deviation',
                record.procedure_id.corrective_action_ids: 'corrective_action',
                record.procedure_id.cross_reference_ids: 'cross_reference',
                record.procedure_id.key_characteristic_ids: 'key_characteristic',
            }
            for one2many_field, category in field_map.items():
                if record in one2many_field:
                    expected_category = category
                    break
            if expected_category and record.category != expected_category:
                raise ValidationError(f"Category must be '{expected_category}' for this section.")