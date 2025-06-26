from odoo import models, fields, api


class ManpowerTracking(models.Model):
    _name = 'manpower.tracking'
    _description = 'Manpower and Resource Tracking'
    _inherit = "translation.mixin"

    name = fields.Char(string='Reference', required=True, default='New',readonly=True,translate=True)
    date = fields.Date(string='Date', default=fields.Date.today)

    # Manpower Fields
    total_employees = fields.Integer(string='Total Employees' , compute='_compute_total_employees', store=True)
    white_collar = fields.Integer(string='White Collar Employees')
    blue_collar = fields.Integer(string='Blue Collar Employees')
    contract_based = fields.Integer(string='Contract-Based Employees')

    # Equipment Costs
    equipment_cost = fields.Float(string='Equipment/Fixture  Cost')
    gauge_cost = fields.Float(string='Gauge Cost')
    tool_cost = fields.Float(string='ToolCost')
    total_equipment_cost = fields.Float(string='Total Equipment Cost', compute='_compute_total_equipment_cost', store=True)

    # Quality and Safety Incidents
    quality_incident_cost = fields.Float(string='Quality Incident Cost')
    safety_incident_cost = fields.Float(string='Safety Incident Cost')
    total_incident_cost = fields.Float(string='Total Incident Cost', compute='_compute_total_incident_cost', store=True)

    # Carbon Footprint
    carbon_footprint = fields.Float(string='Carbon Footprint (kg CO2e)')

    @api.depends('white_collar', 'blue_collar', 'contract_based')
    def _compute_total_employees(self):
        for record in self:
            record.total_employees = record.white_collar + record.blue_collar + record.contract_based


    @api.depends('equipment_cost', 'gauge_cost', 'tool_cost')
    def _compute_total_equipment_cost(self):
        for record in self:
            record.total_equipment_cost = record.equipment_cost + record.gauge_cost + record.tool_cost

    @api.depends('quality_incident_cost', 'safety_incident_cost')
    def _compute_total_incident_cost(self):
        for record in self:
            record.total_incident_cost = record.quality_incident_cost + record.safety_incident_cost

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('manpower.tracking') or 'New'
        return super(ManpowerTracking, self).create(vals)