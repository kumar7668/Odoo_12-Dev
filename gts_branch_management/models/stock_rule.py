from odoo import models, fields


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    branch_id = fields.Many2one('res.branch', 'Branch')


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_custom_move_fields(self):
        fields = super(StockRule, self)._get_custom_move_fields()
        fields += ['branch_id']
        return fields

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        new_move_vals = super(StockRule, self)._push_prepare_move_copy_values(
            move_to_copy, new_date)
        new_move_vals.update({
            'branch_id': move_to_copy.branch_id.id
        })
        return new_move_vals

    def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_id,
                         name, origin, values, bom):
        new_vals = super(StockRule, self)._prepare_mo_vals(
            product_id, product_qty, product_uom, location_id, name, origin, values, bom)
        new_vals.update({
            'branch_id': values.get('branch_id', '')
        })
        return new_vals
