from odoo import api, fields, models
from odoo.tools import float_compare
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _get_default_branch(self):
        User = self.env['res.users']
        return User.browse(self.env.uid).branch_id.id or False

    branch_id = fields.Many2one('res.branch', 'Branch', required=True,
                                default=_get_default_branch)

    @api.onchange('branch_id')
    def onchange_branch_id(self):
        if self.branch_id:
            if self.branch_id.term_conditions:
                self.note = self.branch_id.term_conditions
            if self.branch_id.gst_no:
                self.df_gst_number = self.branch_id.gst_no
            wh = self.env['stock.warehouse'].search([('branch_id', '=',self.branch_id.id)])
            if wh:
                self.warehouse_id = wh[0]
            else:
                self.warehouse_id = False

    # @api.multi
    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        res.update({
            'branch_id': self.branch_id.id
        })
        return res


class StockPicking(models.Model):
    _inherit='stock.picking'

    branch_id = fields.Many2one('res.branch', 'Branch')


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # @api.multi
    def _prepare_procurement_values(self, group_id=False):
        values = super(SaleOrderLine, self)._prepare_procurement_values(group_id=group_id)
        values.update({
            'branch_id': self.order_id.branch_id.id,
        })
        return values


    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        """
        Launch procurement group run method with required/custom fields genrated by a
        sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
        depending on the sale order line product rule.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        procurements = []
        for line in self:
            line = line.with_company(line.company_id)
            if line.state != 'sale' or not line.product_id.type in ('consu','product'):
                continue
            qty = line._get_qty_procurement(previous_product_uom_qty)
            if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
                continue

            group_id = line._get_procurement_group()
            if not group_id:
                group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
                line.order_id.procurement_group_id = group_id
            else:
                # In case the procurement group is already created and the order was
                # cancelled, we need to update certain values of the group.
                updated_vals = {}
                if group_id.partner_id != line.order_id.partner_shipping_id:
                    updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
                if group_id.move_type != line.order_id.picking_policy:
                    updated_vals.update({'move_type': line.order_id.picking_policy})
                if updated_vals:
                    group_id.write(updated_vals)

            values = line._prepare_procurement_values(group_id=group_id)
            values.update({'branch_id': line.order_id.branch_id.id})
            product_qty = line.product_uom_qty - qty

            line_uom = line.product_uom
            quant_uom = line.product_id.uom_id
            product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
            procurements.append(self.env['procurement.group'].Procurement(
                line.product_id, product_qty, procurement_uom,
                line.order_id.partner_shipping_id.property_stock_customer,
                line.name, line.order_id.name, line.order_id.company_id, values))
        if procurements:
            self.env['procurement.group'].run(procurements)
        return True

    # @api.multi
    # def _action_launch_stock_rule(self, previous_product_uom_qty=False):
    #     """
    #     Launch procurement group run method with required/custom fields genrated by a
    #     sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
    #     depending on the sale order line product rule.
    #     """
    #     precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
    #     errors = []
    #     for line in self:
    #         if line.state != 'sale' or not line.product_id.type in ('consu', 'product'):
    #             continue
    #         qty = line._get_qty_procurement()
    #         if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
    #             continue
    #
    #         group_id = line.order_id.procurement_group_id
    #         if not group_id:
    #             group_id = self.env['procurement.group'].create({
    #                 'name': line.order_id.name, 'move_type': line.order_id.picking_policy,
    #                 'sale_id': line.order_id.id,
    #                 'partner_id': line.order_id.partner_shipping_id.id,
    #             })
    #             line.order_id.procurement_group_id = group_id
    #         else:
    #             # In case the procurement group is already created and the order was
    #             # cancelled, we need to update certain values of the group.
    #             updated_vals = {}
    #             if group_id.partner_id != line.order_id.partner_shipping_id:
    #                 updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
    #             if group_id.move_type != line.order_id.picking_policy:
    #                 updated_vals.update({'move_type': line.order_id.picking_policy})
    #             if updated_vals:
    #                 group_id.write(updated_vals)
    #
    #         values = line._prepare_procurement_values(group_id=group_id)
    #         values.update({'branch_id': line.order_id.branch_id.id})
    #         product_qty = line.product_uom_qty - qty
    #
    #         procurement_uom = line.product_uom
    #         quant_uom = line.product_id.uom_id
    #         get_param = self.env['ir.config_parameter'].sudo().get_param
    #         if procurement_uom.id != quant_uom.id and get_param('stock.propagate_uom') != '1':
    #             product_qty = line.product_uom._compute_quantity(product_qty, quant_uom, rounding_method='HALF-UP')
    #             procurement_uom = quant_uom
    #
    #         try:
    #             self.env['procurement.group'].run(line.product_id, product_qty, procurement_uom,
    #                                               line.order_id.partner_shipping_id.property_stock_customer, line.name,
    #                                               line.order_id.name, values)
    #         except UserError as error:
    #             errors.append(error.name)
    #     if errors:
    #         raise UserError('\n'.join(errors))
    #     #if self.sudo().env['ir.module.module'].search(
    #     #        [('name', '=', 'procurement_jit')], limit=1).state in (
    #     #        'installed', 'to install', 'to upgrade'):
    #     #    orders = list(set(x.order_id for x in self))
    #     #    for order in orders:
    #     #        reassign = order.picking_ids.filtered(
    #     #            lambda x: x.state == 'confirmed' or (x.state in ['waiting', 'assigned'] \
    #     #                                                 and not x.printed))
    #     #        if reassign:
    #     #            reassign.do_unreserve()
    #     #        reassign.action_assign()
    #     return True
