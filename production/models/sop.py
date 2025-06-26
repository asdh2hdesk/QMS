from odoo import fields, models, api, _

class StandardOperatingProcedure(models.Model):
    _name = "standard.operating.procedure"
    _description = "Standard Operating Procedure"
    _inherit = 'iatf.sign.off.members'

    sop_no = fields.Char('SOP No.', required=True, copy=False,
                        readonly=True, default=lambda self: _('New'))
    sop_description = fields.Char('SOP Description', required=True)
    prn_number = fields.Char('PRN Number')
    issued_on = fields.Date('Issued On')
    rev_date = fields.Date('Rev. Date')
    rev_no = fields.Char('Rev. No.')
    rev_details = fields.Char('Rev. Details')
    revised_by = fields.Many2one('res.users', 'Revised By')
    model_name = fields.Char('Model Name')
    stage = fields.Char('Stage')
    shop = fields.Char('Shop')
    doc_no = fields.Char('Doc No')
    page_no = fields.Char('Page No.')


    extra_care = fields.Many2many('extra.care.alerts.line', 'extra_care_rel', 'extra_id', 'alerts_id')
    settings_ids = fields.Many2many('sop.settings', 'settings_rel', 'settings_id', 'sop_id')
    safety_ids = fields.Many2many('sop.safety', 'safety_rel', 'safety_id', 'sop_id')
    process_and_tooling_ids = fields.One2many(
        comodel_name='process.and.tooling',
        inverse_name='sop_id',
        string='Process and Tooling'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sop_no', _('New')) == _('New'):  # Changed from 'name' to 'sop_no'
                vals['sop_no'] = self.env['ir.sequence'].next_by_code('standard.operating.procedure') or _('New')
        return super().create(vals_list)

    def name_get(self):
        """Display SOP No. and Description"""
        result = []
        for record in self:
            name = f"[{record.sop_no}] {record.sop_description}" if record.sop_description else record.sop_no
            result.append((record.id, name))
        return result


class ProcessAndTooling(models.Model):
    _name = "process.and.tooling"
    _description = "Process and Tooling"
    _inherit = 'iatf.sign.off.members'

    sop_id = fields.Many2one('standard.operating.procedure', string='SOP')
    sr_no = fields.Char('Sr. No.')
    process_details = fields.Char('Process Details')
    control_point = fields.Char('Control Point')
    spec_torque = fields.Char('Spec./Torque')
    tools = fields.Many2many('maintenance.equipment', string="Tools")
    procedure_image = fields.Image("Procedure Image")
    bom_ids = fields.One2many(
        comodel_name='bill.of.materials',
        inverse_name='material_id',
        string='Bill of Materials'
    )

    def name_get(self):
        """Display Sr. No. and Process Details"""
        result = []
        for record in self:
            name = f"[{record.sr_no}] {record.process_details}" if record.process_details else (record.sr_no or 'Process')
            result.append((record.id, name))
        return result


class BillOfMaterials(models.Model):
    _name = "bill.of.materials"
    _description = "Bill of Materials"
    _inherit = 'iatf.sign.off.members'

    material_id = fields.Many2one('process.and.tooling', string='Material')
    item_code = fields.Char('Item Code')
    description = fields.Char('Description')
    quantity = fields.Char('Quantity')

    def name_get(self):
        """Display Item Code and Description"""
        result = []
        for record in self:
            name = f"[{record.item_code}] {record.description}" if record.item_code and record.description else (record.item_code or record.description or 'BOM Item')
            result.append((record.id, name))
        return result


class SOPSettings(models.Model):
    _name = "sop.settings"
    _description = "SOP Settings"

    name = fields.Char('Settings', required=True)


class SOPSafety(models.Model):
    _name = "sop.safety"
    _description = "SOP Safety"

    name = fields.Char('Safety Information', required=True)