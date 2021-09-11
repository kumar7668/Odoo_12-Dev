from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    branch_id = fields.Many2one('res.branch', 'Branch')


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _get_default_branch(self):
        User = self.env['res.users']
        return User.browse(self.env.uid).branch_id.id or False

    branch_id = fields.Many2one('res.branch', 'Branch', default=_get_default_branch)

    @api.model
    def create(self, vals):
        res = super(AccountMove, self).create(vals)
        if res.stock_move_id:
            res.branch_id = res.stock_move_id.branch_id
        if res.line_ids:
            for a in res.line_ids:
                a.branch_id = res.branch_id
        return res


# class AccountmoveLine(models.Model):
#     _inherit = 'account.move.line'
#
#     @api.model
#     def _get_default_branch(self):
#         User = self.env['res.users']
#         return User.browse(self.env.uid).branch_id.id or False
#
#     branch_id = fields.Many2one('res.branch', 'Branch', default=_get_default_branch)


# class AccountInvoice(models.Model):
#     _inherit = 'account.invoice'
#
#     @api.onchange('branch_id')
#     def onchange_branch_id(self):
#         if self.branch_id:
#             if self.branch_id.term_conditions1:
#                 self.comment = self.branch_id.term_conditions1
#
#     # @api.multi
#     def action_move_create(self):
#         """ Creates invoice related analytics and financial move lines """
#         account_move = self.env['account.move']
#
#         for inv in self:
#             if not inv.journal_id.sequence_id:
#                 raise UserError(_('Please define sequence on the journal related to this invoice.'))
#             if not inv.invoice_line_ids.filtered(lambda line: line.account_id):
#                 raise UserError(_('Please add at least one invoice line.'))
#             if inv.move_id:
#                 continue
#
#             if not inv.date_invoice:
#                 inv.write({'date_invoice': fields.Date.context_today(self)})
#             if not inv.date_due:
#                 inv.write({'date_due': inv.date_invoice})
#             company_currency = inv.company_id.currency_id
#
#             # create move lines (one per invoice line + eventual taxes and analytic lines)
#             iml = inv.invoice_line_move_line_get()
#             iml += inv.tax_line_move_line_get()
#
#             diff_currency = inv.currency_id != company_currency
#             # create one move line for the total and possibly adjust the other lines amount
#             total, total_currency, iml = inv.compute_invoice_totals(company_currency, iml)
#
#             name = inv.name or ''
#             if inv.payment_term_id:
#                 totlines = \
#                 inv.payment_term_id.with_context(currency_id=company_currency.id).compute(total, inv.date_invoice)[0]
#                 res_amount_currency = total_currency
#                 for i, t in enumerate(totlines):
#                     if inv.currency_id != company_currency:
#                         amount_currency = company_currency._convert(t[1], inv.currency_id, inv.company_id,
#                                                                     inv._get_currency_rate_date() or fields.Date.today())
#                     else:
#                         amount_currency = False
#
#                     # last line: add the diff
#                     res_amount_currency -= amount_currency or 0
#                     if i + 1 == len(totlines):
#                         amount_currency += res_amount_currency
#
#                     iml.append({
#                         'type': 'dest',
#                         'name': name,
#                         'price': t[1],
#                         'account_id': inv.account_id.id,
#                         'date_maturity': t[0],
#                         'amount_currency': diff_currency and amount_currency,
#                         'currency_id': diff_currency and inv.currency_id.id,
#                         'invoice_id': inv.id,
#                         'branch_id': inv.branch_id.id,
#                     })
#             else:
#                 iml.append({
#                     'type': 'dest',
#                     'name': name,
#                     'price': total,
#                     'account_id': inv.account_id.id,
#                     'date_maturity': inv.date_due,
#                     'amount_currency': diff_currency and total_currency,
#                     'currency_id': diff_currency and inv.currency_id.id,
#                     'invoice_id': inv.id,
#                     'branch_id': inv.branch_id.id,
#                 })
#             part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
#             line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
#             line = inv.group_lines(iml, line)
#
#             line = inv.finalize_invoice_move_lines(line)
#
#             date = inv.date or inv.date_invoice
#             move_vals = {
#                 'ref': inv.reference,
#                 'line_ids': line,
#                 'journal_id': inv.journal_id.id,
#                 'date': date,
#                 'narration': inv.comment,
#                 'branch_id': inv.branch_id.id,
#             }
#             move = account_move.create(move_vals)
#             for line in move.line_ids:
#                  if inv.branch_id.id:
#                     line.branch_id = inv.branch_id.id
#             # Pass invoice in method post: used if you want to get the same
#             # account move reference when creating the same invoice after a cancelled one:
#             move.post(invoice=inv)
#             # make the invoice point to that move
#             vals = {
#                 'move_id': move.id,
#                 'date': date,
#                 'move_name': move.name,
#             }
#             inv.write(vals)
#         return True
#
#     # @api.multi
#     def action_invoice_open(self):
#         res = super(AccountInvoice, self).action_invoice_open()
#         # to write branch of account invoice in account invoice line
#         for inv in self:
#             if inv.branch_id:
#                 for line in inv.invoice_line_ids:
#                     line.branch_id = inv.branch_id.id
#         return res
