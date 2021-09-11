from odoo import api, models, _, fields
from odoo.tools.safe_eval import safe_eval


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def _get_default_branch(self):
        User = self.env['res.users']
        return User.browse(self.env.uid).branch_id.id or False

    branch_id = fields.Many2one('res.branch', 'Branch', default=_get_default_branch)


    @api.model
    def _query_get(self, domain=None):
        ''' Inherited for adding branch condition in query '''
        context = dict(self._context or {})
        domain = domain or []
        if not isinstance(domain, (list, tuple)):
            domain = safe_eval(domain)

        date_field = 'date'
        branch_id = 'branch_id'
        operating_unit_id = 'operating_unit_id'

        if context.get('aged_balance'):
            date_field = 'date_maturity'

        if context.get('operating_unit_id'):
            domain += [(operating_unit_id, '=', context['operating_unit_id'])]


        if context.get('branch_id'):
            domain += [(branch_id, '=', context['branch_id'])]

        # if context.get('branch_id'):
        #     domain += [(branch_id, '=', context['branch_id'])]

        if context.get('date_to'):
            domain += [(date_field, '<=', context['date_to'])]
        if context.get('date_from'):
            if not context.get('strict_range'):
                domain += ['|', (date_field, '>=', context['date_from']),
                           ('account_id.user_type_id.include_initial_balance', '=', True)]
            elif context.get('initial_bal'):
                domain += [(date_field, '<', context['date_from'])]
            else:
                domain += [(date_field, '>=', context['date_from'])]

        if context.get('journal_ids'):
            domain += [('journal_id', 'in', context['journal_ids'])]

        state = context.get('state')
        if state and state.lower() != 'all':
            domain += [('move_id.state', '=', state)]

        if context.get('company_id'):
            domain += [('company_id', '=', context['company_id'])]

        if 'company_ids' in context:
            domain += [('company_id', 'in', context['company_ids'])]

        if context.get('reconcile_date'):
            domain += ['|', ('reconciled', '=', False), '|',
                       ('matched_debit_ids.max_date', '>', context['reconcile_date']),
                       ('matched_credit_ids.max_date', '>', context['reconcile_date'])]

        if context.get('account_tag_ids'):
            domain += [('account_id.tag_ids', 'in', context['account_tag_ids'].ids)]

        if context.get('account_ids'):
            domain += [('account_id', 'in', context['account_ids'].ids)]

        if context.get('analytic_tag_ids'):
            domain += ['|', ('analytic_account_id.tag_ids', 'in', context['analytic_tag_ids'].ids),
                       ('analytic_tag_ids', 'in', context['analytic_tag_ids'].ids)]

        if context.get('analytic_account_ids'):
            domain += [('analytic_account_id', 'in', context['analytic_account_ids'].ids)]

        where_clause = ""
        where_clause_params = []
        tables = ''
        if domain:
            query = self._where_calc(domain)
            tables, where_clause, where_clause_params = query.get_sql()
        return tables, where_clause, where_clause_params
