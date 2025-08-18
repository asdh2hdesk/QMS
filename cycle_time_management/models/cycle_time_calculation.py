from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
import base64
import xlsxwriter
from io import BytesIO


_logger = logging.getLogger(__name__)


class CycleTimeCalculation(models.Model):
    _name = 'cycle.time.calculation'
    _description = 'Manufacturing Cycle Time Calculation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sr_no'

    sr_no = fields.Integer('Sr. No', required=True, default=lambda self: self._get_next_sr_no())
    part_number = fields.Many2one(
        'product.product', string='Part Number', required=True
    )
    part_name = fields.Char(related='part_number.name', string='Part Name', store=True)
    operation_shift_ids = fields.One2many('cycle.time.operation.shift', 'calculation_id', string='Operations & Shifts')
    configuration_id = fields.Many2one('cycle.time.configuration', string='Configuration', default=lambda self: self._default_configuration_id())

    def _get_next_sr_no(self):
        last_record = self.search([], order='sr_no desc', limit=1)
        return last_record.sr_no + 1 if last_record else 1

    @api.model
    def _default_configuration_id(self):
        """
        Safe default method for configuration_id.
        Avoids querying during module installation.
        """
        if not self.env.registry.ready:
            return False
        config = self.env['cycle.time.configuration'].search([('active', '=', True)], limit=1)
        return config.id if config else False

    def name_get(self):
        result = []
        for record in self:
            first_operation_name = record.operation_shift_ids[:1].operation_name or 'No Operation'
            name = f"[{record.sr_no}] {record.part_name or 'Unknown'} - {first_operation_name}"
            result.append((record.id, name))
        return result

    def action_calculate_all(self):
        """Recalculate all computed fields for this record"""
        for operation in self.operation_shift_ids:
            operation._compute_efficiency_days_required()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success!',
                'message': 'All calculations have been updated.',
                'type': 'success',
            }
        }

    def action_show_calculation_details(self):
        if not self.id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Save the record first!',
                    'message': 'Please save the Cycle Time Calculation before viewing details.',
                    'type': 'warning',
                }
            }

        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Calculation Details - {self.part_name or "Unknown Part"}',
            'res_model': 'cycle.time.calculation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_calculation_id': self.id},
        }


class CycleTimeOperationShift(models.Model):
    _name = 'cycle.time.operation.shift'
    _description = 'Cycle Time Operation with Shift'
    _order = 'operation_pfd_id'

    calculation_id = fields.Many2one(
        'cycle.time.calculation',
        string='Part',
        ondelete='cascade'
    )
    s_no = fields.Integer('Sr. No', compute='_compute_s_no', store=False)

    # Operation Info
    operation_pfd_id = fields.Many2one('process.flow.line', string='Operation Number')
    operation_name = fields.Char(
        'Operation Name',
        related='operation_pfd_id.desc_of_operation',
        store=True,
        readonly=True
    )
    equipment_id = fields.Many2one(
        'maintenance.equipment', string='Machine Number', required=True
    )

    # Shift Information
    available_shift_working = fields.Selection([
        ('A', 'Shift A'),
        ('B', 'Shift B'),
        ('C', 'Shift C')
    ], string='Shift', required=False)
    shift_hours = fields.Float('Shift Hours', default=8.0)

    # Main Inputs
    cycle_time_minutes = fields.Float('Cycle Time (Minutes)', required=True)
    volume_per_month = fields.Float('Volume/Month', required=True)
    plant_efficiency = fields.Float('Plant Efficiency (%)', default=85.0, required=True)

    # Computed Field
    efficiency_days_required = fields.Float(
        'No. of Days Required for Production',
        compute='_compute_efficiency_days_required',
        store=True
    )

    @api.depends('calculation_id.operation_shift_ids', 'operation_pfd_id')
    def _compute_s_no(self):
        for rec in self:
            rec.s_no = 0
            if not rec.calculation_id or not rec.operation_pfd_id:
                continue

            try:
                valid_records = rec.calculation_id.operation_shift_ids.filtered(
                    lambda x: x.operation_pfd_id
                )
                ordered_records = valid_records.sorted(
                    key=lambda x: x.operation_pfd_id.id
                )
                for idx, record in enumerate(ordered_records, start=1):
                    if record == rec:
                        rec.s_no = idx
                        break
            except Exception as e:
                _logger.warning(f"Error computing s_no for record {rec.id}: {e}")
                rec.s_no = 0

    @api.depends('volume_per_month', 'cycle_time_minutes', 'plant_efficiency', 'shift_hours',
                 'calculation_id.configuration_id')
    def _compute_efficiency_days_required(self):
        for rec in self:
            rec.efficiency_days_required = 0.0
            if not rec.cycle_time_minutes or not rec.volume_per_month:
                continue

            try:
                config = rec.calculation_id.configuration_id or self.env[
                    'cycle.time.configuration'].get_default_config()
                calc_values = rec._calculate_all_values(config)
                rec.efficiency_days_required = calc_values.get('efficiency_days_required', 0.0)
            except Exception as e:
                _logger.warning(f"Error computing efficiency days for record {rec.id}: {e}")
                rec.efficiency_days_required = 0.0

    def _calculate_all_values(self, config=None):
        """Calculate all values using the configuration formulas"""
        if not config:
            config = self.calculation_id.configuration_id or self.env['cycle.time.configuration'].get_default_config()

        # Initialize variables
        variables = {
            'shift_hours': self.shift_hours or 0.0,
            'cycle_time_minutes': self.cycle_time_minutes or 0.0,
            'volume_per_month': self.volume_per_month or 0.0,
            'plant_efficiency': self.plant_efficiency or 0.0,
            'working_days_per_month': config.working_days_per_month,
            'shifts_per_day': config.shifts_per_day,
            'hours_per_day': config.hours_per_day,
            'seconds_per_day': config.seconds_per_day,
        }

        result = {}

        # Skip if essential values are missing
        if variables['shift_hours'] <= 0 or variables['cycle_time_minutes'] <= 0 or variables['volume_per_month'] <= 0:
            return {key: 0.0 for key in [
                'shift_minutes', 'shift_seconds', 'volume_per_day', 'volume_per_shift',
                'volume_per_hour', 'takt_time_seconds', 'cycle_time_seconds',
                'output_per_hour', 'output_per_shift', 'output_per_day', 'output_per_month',
                'days_required', 'actual_takt_time_base', 'actual_takt_time_seconds_eff',
                'actual_takt_time_seconds', 'efficiency_output_per_hour', 'efficiency_output_per_shift',
                'efficiency_output_per_day', 'efficiency_output_per_month', 'efficiency_days_required'
            ]}

        try:
            # Calculate step by step using formulas
            formulas = [
                ('shift_minutes', config.shift_minutes_formula),
                ('shift_seconds', config.shift_seconds_formula),
                ('volume_per_day', config.volume_per_day_formula),
                ('volume_per_shift', config.volume_per_shift_formula),
                ('volume_per_hour', config.volume_per_hour_formula),
                ('takt_time_seconds', config.takt_time_seconds_formula),
                ('cycle_time_seconds', config.cycle_time_seconds_formula),
                ('output_per_hour', config.output_per_hour_formula),
                ('output_per_shift', config.output_per_shift_formula),
                ('output_per_day', config.output_per_day_formula),
                ('output_per_month', config.output_per_month_formula),
                ('days_required', config.days_required_formula),
                ('actual_takt_time_base', config.actual_takt_time_base_formula),
                ('actual_takt_time_seconds_eff', config.actual_takt_time_seconds_eff_formula),
                ('actual_takt_time_seconds', config.actual_takt_time_seconds_formula),
                ('efficiency_output_per_hour', config.efficiency_output_per_hour_formula),
                ('efficiency_output_per_shift', config.efficiency_output_per_shift_formula),
                ('efficiency_output_per_day', config.efficiency_output_per_day_formula),
                ('efficiency_output_per_month', config.efficiency_output_per_month_formula),
                ('efficiency_days_required', config.efficiency_days_required_formula),
            ]

            for field_name, formula in formulas:
                try:
                    # Update variables with previously calculated values
                    variables.update(result)

                    # Safely evaluate the formula
                    if formula and variables.get('cycle_time_minutes', 0) > 0:
                        # Replace division by zero checks
                        safe_formula = formula
                        value = eval(safe_formula, {"__builtins__": {}}, variables)
                        result[field_name] = float(value) if value and not (
                                    isinstance(value, float) and (value != value or value == float('inf'))) else 0.0
                    else:
                        result[field_name] = 0.0
                except:
                    result[field_name] = 0.0

        except Exception as e:
            _logger.warning(f"Error in formula calculations: {e}")
            result = {key: 0.0 for key in result.keys()}

        return result

    def name_get(self):
        result = []
        for rec in self:
            part = rec.calculation_id.part_name if rec.calculation_id else 'Unknown'
            op = rec.operation_name or 'Unknown'
            shift = rec.available_shift_working or 'N/A'
            result.append((rec.id, f"{part} - {op} (Shift {shift})"))
        return result


class CycleTimeShiftWizard(models.TransientModel):
    _name = 'cycle.time.shift.wizard'
    _description = 'Shift Cycle Time Calculation Details'

    shift_id = fields.Many2one('cycle.time.shift', string='Shift')

    # Input fields - these will be populated from the actual shift record
    shift_hours = fields.Float('Shift Hours', default=8.0)
    cycle_time_minutes = fields.Float('Cycle Time (Minutes)')
    volume_per_month = fields.Float('Volume/Month')
    plant_efficiency = fields.Float('Plant Efficiency (%)', default=85.0)

    # Computed fields showing all the calculations
    shift_minutes = fields.Float('Shift Minutes', compute='_compute_all_calculations')
    shift_seconds = fields.Float('Shift Seconds', compute='_compute_all_calculations')
    volume_per_day = fields.Float('Volume/Day', compute='_compute_all_calculations')
    volume_per_shift = fields.Float('Volume/Shift', compute='_compute_all_calculations')
    volume_per_hour = fields.Float('Volume/Hour', compute='_compute_all_calculations')
    takt_time_seconds = fields.Float('Takt Time (Seconds)', compute='_compute_all_calculations')
    cycle_time_seconds = fields.Float('Cycle Time (Seconds)', compute='_compute_all_calculations')
    output_per_hour = fields.Float('Output/Hour', compute='_compute_all_calculations')
    output_per_shift = fields.Float('Output/Shift', compute='_compute_all_calculations')
    output_per_day = fields.Float('Output/Day', compute='_compute_all_calculations')
    output_per_month = fields.Float('Output/Month', compute='_compute_all_calculations')
    days_required = fields.Float('Days Required', compute='_compute_all_calculations')
    actual_takt_time_base = fields.Float('Actual Takt Time Base (Seconds)', compute='_compute_live_calculations',store=False)
    actual_takt_time_seconds = fields.Float('Actual Takt Time (Seconds)', compute='_compute_all_calculations')
    efficiency_output_per_hour = fields.Float('Efficiency Output/Hour', compute='_compute_all_calculations')
    efficiency_output_per_shift = fields.Float('Efficiency Output/Shift', compute='_compute_all_calculations')
    efficiency_output_per_day = fields.Float('Efficiency Output/Day', compute='_compute_all_calculations')
    efficiency_output_per_month = fields.Float('Efficiency Output/Month', compute='_compute_all_calculations')
    efficiency_days_required = fields.Float('Efficiency Days Required', compute='_compute_all_calculations')

    @api.depends('shift_hours', 'cycle_time_minutes', 'volume_per_month', 'plant_efficiency')
    def _compute_all_calculations(self):
        for wizard in self:
            try:
                # Initialize all fields to 0 first
                fields_to_reset = [
                    'shift_minutes', 'shift_seconds', 'volume_per_day', 'volume_per_shift',
                    'volume_per_hour', 'takt_time_seconds', 'cycle_time_seconds',
                    'output_per_hour', 'output_per_shift', 'output_per_day', 'output_per_month',
                    'days_required', 'actual_takt_time_seconds', 'actual_takt_time_base',
                    'efficiency_output_per_hour', 'efficiency_output_per_shift',
                    'efficiency_output_per_day', 'efficiency_output_per_month', 'efficiency_days_required'
                ]
                for field in fields_to_reset:
                    setattr(wizard, field, 0.0)

                # Only proceed if we have the essential data
                if not wizard.shift_hours or wizard.shift_hours <= 0:
                    continue
                if not wizard.cycle_time_minutes or wizard.cycle_time_minutes <= 0:
                    continue
                if not wizard.volume_per_month or wizard.volume_per_month <= 0:
                    continue
                if not wizard.plant_efficiency:
                    continue
                # Basic conversions

                wizard.shift_minutes = wizard.shift_hours * 60 if wizard.shift_hours else 0
                wizard.shift_seconds = wizard.shift_minutes * 60 if wizard.shift_minutes else 0

                # Volume breakdown
                wizard.volume_per_day = wizard.volume_per_month / 25 if wizard.volume_per_month else 0
                wizard.volume_per_shift = wizard.volume_per_day / 24 if wizard.volume_per_day else 0
                wizard.volume_per_hour = wizard.volume_per_shift / wizard.shift_hours if wizard.shift_hours and wizard.volume_per_shift else 0

                # Takt time
                wizard.takt_time_seconds = 86400 / wizard.volume_per_month if wizard.volume_per_month else 0

                # Cycle time
                wizard.cycle_time_seconds = wizard.cycle_time_minutes * 60 if wizard.cycle_time_minutes else 0

                # Output calculations
                wizard.output_per_hour = 60 / wizard.cycle_time_minutes if wizard.cycle_time_minutes else 0
                wizard.output_per_shift = wizard.output_per_hour * wizard.shift_hours if wizard.output_per_hour and wizard.shift_hours else 0
                wizard.output_per_day = wizard.output_per_shift * 3 if wizard.output_per_shift else 0
                wizard.output_per_month = wizard.output_per_day * 25 if wizard.output_per_day else 0

                # Days required
                wizard.days_required = wizard.volume_per_month / wizard.output_per_day if wizard.output_per_day and wizard.volume_per_month else 0

                # Actual takt time with efficiency
                wizard.actual_takt_time_base = 86400 / wizard.output_per_month if wizard.output_per_month else 0

                wizard.actual_takt_time_seconds_eff = ((100 - wizard.plant_efficiency) / 100) * wizard.actual_takt_time_base + wizard.actual_takt_time_base

                wizard.actual_takt_time_seconds = ((100 - wizard.plant_efficiency)/100) * wizard.cycle_time_minutes + wizard.cycle_time_minutes

                # Efficiency outputs
                wizard.efficiency_output_per_hour = 60 / wizard.actual_takt_time_seconds
                wizard.efficiency_output_per_shift = wizard.efficiency_output_per_hour * 8
                wizard.efficiency_output_per_day = wizard.efficiency_output_per_shift * 3
                wizard.efficiency_output_per_month = wizard.efficiency_output_per_day * 25
                # wizard.efficiency_output_per_second = ((100 - wizard.plant_efficiency) * wizard.cycle_time_minutes + wizard.cycle_time_minutes) * 60

                wizard.efficiency_days_required = (wizard.volume_per_month / wizard.efficiency_output_per_month) * 25
            except Exception as e:

                # Log error and reset fields
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning(f"Error in shift wizard calculations: {e}")
                for field in fields_to_reset:
                    setattr(wizard, field, 0.0)


class CycleTimeCalculationWizard(models.TransientModel):
    _name = 'cycle.time.calculation.wizard'
    _description = 'Cycle Time Calculation Details Wizard'

    calculation_id = fields.Many2one('cycle.time.calculation', string='Calculation', required=True)
    calculation_table_html = fields.Html('Calculation Details', compute='_compute_calculation_table', store=False)
    excel_file = fields.Binary('Excel File', readonly=True)
    excel_filename = fields.Char('Excel Filename')

    @api.depends('calculation_id')
    def _compute_calculation_table(self):
        """Generate HTML table with all calculation details"""
        for wizard in self:
            if not wizard.calculation_id or not wizard.calculation_id.operation_shift_ids:
                wizard.calculation_table_html = "<p>No calculation data available. Please add operations.</p>"
                continue

            config = wizard.calculation_id.configuration_id or self.env['cycle.time.configuration'].get_default_config()

            # Start building the HTML table
            html = """
                        <style>
                            .calc-table { 
                                width: 100%; 
                                border-collapse: collapse; 
                                font-size: 13px; 
                                margin-top: 15px;
                                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                                text-align: center;
                            }
                            .calc-table th { 
                                background-color: #f8f9fa; 
                                font-weight: bold; 
                                padding: 8px 6px;
                                border: 1px solid #dee2e6;
                                text-align: center;
                                vertical-align: middle;
                                font-size: 12px;
                                text-align: center;
                            }
                            .calc-table thead {
                                text-align: center;
                            }
                            .calc-table thead th {
                                text-align: center;
                                vertical-align: middle;
                            }
                            .calc-table td { 
                                padding: 6px; 
                                border: 1px solid #dee2e6;
                                text-align: center;
                                vertical-align: middle;
                            }
                            .calc-table tbody tr:nth-child(even) {
                                background-color: #f8f9fa;
                            }
                            .calc-table tbody tr:hover {
                                background-color: #e3f2fd;
                            }
                            .number { 
                                text-align: center !important;
                                font-family: 'Courier New', monospace;
                            }
                            .header-group-1 { background-color: #e3f2fd !important; text-align: center !important; }
                            .header-group-2 { background-color: #f3e5f5 !important; text-align: center !important; }
                            .header-group-3 { background-color: #e8f5e8 !important; text-align: center !important; }
                            .header-group-4 { background-color: #fff3e0 !important; text-align: center !important; }
                            .header-group-5 { background-color: #fce4ec !important; text-align: center !important; }
                            .header-group-6 { background-color: #e1f5fe !important; text-align: center !important; }
                            .header-group-7 { background-color: #f1f8e9 !important; text-align: center !important; }
                            .header-group-8 { background-color: #fff8e1 !important; text-align: center !important; }
                        </style>
                        <div style="overflow-x: auto; margin-top: 10px;">
                            <table class="calc-table">
                                <thead>
                                    <tr>
                                        <th rowspan="2" style="min-width: 60px; text-align: center !important;">Sr. No</th>
                                        <th rowspan="2" style="min-width: 120px; text-align: center !important;">Part Number</th>
                                        <th rowspan="2" style="min-width: 150px; text-align: center !important;">Part Name</th>
                                        <th rowspan="2" style="min-width: 100px; text-align: center !important;">Operation ID</th>
                                        <th rowspan="2" style="min-width: 150px; text-align: center !important;">Operation Name</th>
                                        <th rowspan="2" style="min-width: 120px; text-align: center !important;">Machine</th>
                                        <th colspan="3" class="header-group-1 text-align: center !important;">Available Shift Working</th>
                                        <th colspan="5" class="header-group-2 text-align: center !important;"> Customer Demand During Planning</th>
                                        <th colspan="2" class="header-group-3 text-align: center !important;">Actual Output to Produce/part</th>
                                        <th colspan="5" class="header-group-4 text-align: center !important;">No. of Days Required to Manufacture</th>
                                        <th rowspan="2" class="header-group-5 text-align: center !important;">Acutal Takt time (In second)</th>
                                        <th rowspan="2" class="header-group-6 text-align: center !important;">Plant Efficiency</th>
                                        <th rowspan="2" class="header-group-7 text-align: center !important;">Output with Efficiency Acutal Takt time(In second)</th>
                                        <th colspan="6" class="header-group-8 text-align: center !important;">No. of Days Required to Manufacture</th>					
                                    </tr>
                                    <tr>
                                        <th class="header-group-1" style="min-width: 90px;">In hours</th>
                                        <th class="header-group-1" style="min-width: 100px;">In mins</th>
                                        <th class="header-group-1" style="min-width: 90px;">In seconds</th>
                                        <th class="header-group-2" style="min-width: 90px;">Volume/Month</th>
                                        <th class="header-group-2" style="min-width: 90px;">Volume/Day</th>
                                        <th class="header-group-2" style="min-width: 90px;">Volume/shift</th>
                                        <th class="header-group-2" style="min-width: 90px;">Volume/Hour</th>
                                        <th class="header-group-2" style="min-width: 90px;">Takt time in Seconds</th>
                                        <th class="header-group-3" style="min-width: 90px;">Cycle time in mins</th>
                                        <th class="header-group-3" style="min-width: 90px;">In seconds</th>
                                        <th class="header-group-4" style="min-width: 90px;">In hour</th>
                                        <th class="header-group-4" style="min-width: 90px;">In Shift</th>
                                        <th class="header-group-4" style="min-width: 90px;">In day</th>
                                        <th class="header-group-4" style="min-width: 90px;">In Month Capacity</th>
                                        <th class="header-group-4" style="min-width: 90px;">No. of Days</th>
                                        <th class="header-group-8" style="min-width: 90px;">In Mins</th>
                                        <th class="header-group-8" style="min-width: 90px;">In hour</th>
                                        <th class="header-group-8" style="min-width: 90px;">In Shift</th>
                                        <th class="header-group-8" style="min-width: 90px;">In day</th>
                                        <th class="header-group-8" style="min-width: 90px;">In Month Capacity</th>
                                        <th class="header-group-8" style="min-width: 90px;">No. of Required Days for Production</th>
                                    </tr>
                                </thead>
                                <tbody>
            """

            # Process all operations and shifts
            for shift in wizard.calculation_id.operation_shift_ids:
                calc_data = shift._calculate_all_values(config)

                html += f"""
                    <tr>
                        <td style="text-align: center;">{shift.s_no}</td>
                        <td style="text-align: center;">{wizard.calculation_id.part_number.default_code or wizard.calculation_id.part_number.name}</td>
                        <td style="text-align: center;">{wizard.calculation_id.part_name or ''}</td>
                        <td style="text-align: center;">{shift.operation_pfd_id.desc_of_operation if shift.operation_pfd_id else ''}</td>
                        <td style="text-align: center;">{shift.operation_name or ''}</td>
                        <td style="text-align: center;">{shift.equipment_id.name if shift.equipment_id else ''}</td>

                        <!-- Available Shift Working -->
                        <td style="text-align: center;">{shift.shift_hours}</td>
                        <td style="text-align: center;">{calc_data.get('shift_minutes', 0):.2f}</td>
                        <td style="text-align: center;">{calc_data.get('shift_seconds', 0):.2f}</td>

                        <!--  Customer Demand During Planning -->
                        <td style="text-align: center;">{shift.volume_per_month}</td>
                        <td style="text-align: center;">{calc_data.get('volume_per_day', 0):.2f}</td>
                        <td style="text-align: center;">{calc_data.get('volume_per_shift', 0):.4f}</td>
                        <td style="text-align: center;">{calc_data.get('volume_per_hour', 0):.4f}</td>
                        <td style="text-align: center;">{calc_data.get('takt_time_seconds', 0):.2f}</td>

                        <!--  Actual Output to produce/part	 -->
                        <td style="text-align: center;">{shift.cycle_time_minutes}</td>
                        <td style="text-align: center;">{calc_data.get('cycle_time_seconds', 0):.2f}</td>

                        <!--  No. of days required to Manufacture	 -->	
                        <td style="text-align: center;">{calc_data.get('output_per_hour', 0):.2f}</td>
                        <td style="text-align: center;">{calc_data.get('output_per_shift', 0):.2f}</td>
                        <td style="text-align: center;">{calc_data.get('output_per_day', 0):.2f}</td>
                        <td style="text-align: center;">{calc_data.get('output_per_month', 0):.2f}</td>
                        <td style="text-align: center;">{calc_data.get('days_required', 0):.2f}</td>	

                        <!--  Acutal Takt time In Second	 -->
                        <td style="text-align: center;">{calc_data.get('actual_takt_time_base', 0):.2f}</td>

                        <!--  Plant Efficiency  -->
                        <td style="text-align: center;">{shift.plant_efficiency}</td>	

                        <!--  Output with efficiency Acutal Takt time  -->
                        <td style="text-align: center;">{calc_data.get('actual_takt_time_seconds_eff', 0):.2f}</td>	

                        <!--  No. of days required to Manufacture	 -->	
                        <td style="text-align: center;">{calc_data.get('actual_takt_time_seconds', 0):.2f}</td>
                        <td style="text-align: center;">{calc_data.get('efficiency_output_per_hour', 0):.2f}</td>
                        <td style="text-align: center;">{calc_data.get('efficiency_output_per_shift', 0):.2f}</td>	                            
                        <td style="text-align: center;">{calc_data.get('efficiency_output_per_day', 0):.2f}</td>
                        <td style="text-align: center;">{calc_data.get('efficiency_output_per_month', 0):.2f}</td>
                        <td style="text-align: center;">{calc_data.get('efficiency_days_required', 0):.2f}</td>
                    </tr>
                """

            html += """
                    </tbody>
                </table>
            </div>
            <br/>
            """

            wizard.calculation_table_html = html

    def _calculate_shift_values(self, shift):
        """Calculate all values for a given shift record"""
        try:
            # Get basic values
            shift_hours = shift.shift_hours or 0.0
            cycle_time_minutes = shift.cycle_time_minutes or 0.0
            volume_per_month = shift.volume_per_month or 0.0
            plant_efficiency = shift.plant_efficiency or 0.0

            # Initialize result dictionary
            result = {
                'shift_hours': shift_hours,
                'cycle_time_minutes': cycle_time_minutes,
                'volume_per_month': volume_per_month,
                'plant_efficiency': plant_efficiency,
                'shift_minutes': 0.0,
                'shift_seconds': 0.0,
                'volume_per_day': 0.0,
                'volume_per_shift': 0.0,
                'volume_per_hour': 0.0,
                'takt_time_seconds': 0.0,
                'cycle_time_seconds': 0.0,
                'output_per_hour': 0.0,
                'output_per_shift': 0.0,
                'output_per_day': 0.0,
                'output_per_month': 0.0,
                'days_required': 0.0,
                'actual_takt_time_base': 0.0,
                'actual_takt_time_seconds_eff': 0.0,
                'actual_takt_time_seconds': 0.0,
                'efficiency_output_per_hour': 0.0,
                'efficiency_output_per_shift': 0.0,
                'efficiency_output_per_day': 0.0,
                'efficiency_output_per_month': 0.0,
                'efficiency_days_required': 0.0,
            }

            # Only calculate if we have valid input values
            if shift_hours <= 0 or cycle_time_minutes <= 0 or volume_per_month <= 0:
                return result

            # Basic conversions
            result['shift_minutes'] = shift_hours * 60
            result['shift_seconds'] = result['shift_minutes'] * 60
            result['cycle_time_seconds'] = cycle_time_minutes * 60

            # Volume breakdown
            result['volume_per_day'] = volume_per_month / 25
            result['volume_per_shift'] = result['volume_per_day'] / 24  # 24-hour operation
            result['volume_per_hour'] = result['volume_per_shift'] / shift_hours

            # Takt time
            result['takt_time_seconds'] = 86400 / volume_per_month

            # Output calculations
            result['output_per_hour'] = 60 / cycle_time_minutes
            result['output_per_shift'] = result['output_per_hour'] * shift_hours
            result['output_per_day'] = result['output_per_shift'] * 3  # 3 shifts per day
            result['output_per_month'] = result['output_per_day'] * 25  # 25 working days

            # Days required
            if result['output_per_day'] > 0:
                result['days_required'] = volume_per_month / result['output_per_day']

            # Actual takt time calculations
            if result['output_per_month'] > 0:
                result['actual_takt_time_base'] = 86400 / result['output_per_month']

            if plant_efficiency > 0:
                result['actual_takt_time_seconds_eff'] = ((100 - plant_efficiency) / 100) * result['actual_takt_time_base'] + result['actual_takt_time_base']

            if plant_efficiency > 0:
                result['actual_takt_time_seconds'] = ((100 - plant_efficiency) / 100) * cycle_time_minutes + cycle_time_minutes


            # Efficiency calculations
            if result['actual_takt_time_seconds'] > 0:
                result['efficiency_output_per_hour'] = 60 / result['actual_takt_time_seconds']
                result['efficiency_output_per_shift'] = result['efficiency_output_per_hour'] * 8
                result['efficiency_output_per_day'] = result['efficiency_output_per_shift'] * 3
                result['efficiency_output_per_month'] = result['efficiency_output_per_day'] * 25

                if result['efficiency_output_per_month'] > 0:
                    result['efficiency_days_required'] = (volume_per_month / result['efficiency_output_per_month']) * 25

            return result

        except Exception as e:
            # Log error and return zero values
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning(f"Error calculating shift values: {e}")
            return result

    def action_export_to_excel(self):
        """Generate Excel export for the calculation details."""
        self.ensure_one()

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Calculation Details')

        # === Define Styles ===
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#F8F9FA',
            'border': 1
        })
        normal_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'border': 1
        })

        # === Write Headers (example from your HTML) ===
        headers = [
            "Sr. No", "Part Number", "Part Name", "Operation ID", "Operation Name",
            "Equipment", "Shift", "Hours", "Minutes", "Seconds",
            "Volume/Month", "Volume/Day", "Volume/Shift", "Volume/Hour", "Takt Time (Sec)",
            "Cycle Time (Min)", "Cycle Time (Sec)", "Output/Hour", "Output/Shift", "Output/Day",
            "Output/Month", "Days Required", "Actual Takt Time (Sec)", "Plant Efficiency",
            "Efficiency Output/Hour", "Efficiency Output/Shift", "Efficiency Output/Day",
            "Efficiency Output/Month", "Efficiency Days Required"
        ]

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # === Write Data ===
        config = self.calculation_id.configuration_id or self.env['cycle.time.configuration'].get_default_config()
        row = 1
        for op_shift in self.calculation_id.operation_shift_ids:
            calc_data = op_shift._calculate_all_values(config)

            worksheet.write(row, 0, op_shift.s_no, normal_format)
            worksheet.write(row, 1, op_shift.calculation_id.part_number.display_name, normal_format)
            worksheet.write(row, 2, op_shift.calculation_id.part_name or '', normal_format)
            worksheet.write(row, 3, op_shift.operation_pfd_id.display_name or '', normal_format)
            worksheet.write(row, 4, op_shift.operation_name or '', normal_format)
            worksheet.write(row, 5, op_shift.equipment_id.name or '', normal_format)
            worksheet.write(row, 6, op_shift.available_shift_working or '', normal_format)

            # Write calculated values
            worksheet.write_number(row, 7, calc_data.get('shift_hours', 0), normal_format)
            worksheet.write_number(row, 8, calc_data.get('shift_minutes', 0), normal_format)
            worksheet.write_number(row, 9, calc_data.get('shift_seconds', 0), normal_format)
            worksheet.write_number(row, 10, calc_data.get('volume_per_month', 0), normal_format)
            worksheet.write_number(row, 11, calc_data.get('volume_per_day', 0), normal_format)
            worksheet.write_number(row, 12, calc_data.get('volume_per_shift', 0), normal_format)
            worksheet.write_number(row, 13, calc_data.get('volume_per_hour', 0), normal_format)
            worksheet.write_number(row, 14, calc_data.get('takt_time_seconds', 0), normal_format)
            worksheet.write_number(row, 15, calc_data.get('cycle_time_minutes', 0), normal_format)
            worksheet.write_number(row, 16, calc_data.get('cycle_time_seconds', 0), normal_format)
            worksheet.write_number(row, 17, calc_data.get('output_per_hour', 0), normal_format)
            worksheet.write_number(row, 18, calc_data.get('output_per_shift', 0), normal_format)
            worksheet.write_number(row, 19, calc_data.get('output_per_day', 0), normal_format)
            worksheet.write_number(row, 20, calc_data.get('output_per_month', 0), normal_format)
            worksheet.write_number(row, 21, calc_data.get('days_required', 0), normal_format)
            worksheet.write_number(row, 22, calc_data.get('actual_takt_time_base', 0), normal_format)
            worksheet.write_number(row, 23, calc_data.get('plant_efficiency', 0), normal_format)
            worksheet.write_number(row, 24, calc_data.get('efficiency_output_per_hour', 0), normal_format)
            worksheet.write_number(row, 25, calc_data.get('efficiency_output_per_shift', 0), normal_format)
            worksheet.write_number(row, 26, calc_data.get('efficiency_output_per_day', 0), normal_format)
            worksheet.write_number(row, 27, calc_data.get('efficiency_output_per_month', 0), normal_format)
            worksheet.write_number(row, 28, calc_data.get('efficiency_days_required', 0), normal_format)

            row += 1

        workbook.close()
        output.seek(0)

        # Save file to wizard
        self.excel_file = base64.b64encode(output.read())
        self.excel_filename = f"Calculation_Details_{self.calculation_id.part_name}.xlsx"

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/?model={self._name}&id={self.id}&field=excel_file&filename_field=excel_filename&download=true",
            'target': 'self',
        }

class CycleTimeConfiguration(models.Model):
    _name = 'cycle.time.configuration'
    _description = 'Cycle Time Calculation Configuration'
    _rec_name = 'name'

    name = fields.Char('Configuration Name', required=True, default='Default Configuration')
    active = fields.Boolean('Active', default=True)

    # Working parameters
    working_days_per_month = fields.Float('Working Days per Month', default=25.0, required=True)
    shifts_per_day = fields.Integer('Shifts per Day', default=3, required=True)
    hours_per_day = fields.Float('Hours per Day', default=24.0, required=True)
    seconds_per_day = fields.Float('Seconds per Day', default=86400.0, required=True)

    # Formula configurations
    shift_minutes_formula = fields.Text('Shift Minutes Formula',
                                        default='shift_hours * 60')

    shift_seconds_formula = fields.Text('Shift Seconds Formula',
                                        default='shift_minutes * 60',
                                        help='Formula: shift_minutes * 60')

    volume_per_day_formula = fields.Text('Volume per Day Formula',
                                         default='volume_per_month / working_days_per_month',
                                         help='Formula: volume_per_month / working_days_per_month')

    volume_per_shift_formula = fields.Text('Volume per Shift Formula',
                                           default='volume_per_day / hours_per_day',
                                           help='Formula: volume_per_day / hours_per_day')

    volume_per_hour_formula = fields.Text('Volume per Hour Formula',
                                          default='volume_per_shift / shift_hours',
                                          help='Formula: volume_per_shift / shift_hours')

    takt_time_seconds_formula = fields.Text('Takt Time (Seconds) Formula',
                                            default='seconds_per_day / volume_per_month',
                                            help='Formula: seconds_per_day / volume_per_month')

    cycle_time_seconds_formula = fields.Text('Cycle Time (Seconds) Formula',
                                             default='cycle_time_minutes * 60',
                                             help='Formula: cycle_time_minutes * 60')

    output_per_hour_formula = fields.Text('Output per Hour Formula',
                                          default='60 / cycle_time_minutes',
                                          help='Formula: 60 / cycle_time_minutes')

    output_per_shift_formula = fields.Text('Output per Shift Formula',
                                           default='output_per_hour * shift_hours',
                                           help='Formula: output_per_hour * shift_hours')

    output_per_day_formula = fields.Text('Output per Day Formula',
                                         default='output_per_shift * shifts_per_day',
                                         help='Formula: output_per_shift * shifts_per_day')

    output_per_month_formula = fields.Text('Output per Month Formula',
                                           default='output_per_day * working_days_per_month',
                                           help='Formula: output_per_day * working_days_per_month')

    days_required_formula = fields.Text('Days Required Formula',
                                        default='volume_per_month / output_per_day',
                                        help='Formula: volume_per_month / output_per_day')

    actual_takt_time_base_formula = fields.Text('Actual Takt Time Base Formula',
                                                default='seconds_per_day / output_per_month',
                                                help='Formula: seconds_per_day / output_per_month')

    actual_takt_time_seconds_eff_formula = fields.Text('Actual Takt Time (Eff) Formula',
                                                       default='((100 - plant_efficiency) / 100) * actual_takt_time_base + actual_takt_time_base',
                                                       help='Formula: ((100 - plant_efficiency) / 100) * actual_takt_time_base + actual_takt_time_base')

    actual_takt_time_seconds_formula = fields.Text('Actual Takt Time (Cycle) Formula',
                                                   default='((100 - plant_efficiency) / 100) * cycle_time_minutes + cycle_time_minutes',
                                                   help='Formula: ((100 - plant_efficiency) / 100) * cycle_time_minutes + cycle_time_minutes')

    efficiency_output_per_hour_formula = fields.Text('Efficiency Output per Hour Formula',
                                                     default='60 / actual_takt_time_seconds',
                                                     help='Formula: 60 / actual_takt_time_seconds')

    efficiency_output_per_shift_formula = fields.Text('Efficiency Output per Shift Formula',
                                                      default='efficiency_output_per_hour * 8',
                                                      help='Formula: efficiency_output_per_hour * 8')

    efficiency_output_per_day_formula = fields.Text('Efficiency Output per Day Formula',
                                                    default='efficiency_output_per_shift * shifts_per_day',
                                                    help='Formula: efficiency_output_per_shift * shifts_per_day')

    efficiency_output_per_month_formula = fields.Text('Efficiency Output per Month Formula',
                                                      default='efficiency_output_per_day * working_days_per_month',
                                                      help='Formula: efficiency_output_per_day * working_days_per_month')

    efficiency_days_required_formula = fields.Text('Efficiency Days Required Formula',
                                                   default='(volume_per_month / efficiency_output_per_month) * working_days_per_month',
                                                   help='Formula: (volume_per_month / efficiency_output_per_month) * working_days_per_month')

    @api.model
    def get_default_config(self):
        """Get the default configuration for calculations"""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            config = self.create({
                'name': 'Default Configuration',
                'active': True
            })
        return config

    def action_apply_to_all_calculations(self):
        """Apply this configuration to all existing calculations"""
        calculations = self.env['cycle.time.calculation'].search([])
        for calc in calculations:
            calc.action_calculate_all()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success!',
                'message': f'Configuration applied to {len(calculations)} calculations.',
                'type': 'success',
            }
        }