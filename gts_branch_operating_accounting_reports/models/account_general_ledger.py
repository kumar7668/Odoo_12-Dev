from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta


class AccountGeneralLedgerReport(models.AbstractModel):
    _inherit = "account.general.ledger"

    filter_branch = True
    filter_operating_unit = True

    @api.model
    def _get_query_sums(self, options_list, expanded_account=None):
        ''' Construct a query retrieving all the aggregated sums to build the report. It includes:
        - sums for all accounts.
        - sums for the initial balances.
        - sums for the unaffected earnings.
        - sums for the tax declaration.
        :param options_list:        The report options list, first one being the current dates range, others being the
                                    comparisons.
        :param expanded_account:    An optional account.account record that must be specified when expanding a line
                                    with of without the load more.
        :return:                    (query, params)
        '''
        options = options_list[0]
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        params = []
        queries = []

        # Create the currency table.
        # As the currency table is the same whatever the comparisons, create it only once.
        ct_query = self.env['res.currency']._get_query_currency_table(options)

        # ============================================
        # 1) Get sums for all accounts.
        # ============================================

        domain = [('account_id', '=', expanded_account.id)] if expanded_account else []

        for i, options_period in enumerate(options_list):
            # The period domain is expressed as:
            # [
            #   ('date' <= options['date_to']),
            #   '|',
            #   ('date' >= fiscalyear['date_from']),
            #   ('account_id.user_type_id.include_initial_balance', '=', True),
            # ]

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

            new_options = self._get_options_sum_balance(options_period)
            tables, where_clause, where_params = self._query_get(new_options, domain=domain)
            params += where_params
            queries.append('''
                    SELECT
                        account_move_line.account_id                            AS groupby,
                        'sum'                                                   AS key,
                        MAX(account_move_line.date)                             AS max_date,
                        %s                                                      AS period_number,
                        COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                        SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                        SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                        SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                    FROM %s
                    LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
                    WHERE %s
                    GROUP BY account_move_line.account_id
                ''' % (i, tables, ct_query, where_clause))

        # ============================================
        # 2) Get sums for the unaffected earnings.
        # ============================================

        domain = [('account_id.user_type_id.include_initial_balance', '=', False)]
        if expanded_account:
            domain.append(('company_id', '=', expanded_account.company_id.id))

        # Compute only the unaffected earnings for the oldest period.

        i = len(options_list) - 1
        options_period = options_list[-1]

        # The period domain is expressed as:
        # [
        #   ('date' <= fiscalyear['date_from'] - 1),
        #   ('account_id.user_type_id.include_initial_balance', '=', False),
        # ]

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

        new_options = self._get_options_unaffected_earnings(options_period)
        tables, where_clause, where_params = self._query_get(new_options, domain=domain)
        params += where_params
        queries.append('''
                SELECT
                    account_move_line.company_id                            AS groupby,
                    'unaffected_earnings'                                   AS key,
                    NULL                                                    AS max_date,
                    %s                                                      AS period_number,
                    COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                    SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                    SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                    SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                FROM %s
                LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
                WHERE %s
                GROUP BY account_move_line.company_id
            ''' % (i, tables, ct_query, where_clause))

        # ============================================
        # 3) Get sums for the initial balance.
        # ============================================

        domain = None
        if expanded_account:
            domain = [('account_id', '=', expanded_account.id)]
        elif unfold_all:
            domain = []
        elif options['unfolded_lines']:
            domain = [('account_id', 'in', [int(line[8:]) for line in options['unfolded_lines']])]

        if domain is not None:
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

            for i, options_period in enumerate(options_list):
                # The period domain is expressed as:
                # [
                #   ('date' <= options['date_from'] - 1),
                #   '|',
                #   ('date' >= fiscalyear['date_from']),
                #   ('account_id.user_type_id.include_initial_balance', '=', True)
                # ]

                new_options = self._get_options_initial_balance(options_period)
                tables, where_clause, where_params = self._query_get(new_options, domain=domain)
                params += where_params
                queries.append('''
                        SELECT
                            account_move_line.account_id                            AS groupby,
                            'initial_balance'                                       AS key,
                            NULL                                                    AS max_date,
                            %s                                                      AS period_number,
                            COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                            SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                            SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                            SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                        FROM %s
                        LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
                        WHERE %s
                        GROUP BY account_move_line.account_id
                    ''' % (i, tables, ct_query, where_clause))

        # ============================================
        # 4) Get sums for the tax declaration.
        # ============================================
        journal_options = self._get_options_journals(options)
        if not expanded_account and len(journal_options) == 1 and journal_options[0]['type'] in ('sale', 'purchase'):
            for i, options_period in enumerate(options_list):
                tables, where_clause, where_params = self._query_get(options_period)
                params += where_params + where_params
                queries += ['''
                        SELECT
                            tax_rel.account_tax_id                  AS groupby,
                            'base_amount'                           AS key,
                            NULL                                    AS max_date,
                            %s                                      AS period_number,
                            0.0                                     AS amount_currency,
                            0.0                                     AS debit,
                            0.0                                     AS credit,
                            SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                        FROM account_move_line_account_tax_rel tax_rel, %s
                        LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
                        WHERE account_move_line.id = tax_rel.account_move_line_id AND %s
                        GROUP BY tax_rel.account_tax_id
                    ''' % (i, tables, ct_query, where_clause), '''
                        SELECT
                        account_move_line.tax_line_id               AS groupby,
                        'tax_amount'                                AS key,
                            NULL                                    AS max_date,
                            %s                                      AS period_number,
                            0.0                                     AS amount_currency,
                            0.0                                     AS debit,
                            0.0                                     AS credit,
                            SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                        FROM %s
                        LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
                        WHERE %s
                        GROUP BY account_move_line.tax_line_id
                    ''' % (i, tables, ct_query, where_clause)]
        return ' UNION ALL '.join(queries), params

    @api.model
    def _get_query_amls(self, options, expanded_account, offset=None, limit=None):
        ''' Construct a query retrieving the account.move.lines when expanding a report line with or without the load
        more.
        :param options:             The report options.
        :param expanded_account:    The account.account record corresponding to the expanded line.
        :param offset:              The offset of the query (used by the load more).
        :param limit:               The limit of the query (used by the load more).
        :return:                    (query, params)
        '''

        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        # Get sums for the account move lines.
        # period: [('date' <= options['date_to']), ('date', '>=', options['date_from'])]
        domain = [  ]
        if expanded_account:
            domain = [('account_id', '=', expanded_account.id)]
        elif unfold_all:
            domain = []
        elif options['unfolded_lines']:
            domain = [('account_id', 'in', [int(line[8:]) for line in options['unfolded_lines']])]

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

        new_options = self._force_strict_range(options)
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
                    ROUND(account_move_line.debit * currency_table.rate, currency_table.precision)   AS debit,
                    ROUND(account_move_line.credit * currency_table.rate, currency_table.precision)  AS credit,
                    ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) AS balance,
                    account_move_line__move_id.name         AS move_name,
                    company.currency_id                     AS company_currency_id,
                    partner.name                            AS partner_name,
                    account_move_line__move_id.move_type         AS move_type,
                    account.code                            AS account_code,
                    account.name                            AS account_name,
                    journal.code                            AS journal_code,
                    journal.name                            AS journal_name,
                    full_rec.name                           AS full_rec_name
                FROM account_move_line
                LEFT JOIN account_move account_move_line__move_id ON account_move_line__move_id.id = account_move_line.move_id
                LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
                LEFT JOIN res_company company               ON company.id = account_move_line.company_id
                LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
                LEFT JOIN account_account account           ON account.id = account_move_line.account_id
                LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
                LEFT JOIN account_full_reconcile full_rec   ON full_rec.id = account_move_line.full_reconcile_id
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
