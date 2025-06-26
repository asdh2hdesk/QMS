from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TopAPPFMEA(models.Model):
    _name = 'top.ap.pfmea'
    _description = 'Top AP for PFMEA'
    _rec_name = 'problem_id'
    _inherit = "translation.mixin"

    problem_id = fields.Char(string='Problem ID', readonly=True,translate=True)
    process_step_name = fields.Char(string='Process Step', readonly=True,translate=True)
    work_type = fields.Selection([
        ('man', 'Man'),
        ('machine', 'Machine'),
        ('material', 'Material'),
        ('environment', 'Environment'),
        ('method', 'Method')
    ], string="4M Type", readonly=True)
    failure_mode = fields.Char(string='Failure Mode', readonly=True,translate=True)
    failure_causes = fields.Char(string='Failure Cause', readonly=True,translate=True)
    fmea_ap = fields.Char(string='Risk Analysis Action Priority', readonly=True,translate=True)
    pfmea_ap = fields.Char(string='Optimization Action Priority', readonly=True,translate=True)




    # New computed field for sorting
    fmea_ap_sort = fields.Integer(
        string='FMEA AP Sort Priority',
        compute='_compute_fmea_ap_sort',
        store=True  # Optional: store it if you want to improve performance
    )

    @api.depends('fmea_ap')
    def _compute_fmea_ap_sort(self):
        for record in self:
            if record.fmea_ap == 'H':
                record.fmea_ap_sort = 3
            elif record.fmea_ap == 'M':
                record.fmea_ap_sort = 2
            elif record.fmea_ap == 'L':
                record.fmea_ap_sort = 1
            else:
                record.fmea_ap_sort = 0  # Default for unexpected values

    # Set default sorting for the model
    _order = 'fmea_ap_sort desc'

    # For filtering in views
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    pfmea_id = fields.Many2one('process.report', string='PFMEA Report', readonly=True)
    # Add to the PFMEADashboard class in dashboard_report.py after the pfmea_id field
    part_id = fields.Many2one("product.template", string="Part", readonly=True)

    process_operation_id = fields.Many2one('process.operations', string='Process Operation', readonly=True)
    process_line_id = fields.Many2one('process.sub.operations.lines', string='Process Line', readonly=True)

    @api.model
    def refresh_top_ap_data(self):
        """Refresh Top AP data by syncing with process operations and lines"""
        # Clear existing records to prevent duplicates
        self.env['top.ap.pfmea'].search([]).unlink()

        # Get all process sub operation lines directly
        line_records = self.env['process.sub.operations.lines'].search([])

        for line in line_records:
            # Determine the parent operation
            parent_op = False
            work_type = False

            if line.man_pro_id:
                parent_op = line.man_pro_id
                work_type = 'man'
            elif line.machine_pro_id:
                parent_op = line.machine_pro_id
                work_type = 'machine'
            elif line.material_pro_id:
                parent_op = line.material_pro_id
                work_type = 'material'
            elif line.environment_pro_id:
                parent_op = line.environment_pro_id
                work_type = 'environment'
            elif line.method_pro_id:
                parent_op = line.method_pro_id
                work_type = 'method'
            else:
                # Skip if no parent operation
                continue

            # Get PFMEA report
            pfmea_report = parent_op.operations_id if parent_op else False
            if not pfmea_report:
                continue

            # Generate unique problem ID
            if parent_op.process_step_name:
                problem_id = f"PFMEA-{parent_op.process_step_name[:3].upper()}-{work_type[:3].upper()}-{line.id}"
            else:
                problem_id = f"PFMEA-{line.id}-{work_type[:3].upper()}"

            # Create top AP record
            self.create({
                'problem_id': problem_id,
                'process_step_name': parent_op.process_step_name or '',
                'work_type': work_type,
                'failure_mode': parent_op.failure_mode or '',
                'failure_causes': line.failure_causes or '',
                'fmea_ap': line.fmea_ap or '',
                'pfmea_ap': line.pfmea_ap or '',
                'process_operation_id': parent_op.id,
                'process_line_id': line.id,
                'company_id': pfmea_report.company_name.id if pfmea_report.company_name else False,
                'part_id': pfmea_report.part_id.id if pfmea_report.part_id else False,
                'pfmea_id': pfmea_report.id if pfmea_report else False,
            })

        return True


class TopAPPFMEAScheduler(models.Model):
    _name = 'top.ap.pfmea.scheduler'
    _description = 'Top AP for PFMEA Scheduler'

    @api.model
    def refresh_top_ap(self):
        self.env['top.ap.pfmea'].refresh_top_ap_data()
        return True


# Add hooks to update top AP data when process records change
class ProcessOperationsTopAP(models.Model):
    _inherit = 'process.operations'

    @api.model_create_multi
    def create(self, vals_list):
        records = super(ProcessOperationsTopAP, self).create(vals_list)
        self.env['top.ap.pfmea'].refresh_top_ap_data()
        return records

    def write(self, vals):
        result = super(ProcessOperationsTopAP, self).write(vals)
        self.env['top.ap.pfmea'].refresh_top_ap_data()
        return result

    def unlink(self):
        result = super(ProcessOperationsTopAP, self).unlink()
        self.env['top.ap.pfmea'].refresh_top_ap_data()
        return result


class ProcessSubOperationsLinesTopAP(models.Model):
    _inherit = 'process.sub.operations.lines'

    @api.model_create_multi
    def create(self, vals_list):
        records = super(ProcessSubOperationsLinesTopAP, self).create(vals_list)
        self.env['top.ap.pfmea'].refresh_top_ap_data()
        return records

    def write(self, vals):
        result = super(ProcessSubOperationsLinesTopAP, self).write(vals)
        self.env['top.ap.pfmea'].refresh_top_ap_data()
        return result

    def unlink(self):
        result = super(ProcessSubOperationsLinesTopAP, self).unlink()
        self.env['top.ap.pfmea'].refresh_top_ap_data()
        return result