from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PfmeaSuggestion(models.Model):
    _name= 'pfmea.suggestion'
    _description = 'PFMEA Suggestion'
    _rec_name = 'process_step'
    _inherit = "translation.mixin"
    process_step = fields.Char("Process Step", required=True)

    # Basic Information
    issue = fields.Char(string='Issue #')
    hca = fields.Char(string='History/Change Authorization')
    process_item = fields.Char(string='Name of Process')

    # Function of Process Item
    fpi_process_item = fields.Char(string='Process Item')
    fpi_in_plant = fields.Char(string='In Plant')
    fpi_ship_to_plant = fields.Char(string='Ship to Plant')
    fpi_end_user = fields.Char(string='End User')

    # Failure Effects
    fe_in_plant = fields.Char(string='In Plant')
    fe_customer_end = fields.Char(string='Customer End')
    fe_end_user = fields.Char(string='End User')

    station_no = fields.Char(string='Station No.')
    fun_of_process_step = fields.Char(string='Function of Process Step and Product Characteristics')
    failure_mode = fields.Char(string='Failure Mode (FM)')
    special_product_characteristics = fields.Many2one('process.flow.class', string='Special Product Characteristics')
    severity = fields.Integer(string='Severity (S) of FE', default=1)
    # Add relationship to suggestion lines
    man_line_ids = fields.One2many('pfmea.suggestion.line', 'man_pro_id',
                                   string='Man Lines',

                                   )
    machine_line_ids = fields.One2many('pfmea.suggestion.line', 'machine_pro_id',
                                       string='Machine Lines',
                                       )
    material_line_ids = fields.One2many('pfmea.suggestion.line', 'material_pro_id',
                                        string='Material Lines',

                                        )
    environment_line_ids = fields.One2many('pfmea.suggestion.line', 'environment_pro_id',
                                           string='Environment Lines',

                                           )
    method_line_ids = fields.One2many('pfmea.suggestion.line', 'method_pro_id',
                                      string='Method Lines',

                                      )

    # Add active field for archiving
    active = fields.Boolean(default=True)
    _sql_constraints = [
        ('process_step_issue_uniq', 'unique(process_step, issue)', 'Process Step and Issue combination must be unique!')
    ]

    def name_get(self):
        result = []
        for record in self:
            name = record.process_step
            if record.station_no:
                name = f'[{record.station_no}] {name}'
            if record.issue:
                name = f'{name} - Issue: {record.issue}'
            result.append((record.id, name))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('process_step', operator, name), ('station_no', operator, name), ('issue', operator, name)]
        return self.search(domain + args, limit=limit).name_get()

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})

        # Add suffix to process_step to make it unique if not provided
        if 'process_step' not in default:
            default['process_step'] = f"{self.process_step} (Copy)"

        # Generate a new issue number if not provided
        if 'issue' not in default:
            existing_issues = self.search([('process_step', '=', self.process_step)])
            max_issue = 0
            for existing in existing_issues:
                try:
                    if existing.issue and existing.issue.isdigit():
                        issue_num = int(existing.issue)
                        max_issue = max(max_issue, issue_num)
                except ValueError:
                    continue
            default['issue'] = f"{max_issue + 1:02d}"

        # Create the copy of the main record
        new_suggestion = super(PfmeaSuggestion, self).copy(default)

        # Copy associated lines for each type
        line_types = [
            ('man_line_ids', 'man_pro_id'),
            ('machine_line_ids', 'machine_pro_id'),
            ('material_line_ids', 'material_pro_id'),
            ('environment_line_ids', 'environment_pro_id'),
            ('method_line_ids', 'method_pro_id'),
        ]

        for line_field, ref_field in line_types:
            for line in getattr(self, line_field):
                line_default = {
                    ref_field: new_suggestion.id,
                    'status': 'untouched',  # Reset status for new copy
                    'completion_date': False,  # Clear completion date
                    'target_completion_date': False,  # Clear target date
                    'action_taken': False,  # Clear action taken
                }
                line.copy(line_default)

        return new_suggestion


class PfmeaSuggestionLine(models.Model):
    _name = 'pfmea.suggestion.line'
    _description = 'PFMEA Suggestion Line'
    _inherit = "translation.mixin"



    man_pro_id = fields.Many2one('pfmea.suggestion', string='Man Process Reference')
    machine_pro_id = fields.Many2one('pfmea.suggestion', string='Machine Process Reference')
    material_pro_id = fields.Many2one('pfmea.suggestion', string='Material Process Reference')
    environment_pro_id = fields.Many2one('pfmea.suggestion', string='Environment Process Reference')
    method_pro_id = fields.Many2one('pfmea.suggestion', string='Method Process Reference')

    work_type = fields.Selection(
        [
            ('man', 'Man'),
            ('machine', 'Machine'),
            ('material', 'Material'),
            ('environment', 'Environment'),
            ('method', 'Method')
        ],

        string="4M Type",
        readonly=True,

    )
    process_work_element = fields.Text(string="Process Work Element",translate=True)
    function_of_process_work_element = fields.Text(
        string="Function of Process Work Element and Process Characteristics",translate=True)
    severity = fields.Integer(string='Severity (S) of FE', compute='_compute_severity', store=True)
    failure_causes = fields.Char(string='Failure Causes (FC)',translate=True)
    current_prevention_control = fields.Char(string='Current Prevention Control of FC',translate=True)
    occurrence = fields.Integer(string='Occurrence (O) of FC', help="Occurrence rating from 1-10", default=1)
    current_detection_control = fields.Char(string='Current Detection Control of FC or FM',translate=True)
    detection = fields.Integer(string='Detection (D) of FC/FM', help="Detection rating from 1-10", default=1)
    fmea_ap = fields.Char(string="FMEA AP", compute='_compute_fmea_ap', store=True,translate=True)

    filter_code = fields.Text(string='Filter Code (Optional)',translate=True)
    prevention_action = fields.Text(string='Prevention Action',translate=True)
    detection_action = fields.Text(string='Detection Action',translate=True)
    responsible_person_name = fields.Char(string='Responsible Person Name',translate=True)
    target_completion_date = fields.Date(string='Target Completion Date')
    status = fields.Selection([
        ('untouched', 'Untouched'),
        ('under_consideration', 'Under Consideration'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('discarded', 'Discarded'),
    ], string='Status')
    action_taken = fields.Text(string='Action Taken (with pointer to evidence)',translate=True)
    completion_date = fields.Date(string='Completion Date')

    severity_level = fields.Integer(string='Severity Level', help="Severity rating from 1-10", default=1)
    occurrence_level = fields.Integer(string='Occurrence Level', help="Occurrence rating from 1-10", default=1)
    detection_level = fields.Integer(string='Detection Level', help="Detection rating from 1-10", default=1)

    special_characteristics = fields.Text(string='Special Characteristics',translate=True)
    pfmea_ap = fields.Char(string='PFMEA AP', compute='_compute_fmea_ap_level', store=True,translate=True)
    remarks = fields.Text(string='Remarks',translate=True)

    @api.depends('man_pro_id.severity', 'machine_pro_id.severity', 'material_pro_id.severity',
                 'environment_pro_id.severity', 'method_pro_id.severity')
    def _compute_severity(self):
        """
        Compute the severity based on the parent process.operations record,
        regardless of which reference field is set.
        """
        for record in self:
            # Check each reference field and use the severity from the linked process.operations
            if record.man_pro_id:
                record.severity = record.man_pro_id.severity
            elif record.machine_pro_id:
                record.severity = record.machine_pro_id.severity
            elif record.material_pro_id:
                record.severity = record.material_pro_id.severity
            elif record.environment_pro_id:
                record.severity = record.environment_pro_id.severity
            elif record.method_pro_id:
                record.severity = record.method_pro_id.severity
            else:
                record.severity = 1  # Default value if no parent is linked

    @api.depends('severity', 'occurrence', 'detection')
    def _compute_fmea_ap(self):
        for record in self:
            if record.occurrence and record.occurrence > 10:
                raise ValidationError("OCC Value should not exceed 10")
            if record.detection and record.detection > 10:
                raise ValidationError("Detection Value should not exceed 10")
            if record.occurrence and record.occurrence < 1:
                raise ValidationError("OCC Value should not be less than 1")
            if record.detection and record.detection < 1:
                raise ValidationError("Detection Value should not be less than 1")

            else:
                # Define lookup table for action priority (AP)
                ap_lookup = {
                    (9, 10): {
                        (8, 10): {7: 'H', 5: 'H', 2: 'H', 1: 'H'},
                        (6, 7): {7: 'H', 5: 'H', 2: 'H', 1: 'H'},
                        (4, 5): {7: 'H', 5: 'H', 2: 'H', 1: 'M'},
                        (2, 3): {7: 'H', 5: 'M', 2: 'L', 1: 'L'},
                        (0, 1): 'L',
                    },
                    (7, 8): {
                        (8, 10): {7: 'H', 5: 'H', 2: 'H', 1: 'H'},
                        (6, 7): {7: 'H', 5: 'H', 2: 'H', 1: 'M'},
                        (4, 5): {7: 'H', 5: 'M', 2: 'M', 1: 'M'},
                        (2, 3): {7: 'M', 5: 'M', 2: 'L', 1: 'L'},
                        (0, 1): 'L',
                    },

                    (4, 6): {
                        (8, 10): {7: 'H', 5: 'H', 2: 'M', 1: 'M'},
                        (6, 7): {7: 'M', 5: 'M', 2: 'M', 1: 'L'},
                        (4, 5): {7: 'M', 5: 'L', 2: 'L', 1: 'L'},
                        (2, 3): 'L',
                        (0, 1): 'L',
                    },
                    (2, 3): {
                        (8, 10): {6: 'M', 4: 'M', 1: 'L', 0: 'L'},
                        (6, 7): 'L',
                        (4, 5): 'L',
                        (2, 3): 'L',
                        (0, 1): 'L',
                    },
                    (0, 1): {
                        (1, 10): 'L'
                    }
                }

                # Default value if no match is found
                record.fmea_ap = 'L'

                # Find correct severity range
                for sev_range, occ_dict in ap_lookup.items():
                    if sev_range[0] <= record.severity <= sev_range[1]:
                        # Find correct occurrence range
                        for occ_range, det_dict in occ_dict.items():
                            if occ_range[0] <= record.occurrence <= occ_range[1]:
                                # Assign action priority based on detection
                                if isinstance(det_dict, dict):  # If detection mapping exists
                                    for det_threshold, ap_value in det_dict.items():
                                        if record.detection >= det_threshold:
                                            record.fmea_ap = ap_value
                                            break
                                else:  # If no detection mapping, assign the value directly
                                    record.fmea_ap = det_dict
                                break
                        break

    @api.depends('severity_level', 'occurrence_level', 'detection_level')
    def _compute_fmea_ap_level(self):
        for record in self:
            # Validation for severity, occurrence, and detection

            if record.severity_level > 10:
                raise ValidationError("Severity Level should not exceed 10")
            if record.occurrence_level > 10:
                raise ValidationError("Occurrence Level should not exceed 10")
            if record.detection_level > 10:
                raise ValidationError("Detection Level should not exceed 10")
            if record.severity_level < 1:
                raise ValidationError("Severity Level should not be less than 1")
            if record.occurrence_level < 1:
                raise ValidationError("Occurrence Level should not be less than 1")
            if record.detection_level < 1:
                raise ValidationError("Detection Level should not be less than 1")
            # Define lookup table for action priority (AP) based on severity_level, occurrence_level, and detection_level

            ap_lookup = {
                (9, 10): {
                    (8, 10): {7: 'H', 5: 'H', 2: 'H', 1: 'H'},
                    (6, 7): {7: 'H', 5: 'H', 2: 'H', 1: 'H'},
                    (4, 5): {7: 'H', 5: 'H', 2: 'H', 1: 'M'},
                    (2, 3): {7: 'H', 5: 'M', 2: 'L', 1: 'L'},
                    (0, 1): 'L',
                },
                (7, 8): {
                    (8, 10): {7: 'H', 5: 'H', 2: 'H', 1: 'H'},
                    (6, 7): {7: 'H', 5: 'H', 2: 'H', 1: 'M'},
                    (4, 5): {7: 'H', 5: 'M', 2: 'M', 1: 'M'},
                    (2, 3): {7: 'M', 5: 'M', 2: 'L', 1: 'L'},
                    (0, 1): 'L',
                },

                (4, 6): {
                    (8, 10): {7: 'H', 5: 'H', 2: 'M', 1: 'M'},
                    (6, 7): {7: 'M', 5: 'M', 2: 'M', 1: 'L'},
                    (4, 5): {7: 'M', 5: 'L', 2: 'L', 1: 'L'},
                    (2, 3): 'L',
                    (0, 1): 'L',
                },
                (2, 3): {
                    (8, 10): {6: 'M', 4: 'M', 1: 'L', 0: 'L'},
                    (6, 7): 'L',
                    (4, 5): 'L',
                    (2, 3): 'L',
                    (0, 1): 'L',
                },
                (0, 1): {
                    (1, 10): 'L'
                }
            }

            # Default value if no match is found
            record.pfmea_ap = 'L'

            # Find correct severity range for severity_level
            for sev_range, occ_dict in ap_lookup.items():
                if sev_range[0] <= record.severity_level <= sev_range[1]:
                    # Find correct occurrence range for occurrence_level
                    for occ_range, det_dict in occ_dict.items():
                        if occ_range[0] <= record.occurrence_level <= occ_range[1]:
                            # Assign action priority based on detection_level
                            if isinstance(det_dict, dict):  # If detection mapping exists
                                for det_threshold, ap_value in det_dict.items():
                                    if record.detection_level >= det_threshold:
                                        record.pfmea_ap = ap_value
                                        break
                            else:  # If no detection mapping, assign the value directly
                                record.pfmea_ap = det_dict
                            break
                    break

