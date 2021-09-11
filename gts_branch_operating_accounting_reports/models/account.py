from odoo import api, fields, models, _


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.onchange('currency_id')
    def _onchange_currency(self):
        for line in self:
            if line.move_id:
                company = line.move_id.company_id

                if line.move_id.is_invoice(include_receipts=True):
                    line._onchange_price_subtotal()
                elif not line.move_id.reversed_entry_id:
                    balance = line.currency_id._convert(line.amount_currency, company.currency_id, company,
                                                        line.move_id.date or fields.Date.context_today(line))
                    line.debit = balance if balance > 0.0 else 0.0
                    line.credit = -balance if balance < 0.0 else 0.0

    @api.onchange('amount_currency')
    def _onchange_amount_currency(self):
        for line in self:
            if line.move_id:
                company = line.move_id.company_id
                balance = line.currency_id._convert(line.amount_currency, company.currency_id, company, line.move_id.date)
                line.debit = balance if balance > 0.0 else 0.0
                line.credit = -balance if balance < 0.0 else 0.0

                if not line.move_id.is_invoice(include_receipts=True):
                    continue

                line.update(line._get_fields_onchange_balance())
                line.update(line._get_price_total_and_subtotal())
