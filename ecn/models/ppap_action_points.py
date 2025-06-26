from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError




class PPAPActionPoints(models.Model):
    _name='ppap.action.points'
    _description='PPAP Action Points'

    _inherit='iatf.sign.off.members'

    project = fields.Many2one('xf.doc.approval.document.package', string='Project')
    part_id = fields.Many2one('product.template', related='project.part_id', string='Part No.', required=True)
    part_name = fields.Char(string='Part Name', related='part_id.name')
    part_number = fields.Char(string='Part Number', related='part_id.default_code')

    drg_no = fields.Char('Drg. No.', related='part_id.drg_no')
    partner_id = fields.Many2one('res.partner', string='Customer Name', related='project.partner_id', required=True)

    related_parts = fields.Many2many('product.template', string='Related Parts')
    ppap_ids = fields.One2many('ppap.action.points.line','ppap_id',string='PPAP Action Points Line')
    additional_ids = fields.One2many(
        'ppap.action.points.add',
        'ppap_id',
        string='Additional Formats'
    )
    @api.onchange('project')
    def _fetch_format_data(self):
        for record in self:
            if record.project:
                # Find formats related to this project
                format_ids = self.env['document.formate'].search([
                    ('used_in_project_type_ids', 'in', [record.project.used_in_project_type_id.id]),
                    ('sr_no', '=', 1)
                ])

                if format_ids:
                    # Create lines for each format
                    for format_id in format_ids:
                        self.env['ppap.action.points.line'].create({
                            'ppap_id': record.id,
                            'format': format_id.id,
                            'change_required': False,  # Default value
                        })
                else:
                    # Notify if no formats found
                    record.message_post(body=_("No document formats found for this project type."))
            # else:
            #     raise ValidationError(_("Please select a project before proceeding to implementation planning."))


class PPAPActionPointsLine(models.Model):
    _name='ppap.action.points.line'
    _description = 'PPAP Action Points'
    _inherit = "translation.mixin"

    ppap_id=fields.Many2one('ppap.action.points',string='lines',ondelete='cascade')
    sl_no = fields.Integer('S.No', compute='_compute_sequence_number')
    # Update format field to filter based on project_id's project type
    format = fields.Many2one(
        'document.formate',
        'Format')
    table = fields.Char('Table', related='format.table')

    change_required = fields.Boolean("Change Required (Y/N)")
    responsibility_id = fields.Many2one("res.users", 'Responsibility')
    action=fields.Text('Action')
    target_date = fields.Date('Target Date')
    ecn_attachment = fields.Binary('Attachments')

    @api.depends('ppap_id')
    def _compute_sequence_number(self):
        for line in self:
            if not line.ppap_id or not line.ppap_id.ppap_ids:
                line.sl_no = 1
                continue

            try:
                # Try to sort by ID if they're real IDs
                related_lines = line.ppap_id.ppap_ids

                # Instead of sorting by ID, track position manually
                position = 1
                for rel_line in related_lines:
                    if rel_line.id == line.id:
                        line.sl_no = position
                        break
                    position += 1
                else:
                    line.sl_no = 1
            except Exception:
                # Fallback for new records
                line.sl_no = 1

    def action_open_format(self):
        """Action to open the format in its actual model form view."""
        self.ensure_one()
        if not self.change_required:
            raise UserError(_("Change Required must be checked to open the format."))

        # Check if current user is the responsible person
        current_user = self.env.user
        if self.responsibility_id and self.responsibility_id != current_user:
            raise UserError(_("You don't have access to this record. Only the responsible person can open it."))

        format_to_open = self.format
        if not format_to_open:
            raise UserError(_("No format available to open."))

        if not hasattr(format_to_open, 'table') or not format_to_open.table:
            raise UserError(_("Format doesn't have table information."))

        try:
            target_model = self.env[format_to_open.table].sudo()
            domain = [
                ('part_id', '=', self.ppap_id.part_id.id),
                ('partner_id', '=', self.ppap_id.partner_id.id)
            ]
            format_id = target_model.search(domain, limit=1)

            if not format_id:
                raise UserError(
                    _("Related record not found in %s. You may need to create it first.") % format_to_open.table)

            return {
                'type': 'ir.actions.act_window',
                'name': format_to_open.name,
                'view_mode': 'form',
                'res_model': format_to_open.table,
                'res_id': format_id.id,
            }
        except Exception as e:
            raise UserError(_("Error opening format: %s") % str(e))


class PPAPActionPointsAdditional(models.Model):
    _name='ppap.action.points.add'
    _description = 'PPAP Action Points Additional Formats'

    ppap_id = fields.Many2one('ppap.action.points', string='Additional Lines', ondelete='cascade')

    formate_name = fields.Many2one('ecn.format', 'Format')
    description = fields.Text('Description',translate=True)
    change_required = fields.Boolean("Change Required (Y/N)")
    responsibility_id = fields.Many2one("res.users", 'Responsibility')
    target_date = fields.Date('Target Date')
    ecn_attachment = fields.Binary('Attachments')
