from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PFMEADashboard(models.Model):
    _name = 'pfmea.dashboard'
    _description = 'PFMEA Dashboard'
    _rec_name = 'problem_id'

    problem_id = fields.Char(string='Problem ID', readonly=True)
    issue = fields.Char(string='Issue #', readonly=True)
    process_step_name = fields.Char(string='Process Step', readonly=True)
    prevention_action = fields.Text(string='Prevention Action', readonly=True)
    detection_action = fields.Text(string='Detection Action', readonly=True)
    target_completion_date = fields.Date(string='Target Completion Date', readonly=True)
    responsible_person_name = fields.Many2one('res.users', string='Responsible Person', readonly=True)
    status = fields.Selection([
        ('untouched', 'Untouched'),
        ('under_consideration', 'Under Consideration'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('discarded', 'Discarded'),
    ], string='Status', readonly=True)
    color = fields.Integer(compute="_compute_color", store=True)

    @api.depends('status')
    def _compute_color(self):
        for record in self:
            status_color_map = {
                'untouched': 4,  # Grey
                'under_consideration': 3,  # Yellow
                'in_progress': 2,  # Blue
                'completed': 10,  # Green
                'discarded': 1,  # Red
            }
            record.color = status_color_map.get(record.status, 0)

    process_operation_id = fields.Many2one('pfmea.operations', string='Process Operation', readonly=True)
    process_line_id = fields.Many2one('pfmea.operations.line', string='Process Line', readonly=True)
    work_type = fields.Selection([
        ('man', 'Man'),
        ('machine', 'Machine'),
        ('material', 'Material'),
        ('environment', 'Environment'),
        ('method', 'Method')
    ], string="4M Type", readonly=True)

    # For filtering in views
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    pfmea_id = fields.Many2one('asd.pfmea', string='PFMEA Report', readonly=True)
    part_id = fields.Many2one("product.template", string="Part", readonly=True)

    @api.model
    def refresh_dashboard_data(self):
        """Refresh dashboard data by syncing with process operations and lines"""
        # Clear existing records to prevent duplicates
        self.search([]).unlink()

        # Get all process sub operation lines
        line_records = self.env['pfmea.operations.line'].search([])

        for line in line_records:
            # Determine the parent operation
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
            pfmea_report = parent_op.operations_id

            # Generate unique problem ID
            if parent_op.issue and parent_op.process_step_name:
                problem_id = f"PFMEA-{parent_op.process_step_name[:3].upper()}-{parent_op.issue}-{work_type[:3].upper()}"
            else:
                problem_id = f"PFMEA-{line.id}-{work_type[:3].upper()}"

            # Create dashboard record
            self.create({
                'problem_id': problem_id,
                'issue': parent_op.issue,
                'process_step_name': parent_op.process_step_name,
                'prevention_action': line.prevention_action,
                'detection_action': line.detection_action,
                'target_completion_date': line.target_completion_date,
                'responsible_person_name': line.responsible_person_name.id if line.responsible_person_name else False,
                'status': line.status,
                'process_operation_id': parent_op.id,
                'process_line_id': line.id,
                'work_type': work_type,
                'company_id': pfmea_report.company_name.id if pfmea_report.company_name else False,
                'part_id': pfmea_report.part_id.id if pfmea_report.part_id else False,
                'pfmea_id': pfmea_report.id,
            })

        return True


# Create a scheduled action to refresh the dashboard
class PFMEADashboardScheduler(models.Model):
    _name = 'dashboard.report.scheduler'
    _description = 'PFMEA Dashboard Scheduler'

    @api.model
    def refresh_dashboard(self):
        self.env['pfmea.dashboard'].refresh_dashboard_data()
        return True

# Fixed the duplicate inheritance issue
class PfmeaOperationsLine(models.Model):
    _inherit = 'pfmea.operations.line'
    _description = 'PFMEA Operations Line'

    @api.model_create_multi
    def create(self, vals_list):
        records = super(PfmeaOperationsLine, self).create(vals_list)
        self.env['pfmea.dashboard'].refresh_dashboard_data()
        return records

    def write(self, vals):
        result = super(PfmeaOperationsLine, self).write(vals)
        self.env['pfmea.dashboard'].refresh_dashboard_data()
        return result

    def unlink(self):
        result = super(PfmeaOperationsLine, self).unlink()
        self.env['pfmea.dashboard'].refresh_dashboard_data()
        return result