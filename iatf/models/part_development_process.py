# -*- coding: utf-8 -*-
from datetime import date, datetime
from odoo import api, fields, models


class PartDevelopmentProcess(models.Model):
    _name = 'part.development.process'
    _description = 'Part Development Process'
    _rec_name = "part_no"
    _inherit = "translation.mixin"

    part_no = fields.Integer("Part No")
    part_name = fields.Char("Part Name",translate=True)
    customer_part_no = fields.Integer("Customer Part No")
    customer_part_name = fields.Many2one("res.partner", string="Customer Name")
    origin_date = fields.Datetime("Date")
    revesion_date = fields.Datetime("Revesion Date")

# ======================================================================================================
    # Marketing Part
# ======================================================================================================

    is_marketing = fields.Boolean("Is Marketing?", compute='_compute_is_marketing', store=True)
    risk_assessment_id = fields.Many2one('risk.assessment')
    feasibility_commitment_id = fields.Many2one('feasibility.commitment')
    is_risk = fields.Boolean("Is Risk Done?", compute="_compute_is_risk_done", store=True)
    is_feasibility = fields.Boolean("Is Feasibility?", compute="_compute_is_feasibility", store=True)

    # @api.depends('risk_assessment_id.state', 'feasibility_commitment_id.state')
    # def _compute_is_marketing(self):
    #     for record in self:
    #         if record.risk_assessment_id.state == 'final_approved' and record.feasibility_commitment_id.state == 'final_approved':
    #             record.is_marketing = True
    #         else:
    #             record.is_marketing = False
    #
    # # For Risk Assessment
    # @api.depends('risk_assessment_id.state')
    # def _compute_is_risk_done(self):
    #     for record in self:
    #         if record.risk_assessment_id.state == 'final_approved':
    #             record.is_risk = True
    #         else:
    #             record.is_risk = False
    #
    # def action_open_risk_assessment(self):
    #     existing_risk_assessment = self.env['risk.assessment'].search([
    #         ('part_development_id', '=', self.id)
    #     ], limit=1)
    #
    #     if existing_risk_assessment:
    #         action = {
    #             'name': existing_risk_assessment.format_id,
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'risk.assessment',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'res_id': existing_risk_assessment.id,
    #         }
    #     else:
    #         action = {
    #             'name': 'New Risk Assessment',
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'risk.assessment',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'context': {
    #                 'default_part_development_id': self.id,
    #             },
    #         }
    #     return action
    #
    # # For Team Feasibility
    # @api.depends('feasibility_commitment_id.state')
    # def _compute_is_feasibility(self):
    #     for record in self:
    #         if record.feasibility_commitment_id.state == 'final_approved':
    #             record.is_feasibility = True
    #         else:
    #             record.is_feasibility = False

    # def action_open_feasibility_commitment(self):
    #     existing_feasibility_commitment = self.env['feasibility.commitment'].search([
    #         ('part_development_id', '=', self.id)
    #     ], limit=1)
    #     if existing_feasibility_commitment:
    #         action = {
    #             'name': existing_feasibility_commitment.id,
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'feasibility.commitment',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'res_id': existing_feasibility_commitment.id,
    #         }
    #     else:
    #         action = {
    #             'name': 'New Feasibility Commitment',
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'feasibility.commitment',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'context': {
    #                 'default_part_development_id': self.id,
    #             },
    #         }
    #     return action

# ======================================================================================================
    # Engineering Part
# ======================================================================================================

    is_engineering = fields.Boolean("Is Engineering?")
    cft_id = fields.Many2one('cft.team')
    part_creation_id = fields.Many2one('customer.part.creation')
    quart_id = fields.Many2one('quary.list')
    things_right_wrong_id = fields.Many2one('things.wrong.right')
    process_flow_id = fields.Many2one('process.flow')
    pfmea_id = fields.Many2one('pfmea')
    is_cft = fields.Boolean("Is CFT Done?", compute="_compute_is_cft_done")
    is_part_creation = fields.Boolean("Is Part Creation Done?", compute="_compute_is_part_creation")
    is_quary_list = fields.Boolean("Is Quary List Done?", compute="_compute_is_quary_list")
    is_things = fields.Boolean("Is Things?", compute="_compute_is_things")
    is_pfd = fields.Boolean("Is PFD?", compute="_compute_is_pfd")
    is_pfmea = fields.Boolean("Is PFMEA?", compute="_compute_is_pfmea")

    # @api.depends('cft_id.state')
    # def _compute_is_cft_done(self):
    #     for record in self:
    #         if record.cft_id.state == 'final_approved':
    #             record.is_cft = True
    #         else:
    #             record.is_cft = False

    # def action_cft_team(self):
    #     existing_cft = self.env['cft.team'].search([
    #         ('part_development_id', '=', self.id)
    #     ], limit=1)
    #
    #     if existing_cft:
    #         action = {
    #             'name': existing_cft,
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'cft.team',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'res_id': existing_cft.id,
    #         }
    #     else:
    #         action = {
    #             'name': 'New CFT',
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'cft.team',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'context': {
    #                 'default_part_development_id': self.id,
    #             },
    #         }
    #     return action
    #
    # @api.depends('part_creation_id.state')
    # def _compute_is_part_creation(self):
    #     for record in self:
    #         if record.part_creation_id.state == 'final_approved':
    #             record.is_part_creation = True
    #         else:
    #             record.is_part_creation = False
    #
    # def action_part_creation(self):
    #     existing_part = self.env['customer.part.creation'].search([
    #         ('part_development_id', '=', self.id)
    #     ], limit=1)
    #
    #     if existing_part:
    #         action = {
    #             'name': existing_part,
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'customer.part.creation',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'res_id': existing_part.id,
    #         }
    #     else:
    #         action = {
    #             'name': 'New Part Creation',
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'customer.part.creation',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'context': {
    #                 'default_part_development_id': self.id,
    #             },
    #         }
    #     return action
    #
    # # @api.depends('quart_id.state')
    # # def _compute_is_quary_list(self):
    # #     for record in self:
    # #         if record.quart_id.state == 'final_approved':
    # #             record.is_quary_list = True
    # #         else:
    # #             record.is_quary_list = False
    #
    # def action_query_list(self):
    #     existing_quary = self.env['quary.list'].search([
    #         ('part_development_id', '=', self.id)
    #     ], limit=1)
    #
    #     if existing_quary:
    #         action = {
    #             'name': existing_quary,
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'quary.list',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'res_id': existing_quary.id,
    #         }
    #     else:
    #         action = {
    #             'name': 'New Quary List',
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'quary.list',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'context': {
    #                 'default_part_development_id': self.id,
    #             },
    #         }
    #     return action
    #
    # @api.depends('process_flow_id.state')
    # def _compute_is_pfd(self):
    #     for record in self:
    #         if record.process_flow_id.state == 'final_approved':
    #             record.is_pfd = True
    #         else:
    #             record.is_pfd = False
    #
    # def action_pfd(self):
    #     existing_pfd = self.env['process.flow'].search([
    #         ('part_development_id', '=', self.id)
    #     ], limit=1)
    #
    #     if existing_pfd:
    #         action = {
    #             'name': existing_pfd,
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'process.flow',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'res_id': existing_pfd.id,
    #         }
    #     else:
    #         action = {
    #             'name': 'New PFD',
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'process.flow',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'context': {
    #                 'default_part_development_id': self.id,
    #             },
    #         }
    #     return action
    #
    # def action_apqp(self):
    #     existing_quary = self.env['aqp.name'].search([
    #         ('part_development_id', '=', self.id)
    #     ], limit=1)
    #
    #     if existing_quary:
    #         action = {
    #             'name': existing_quary,
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'aqp.name',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'res_id': existing_quary.id,
    #         }
    #     else:
    #         action = {
    #             'name': 'New Quary List',
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'aqp.name',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'context': {
    #                 'default_part_development_id': self.id,
    #             },
    #         }
    #     return action
    #
    # @api.depends('things_right_wrong_id.state')
    # def _compute_is_things(self):
    #     for record in self:
    #         if record.things_right_wrong_id.state == 'final_approved':
    #             record.is_things = True
    #         else:
    #             record.is_things = False
    #
    # def action_things(self):
    #     existing_things = self.env['things.wrong.right'].search([
    #         ('part_development_id', '=', self.id)
    #     ], limit=1)
    #
    #     if existing_things:
    #         action = {
    #             'name': existing_things,
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'things.wrong.right',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'res_id': existing_things.id,
    #         }
    #     else:
    #         action = {
    #             'name': 'Things Gone Right/Wrong',
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'things.wrong.right',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'context': {
    #                 'default_part_development_id': self.id,
    #             },
    #         }
    #     return action
    #
    # @api.depends('pfmea_id.state')
    # def _compute_is_pfmea(self):
    #     for record in self:
    #         if record.pfmea_id.state == 'final_approved':
    #             record.is_pfmea = True
    #         else:
    #             record.is_pfmea = False
    #
    # def action_pfmea(self):
    #     existing_pfmea = self.env['pfmea'].search([
    #         ('part_development_id', '=', self.id)
    #     ], limit=1)
    #
    #     if existing_pfmea:
    #         action = {
    #             'name': existing_pfmea,
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'pfmea',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'res_id': existing_pfmea.id,
    #         }
    #     else:
    #         action = {
    #             'name': 'PFMEA',
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'pfmea',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'context': {
    #                 'default_part_development_id': self.id,
    #             },
    #         }
    #     return action
    #
    # def action_control_plan(self):
    #     pass
    #
    # def action_tool_requirment_sheet(self):
    #     pass
    #
    # def action_fixture_requirement_sheet(self):
    #     pass
    #
    # def action_poke_yoke_list(self):
    #     pass
    #
    # def action_customer_specific_request_form(self):
    #     existing_pfmea = self.env['customer.specification'].search([
    #         ('part_development_id', '=', self.id)
    #     ], limit=1)
    #
    #     if existing_pfmea:
    #         action = {
    #             'name': existing_pfmea,
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'customer.specification',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'res_id': existing_pfmea.id,
    #         }
    #     else:
    #         action = {
    #             'name': 'PFMEA',
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'customer.specification',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'context': {
    #                 'default_part_development_id': self.id,
    #             },
    #         }
    #     return action

    def action_tool_design(self):
        pass

    def action_fixture_design(self):
        pass

    def action_key_characteristic_sheet(self):
        pass

    def action_customer_specific_requirment(self):
        pass

    def action_symbol_conversion(self):
        pass

    def action_material_handling(self):
        pass

    def action_pqps(self):
        pass

    def action_lptp(self):
        pass

    def action_acmah(self):
        pass

    def action_acmdmr(self):
        pass

    def action_rmacr(self):
        pass

    def action_wi(self):
        pass

    def action_tgwr(self):
        pass


# ======================================================================================================
    # Production Part
# ======================================================================================================

    is_production = fields.Boolean("Is Production?")

    def action_sop(self):
        pass

    def action_wit(self):
        pass

    def action_pct(self):
        pass

    def action_ptt(self):
        pass

    def action_ms(self):
        pass

    def action_tpm(self):
        pass

    def action_oee(self):
        pass

    def action_ppcp(self):
        pass

# ======================================================================================================
    # Quality Part
# ======================================================================================================

    is_quality = fields.Boolean("Is Quality?")

    def action_msa(self):
        pass

    def action_cpcsk(self):
        pass

    def action_rr(self):
        pass

    def action_ir(self):
        pass

    def action_ca(self):
        pass

    def action_cr(self):
        pass


# ======================================================================================================
    # Purchase Part
# ======================================================================================================

    is_purchase = fields.Boolean("Is Purchase?")

    def action_indent(self):
        pass

    def action_po(self):
        pass

    def action_pcs(self):
        pass

    def action_psaso(self):
        pass

    def action_top(self):
        pass

    def action_pvr(self):
        pass

# ======================================================================================================
    # Maintanence Part
# ======================================================================================================

    def action_machine_condition(self):
        pass

    def action_pm_sheet(self):
        pass

    def action_pd_sheet(self):
        pass
