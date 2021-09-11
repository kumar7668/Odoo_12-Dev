from odoo import models, api, _, fields
from odoo.tools.misc import formatLang
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, timedelta
from collections import defaultdict


class ReportPartnerLedger(models.AbstractModel):
    _inherit = 'account.partner.ledger'

    filter_branch = True
    filter_operating_unit = True

    ####################################################
    # QUERIES
    ####################################################

    # Q2
    @api.model
    def _get_query_sums(self, options, expanded_partner=None):
        ''' Construct a query retrieving all the aggregated sums to build the report. It includes:
        - sums for all partners.
        - sums for the initial balances.
        :param options:             The report options.
        :param expanded_partner:    An optional res.partner record that must be specified when expanding a line
                                    with of without the load more.
        :return:                    (query, params)
        '''
        params = []
        queries = []

        domain = []
        if expanded_partner is not None:
            domain.append(('partner_id', '=', expanded_partner.id))
        # else:
        #     domain = []
        branch = [a.get('id') for a in options.get('branch') if a.get('selected', False)]
        if branch:
            domain.append(('branch_id', 'in', branch))
        if not branch:
            branch = [a.get('id') for a in options.get('branch')]
            domain.append(('branch_id', 'in', branch))
        operating_unit = [a.get('id') for a in options.get('operating_unit') if a.get('selected', False)]
        if operating_unit:
            domain.append(('operating_unit_id', 'in', operating_unit))
        if not operating_unit:
            operating_unit = [a.get('id') for a in options.get('operating_unit')]
            domain.append(('operating_unit_id', 'in', operating_unit))

        # Create the currency table.
        ct_query = self.env['res.currency']._get_query_currency_table(options)

        # Get sums for all partners.
        # period: [('date' <= options['date_to']), ('date' >= options['date_from'])]
        new_options = self._get_options_sum_balance(options)
        tables, where_clause, where_params = self._query_get(new_options, domain=domain)
        params += where_params
        queries.append('''
               SELECT
                   account_move_line.partner_id        AS groupby,
                   'sum'                               AS key,
                   SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                   SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                   SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
               FROM %s
               LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
               WHERE %s
               GROUP BY account_move_line.partner_id
           ''' % (tables, ct_query, where_clause))

        # Get sums for the initial balance.
        # period: [('date' <= options['date_from'] - 1)]
        new_options = self._get_options_initial_balance(options)
        tables, where_clause, where_params = self._query_get(new_options, domain=domain)
        params += where_params
        queries.append('''
               SELECT
                   account_move_line.partner_id        AS groupby,
                   'initial_balance'                   AS key,
                   SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                   SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                   SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
               FROM %s
               LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
               WHERE %s
               GROUP BY account_move_line.partner_id
           ''' % (tables, ct_query, where_clause))

        return ' UNION ALL '.join(queries), params

    # Q4
    @api.model
    def _get_lines_without_partner(self, options, expanded_partner=None, offset=0, limit=0):
        ''' Get the detail of lines without partner reconciled with a line with a partner. Those lines should be
        considered as belonging the partner for the reconciled amount as it may clear some of the partner invoice/bill
        and they have to be accounted in the partner balance.'''
        params = []
        branch = [a.get('id') for a in options.get('branch') if a.get('selected', False)]
        if not branch:
            branch = [a.get('id') for a in options.get('branch')]
        operating_unit = [a.get('id') for a in options.get('operating_unit') if a.get('selected', False)]
        if not operating_unit:
            operating_unit = [a.get('id') for a in options.get('operating_unit')]
        if expanded_partner:
            partner_clause = '= %s'
            params = [expanded_partner.id] + params
        else:
            partner_clause = 'IS NOT NULL'
        new_options = self._get_options_without_partner(options)
        params += [options['date']['date_from'], options['date']['date_to']]
        tables, where_clause, where_params = self._query_get(new_options, domain=[('branch_id', 'in', branch),
                                                                                  ('operating_unit_id', 'in', operating_unit)])
        params += where_params + [offset]
        limit_clause = ''
        if limit != 0:
            params += [limit]
            limit_clause = "LIMIT %s"
        query = '''
               SELECT
                   account_move_line.id,
                   account_move_line.date,
                   account_move_line.date_maturity,
                   account_move_line.name,
                   account_move_line.ref,
                   account_move_line.company_id,
                   account_move_line.account_id,
                   account_move_line.payment_id,
                   aml_with_partner.partner_id,
                   account_move_line.currency_id,
                   account_move_line.amount_currency,
                   account_move_line.matching_number,
                   CASE WHEN aml_with_partner.balance > 0 THEN 0 ELSE partial.amount END AS debit,
                   CASE WHEN aml_with_partner.balance < 0 THEN 0 ELSE partial.amount END AS credit,
                   CASE WHEN aml_with_partner.balance > 0 THEN -partial.amount ELSE partial.amount END AS balance,
                   account_move_line__move_id.name         AS move_name,
                   account_move_line__move_id.move_type    AS move_type,
                   account.code                            AS account_code,
                   account.name                            AS account_name,
                   journal.code                            AS journal_code,
                   journal.name                            AS journal_name,
                   full_rec.name                           AS full_rec_name
               FROM {tables},
                   account_partial_reconcile partial
                   LEFT JOIN account_full_reconcile full_rec ON full_rec.id = partial.full_reconcile_id,
                   account_move_line aml_with_partner,
                   account_journal journal,
                   account_account account
               WHERE (account_move_line.id = partial.debit_move_id OR account_move_line.id = partial.credit_move_id)
                  AND account_move_line.partner_id IS NULL
                  AND (aml_with_partner.id = partial.debit_move_id OR aml_with_partner.id = partial.credit_move_id)
                  AND aml_with_partner.partner_id {partner_clause}
                  AND journal.id = account_move_line.journal_id
                  AND account.id = account_move_line.account_id
                  AND partial.max_date BETWEEN %s AND %s
                  AND {where_clause}
               ORDER BY account_move_line.date, account_move_line.id
               OFFSET %s
               {limit_clause}
           '''.format(tables=tables, partner_clause=partner_clause, where_clause=where_clause,
                      limit_clause=limit_clause)

        return query, params

    # Q5
    @api.model
    def _get_sums_without_partner(self, options, expanded_partner=None):
        ''' Get the sum of lines without partner reconciled with a line with a partner, grouped by partner. Those lines
        should be considered as belonging the partner for the reconciled amount as it may clear some of the partner
        invoice/bill and they have to be accounted in the partner balance.'''
        params = []
        branch = [a.get('id') for a in options.get('branch') if a.get('selected', False)]
        if not branch:
            branch = [a.get('id') for a in options.get('branch')]
        operating_unit = [a.get('id') for a in options.get('operating_unit') if a.get('selected', False)]
        if not operating_unit:
            operating_unit = [a.get('id') for a in options.get('operating_unit')]
        if expanded_partner:
            partner_clause = '= %s'
            params = [expanded_partner.id]
        else:
            partner_clause = 'IS NOT NULL'

        new_options = self._get_options_without_partner(options)
        params = [options['date']['date_from']] + params + [options['date']['date_to']]
        tables, where_clause, where_params = self._query_get(new_options, domain=[('branch_id', 'in', branch),
                                                                                  ('operating_unit_id', 'in', operating_unit)])
        params += where_params

        query = '''
               SELECT
                   aml_with_partner.partner_id AS groupby,
                   SUM(CASE WHEN aml_with_partner.balance > 0 THEN 0 ELSE partial.amount END) AS debit,
                   SUM(CASE WHEN aml_with_partner.balance < 0 THEN 0 ELSE partial.amount END) AS credit,
                   SUM(CASE WHEN aml_with_partner.balance > 0 THEN -partial.amount ELSE partial.amount END) AS balance,
                   CASE WHEN partial.max_date < %s THEN 'initial_balance' ELSE 'sum' END as key
               FROM {tables}, account_partial_reconcile partial, account_move_line aml_with_partner
               WHERE (account_move_line.id = partial.debit_move_id OR account_move_line.id = partial.credit_move_id)
                  AND account_move_line.partner_id IS NULL
                  AND (aml_with_partner.id = partial.debit_move_id OR aml_with_partner.id = partial.credit_move_id)
                  AND aml_with_partner.partner_id {partner_clause}
                  AND partial.max_date <= %s
                  AND {where_clause}
               GROUP BY aml_with_partner.partner_id, key
           '''.format(tables=tables, partner_clause=partner_clause, where_clause=where_clause)
        return query, params

    # Q3
    @api.model
    def _get_query_amls(self, options, expanded_partner=None, offset=None, limit=None):
        ''' Construct a query retrieving the account.move.lines when expanding a report line with or without the load
        more.
        :param options:             The report options.
        :param expanded_partner:    The res.partner record corresponding to the expanded line.
        :param offset:              The offset of the query (used by the load more).
        :param limit:               The limit of the query (used by the load more).
        :return:                    (query, params)
        '''
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        # Get sums for the account move lines.
        # period: [('date' <= options['date_to']), ('date', '>=', options['date_from'])]
        domain = []
        if expanded_partner is not None:
            domain.append(('partner_id', '=', expanded_partner.id))
        elif unfold_all:
            domain = []
        elif options['unfolded_lines']:
            domain.append(('partner_id', 'in', [int(line[8:]) for line in options['unfolded_lines']]))

        branch = [a.get('id') for a in options.get('branch') if a.get('selected', False)]
        if branch:
            domain.append(('branch_id', 'in', branch))
        if not branch:
            branch = [a.get('id') for a in options.get('branch')]
            domain.append(('branch_id', 'in', branch))
        operating_unit = [a.get('id') for a in options.get('operating_unit') if a.get('selected', False)]
        if operating_unit:
            domain.append(('operating_unit_id', 'in', operating_unit))
        if not operating_unit:
            operating_unit = [a.get('id') for a in options.get('operating_unit')]
            domain.append(('operating_unit_id', 'in', operating_unit))

        new_options = self._get_options_sum_balance(options)
        tables, where_clause, where_params = self._query_get(new_options, domain=domain)
        ct_query = self.env['res.currency']._get_query_currency_table(options)

        query = '''
               SELECT
                   account_move_line.id,
                   account_move_line.date,
                   account_move_line.date_maturity,
                   account_move_line.name,
                   account_move_line.ref,
                   account_move_line.company_id,
                   account_move_line.account_id,
                   account_move_line.payment_id,
                   account_move_line.partner_id,
                   account_move_line.currency_id,
                   account_move_line.amount_currency,
                   account_move_line.matching_number,
                   ROUND(account_move_line.debit * currency_table.rate, currency_table.precision)   AS debit,
                   ROUND(account_move_line.credit * currency_table.rate, currency_table.precision)  AS credit,
                   ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) AS balance,
                   account_move_line__move_id.name         AS move_name,
                   company.currency_id                     AS company_currency_id,
                   partner.name                            AS partner_name,
                   account_move_line__move_id.move_type    AS move_type,
                   account.code                            AS account_code,
                   account.name                            AS account_name,
                   journal.code                            AS journal_code,
                   journal.name                            AS journal_name
               FROM account_move_line
               LEFT JOIN account_move account_move_line__move_id ON account_move_line__move_id.id = account_move_line.move_id
               LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
               LEFT JOIN res_company company               ON company.id = account_move_line.company_id
               LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
               LEFT JOIN account_account account           ON account.id = account_move_line.account_id
               LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
               WHERE %s
               ORDER BY account_move_line.date, account_move_line.id
           ''' % (ct_query, where_clause)

        if offset:
            query += ' OFFSET %s '
            where_params.append(offset)
        if limit:
            query += ' LIMIT %s '
            where_params.append(limit)

        return query, where_params
