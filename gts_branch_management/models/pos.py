from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
import logging
_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def create(self, vals):
        res = super(PosOrder, self).create(vals)
        res.branch_id = res.session_id.branch_id.id
        return res

    branch_id = fields.Many2one('res.branch', related='config_id.branch_id', strinng='Branch')

    def _reconcile_payments(self):
        for order in self:
            aml = order.statement_ids.mapped('journal_entry_ids') | order.account_move.line_ids | order.invoice_id.move_id.line_ids
            moves = aml.mapped('move_id')
            for move in moves:
                move.write({
                    'branch_id': order.branch_id.id,
                })
            print('moves======', moves)
            for line in aml:
                line.write({
                    'branch_id': order.branch_id.id,
                })
            aml = aml.filtered(lambda r: not r.reconciled and r.account_id.internal_type == 'receivable' and r.partner_id == order.partner_id.commercial_partner_id)

            try:
                # Cash returns will be well reconciled
                # Whereas freight returns won't be
                # "c'est la vie..."
                aml.reconcile()
            except Exception:
                _logger.exception('Reconciliation did not work for order %s', order.name)

    def _force_picking_done(self, picking):
        """Force picking in order to be set as done."""
        print('picking', picking)
        picking.write({
            'branch_id': self.branch_id.id,
        })
        for line in picking.move_ids_without_package:
            line.write({
                'branch_id': self.branch_id.id,
            })
        self.ensure_one()
        picking.action_assign()
        wrong_lots = self.set_pack_operation_lot(picking)
        if not wrong_lots:
            picking.action_done()


class PosSession(models.Model):
    _inherit = 'pos.session'

    # @api.model
    # def create(self, vals):
    #     res = super(PosSession, self).create(vals)
    #     res.branch_id = res.config_id.branch_id.id
    #     return res

    branch_id = fields.Many2one('res.branch', related='config_id.branch_id', string='Branch')


class PosConfig(models.Model):
    _inherit = 'pos.config'

    branch_id = fields.Many2one('res.branch', 'Branch')
    stock_location_id = fields.Many2one('stock.location', 'Stock Location')

    # @api.multi
    @api.constrains('branch_id', 'stock_location_id')
    def _check_branch_constrains(self):
        if self.branch_id and self.stock_location_id:
            if self.branch_id.id != self.stock_location_id.branch_id.id:
                raise UserError(_(
                    'Configuration error\n You must select same branch on a location \
                    as assigned on a point of sale configuration.'
                ))
