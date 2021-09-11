from odoo import models, api, fields
from odoo.tools import safe_eval
from odoo.tools.translate import _
from odoo.exceptions import UserError, RedirectWarning
import re
from collections import defaultdict
from itertools import chain


class generic_tax_report(models.AbstractModel):
    _inherit = 'account.generic.tax.report'

    filter_branch = True
    filter_operating_unit = True

    def _compute_from_amls_taxes(self, options, dict_to_fill, period_number):
        """Fill dict_to_fill with the data needed to generate the report.

        Used when the report is set to group its line by tax.
        """
        group_by_account = options.get('group_by')

        branch = [a.get('id') for a in options.get('branch') if a.get('selected', False)]
        if not branch:
            branch = [a.get('id') for a in options.get('branch')]
        operating_unit = [a.get('id') for a in options.get('operating_unit') if a.get('selected', False)]
        if not operating_unit:
            operating_unit = [a.get('id') for a in options.get('operating_unit')]

        sql = self._sql_cash_based_taxes(group_by_account)
        tables, where_clause, where_params = self._query_get(options, domain=[
            ('branch_id', 'in', branch),
            ('operating_unit_id', 'in', operating_unit),
        ])
        query = sql.format(tables=tables, where_clause=where_clause)
        self.env.cr.execute(query, where_params + where_params)
        for tax_id, account_id, tax, net in self.env.cr.fetchall():
            if tax_id in dict_to_fill:
                dict_to_fill[tax_id][account_id]['periods'][period_number]['net'] = net
                dict_to_fill[tax_id][account_id]['periods'][period_number]['tax'] = tax
                dict_to_fill[tax_id][account_id]['show'] = True

        # Tax base amount.
        sql = self._sql_net_amt_regular_taxes(group_by_account)
        query = sql.format(tables=tables, where_clause=where_clause)
        self.env.cr.execute(query, where_params + where_params)
        for tax_id, account_id, balance in self.env.cr.fetchall():
            if tax_id in dict_to_fill:
                dict_to_fill[tax_id][account_id]['periods'][period_number]['net'] += balance
                dict_to_fill[tax_id][account_id]['show'] = True

        sql = self._sql_tax_amt_regular_taxes(group_by_account)
        query = sql.format(tables=tables, where_clause=where_clause)
        self.env.cr.execute(query, where_params)
        for tax_line_id, account_id, balance in self.env.cr.fetchall():
            if tax_line_id in dict_to_fill:
                dict_to_fill[tax_line_id][account_id]['periods'][period_number]['tax'] += balance
                dict_to_fill[tax_line_id][account_id]['show'] = True
