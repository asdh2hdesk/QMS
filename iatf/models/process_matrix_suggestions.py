from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProcessSuggestion(models.Model):
    _name = 'process.suggestion'
    _description = 'Process Suggestion'
    _inherit = "translation.mixin"

    name = fields.Char('Name', required=True,translate=True)
    category_id = fields.Many2one('presentation.category', string='Process Category', required=True)
    process_type = fields.Selection([
        ('machine', 'Machine'),
        ('assembly', 'Assembly'),
        ('machine_and_assembly', 'Machine and Assembly')
    ], string="Process Type", required=True)

    # Suggestions for operation lines
    operation_line_ids = fields.One2many('process.suggestion.operation', 'suggestion_id', string='Operations')

    _sql_constraints = [
        ('unique_category_type', 'unique(category_id, process_type)',
         'A suggestion for this category and process type already exists!')
    ]


class ProcessSuggestionOperation(models.Model):
    _name = 'process.suggestion.operation'
    _description = 'Process Suggestion Operation'
    _order = 'sequence'
    _inherit = "translation.mixin"

    suggestion_id = fields.Many2one('process.suggestion', string='Suggestion', required=True, ondelete='cascade')
    sequence = fields.Integer('Sequence', default=10)
    operation = fields.Char("Operation", required=True)
    operation_description = fields.Char(string="Operation Description",translate=True)

    # Elements for this operation
    element_line_ids = fields.One2many('process.suggestion.element', 'operation_id', string='Elements')


class ProcessSuggestionElement(models.Model):
    _name = 'process.suggestion.element'
    _description = 'Process Suggestion Element'
    _order = 'sequence'
    _inherit = "translation.mixin"

    operation_id = fields.Many2one('process.suggestion.operation', string='Operation', required=True,
                                   ondelete='cascade')
    sequence = fields.Integer('Sequence', default=1)
    element_description = fields.Char(string="Element Description",translate=True)
    cycle_time = fields.Integer("Cycle Time (sec)")
    boq=fields.Many2one("mrp.bom.line",string="BOM-Item")
    rev_no = fields.Char("Revision No.")
    l_mm = fields.Char("L-mm")
    w_mm = fields.Char("W/OD-mm")
    t_mm = fields.Char("T-mm")
    component_weight = fields.Char("Component Weight - kg")
    manpower = fields.Char("manpower")
    op=fields.Char(related="operation_id.operation",string="Operation",store=True)
    pokayoke_ids = fields.Many2many('poka.yoka.line', string="Pokayoke", domain="[('operation', '=', op)]")
    product_kpc_id = fields.Many2one('product.characteristics', 'Product Characteristics')
    process_kcc_id = fields.Many2one('process.characteristics', 'Process Characteristics')
    special_characteristics = fields.Many2one('process.flow.class', 'Class')
    Child_part = fields.Char(string="Child Part in",translate=True)
    equipment_fixture_ids = fields.Many2many(
        'maintenance.equipment',
        'op_sg_element_equipment_rel',  # Unique relation table name
        'operation_id',  # First column
        'equipment_id',  # Second column
        string="Equipment & Fixture",
        domain="[('category_id', 'in', ['Equipment', 'Fixture'])]")
    tool_ids = fields.Many2many(
        'maintenance.equipment',
        'op_sg_element_tool_rel',  # Unique relation table name
        'operation_id',
        'tool_id',
        string="Tools",
        domain="[('category_id', 'in', ['Tool'])]"
    )
    traceability_system_ids = fields.Many2many('presentation.traceability.system',
                                               'op_sg_element_traceability_system_rel','element_id','traceability_id',string="Traceability System")

    Child_sub = fields.Char(string="Child Part / Sub Assy Out",translate=True)
    crane = fields.Char("Crane",translate=True)
    customize = fields.Char("Customize MHE ",translate=True)
    utility = fields.Char("Utility",translate=True)
    miscl = fields.Char("Miscl. Item",translate=True)
    remarks = fields.Char("Remarks",translate=True)
    remarks = fields.Char("Remarks",translate=True)


class ProcessGroup(models.Model):
    _inherit = 'process.group'

    @api.onchange('process_matrix_category', 'process_type')
    def _onchange_process_category_type(self):
        """When category or type changes, suggest operations based on template if available"""
        if self.process_matrix_category and self.process_type:
            suggestion = self.env['process.suggestion'].search([
                ('category_id', '=', self.process_matrix_category.id),
                ('process_type', '=', self.process_type)
            ], limit=1)

            if suggestion:
                # Clear existing operations first
                if self.process_presentation_ids:
                    # Return a warning if there's already data
                    return {
                        'warning': {
                            'title': 'Existing Operations',
                            'message': 'Loading suggestion data will replace existing operations. '
                                       'Confirm by clicking Apply Suggestion button.'
                        }
                    }

    def action_apply_suggestion(self):
        """Apply suggestions from template based on category and process type"""
        self.ensure_one()
        if not self.process_matrix_category or not self.process_type:
            raise ValidationError("Please select both Process Category and Process Type")

        suggestion = self.env['process.suggestion'].search([
            ('category_id', '=', self.process_matrix_category.id),
            ('process_type', '=', self.process_type)
        ], limit=1)

        if not suggestion:
            raise ValidationError("No suggestion template found for this combination")

        # Clear existing operations
        self.process_presentation_ids.unlink()

        # Create new operations from suggestion
        for sugg_op in suggestion.operation_line_ids:
            operation_vals = {
                'process_id': self.id,
                'operation': sugg_op.operation,
                'operation_description': sugg_op.operation_description,
                'sq_handle': sugg_op.sequence // 10,  # Convert to appropriate sequence
                'operation_lines_ids': []
            }

            # Add elements
            for element in sugg_op.element_line_ids:
                element_vals = {
                    'sequence_handle': element.sequence,
                    'element_description': element.element_description,
                    'cycle_time': element.cycle_time,
                    'boq' : element.boq.id if element.boq else False,
                    'rev_no': element.rev_no,
                    'l_mm': element.l_mm,
                    'w_mm': element.w_mm,
                    't_mm': element.t_mm,
                    'component_weight': element.component_weight,
                    'manpower': element.manpower,
                    'special_characteristics': element.special_characteristics.id if element.special_characteristics else False,
                    'Child_part': element.Child_part,
                    'Child_sub': element.Child_sub,
                    'crane': element.crane,
                    'customize': element.customize,
                    'utility': element.utility,
                    'miscl': element.miscl,
                    'equipment_fixture_ids': [(6, 0, element.equipment_fixture_ids.ids)],
                    'tool_ids': [(6, 0, element.tool_ids.ids)],
                    'traceability_system_ids': [(6, 0, element.traceability_system_ids.ids)],
                    'pokayoke_ids': [(6, 0, element.pokayoke_ids.ids)],
                    'product_kpc': element.product_kpc_id.id if element.product_kpc_id else False,
                    'process_kcc': element.process_kcc_id.id if element.process_kcc_id else False,
                    'remarks': element.remarks,
                }
                operation_vals['operation_lines_ids'].append((0, 0, element_vals))

            # Create the operation with all its elements
            self.env['process.matrix.operation'].create(operation_vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_save_as_suggestion(self):
        """Save current process matrix as a suggestion template"""
        self.ensure_one()
        if not self.process_matrix_category or not self.process_type:
            raise ValidationError("Please select both Process Category and Process Type")

        # Check if a suggestion already exists
        existing = self.env['process.suggestion'].search([
            ('category_id', '=', self.process_matrix_category.id),
            ('process_type', '=', self.process_type)
        ], limit=1)

        if existing:
            # Clear existing operations and elements
            existing.operation_line_ids.mapped('element_line_ids').unlink()
            existing.operation_line_ids.unlink()
            suggestion = existing
        else:
            # Create new suggestion
            suggestion = self.env['process.suggestion'].create({
                'name': f"{self.process_matrix_category.name} - {dict(self._fields['process_type'].selection).get(self.process_type)}",
                'category_id': self.process_matrix_category.id,
                'process_type': self.process_type,
            })

        # Add operations and elements
        for operation in self.process_presentation_ids:
            op_vals = {
                'suggestion_id': suggestion.id,
                'sequence': int(operation.operation) if operation.operation and operation.operation.isdigit() else 10,
                'operation': operation.operation,
                'operation_description': operation.operation_description,
            }

            op = self.env['process.suggestion.operation'].create(op_vals)

            # Add elements for this operation
            for element in operation.operation_lines_ids:
                self.env['process.suggestion.element'].create({
                    'operation_id': op.id,
                    'sequence': element.sequence_handle,
                    'element_description': element.element_description,
                    'cycle_time': element.cycle_time,
                    'boq': element.boq.id if element.boq else False,
                    'rev_no': element.rev_no,
                    'l_mm': element.l_mm,
                    'w_mm': element.w_mm,
                    't_mm': element.t_mm,
                    'component_weight': element.component_weight,
                    'manpower': element.manpower,
                    'special_characteristics': element.special_characteristics.id if element.special_characteristics else False,
                    'Child_part': element.Child_part,
                    'Child_sub': element.Child_sub,
                    'crane': element.crane,
                    'customize': element.customize,
                    'utility': element.utility,
                    'miscl': element.miscl,
                    'equipment_fixture_ids': [(6, 0, element.equipment_fixture_ids.ids)],
                    'tool_ids': [(6, 0, element.tool_ids.ids)],
                    'traceability_system_ids': [(6, 0, element.traceability_system_ids.ids)],
                    'pokayoke_ids': [(6, 0, element.pokayoke_ids.ids)],
                    'product_kpc_id': element.product_kpc.id if element.product_kpc else False,
                    'process_kcc_id': element.process_kcc.id if element.process_kcc else False,
                    'remarks': element.remarks,
                })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Process matrix saved as suggestion template',
                'type': 'success',
                'sticky': False,
            }
        }