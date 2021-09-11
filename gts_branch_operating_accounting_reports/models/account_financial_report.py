import ast
from odoo import models, fields, api, _
from odoo.tools import float_is_zero, ustr


class ReportAccountFinancialReport(models.Model):
    _inherit = "account.financial.html.report"

    filter_branch = True
    filter_operating_unit = True

    @property
    def filters_branch(self):
        if self.show_journal_filter:
            return True
        return super().filters_branch

    @property
    def filters_operating_unit(self):
        if self.operating_unit_filter:
            return True
        return super().filters_operating_unit

    branch_filter = fields.Boolean('Allow filtering by Branch')
    operating_unit_filter = fields.Boolean('Allow filtering by Operating Unit')


class AccountFinancialReportLine(models.Model):
    _inherit = "account.financial.html.report.line"

    def _get_domain(self, options, financial_report):
        ''' Get the domain to be applied on the current line.
        :return: A valid domain to apply on the account.move.line model.
        '''
        self.ensure_one()

        branch = [a.get('id') for a in options.get('branch') if a.get('selected', False)]
        if not branch:
            branch = [a.get('id') for a in options.get('branch')]
        operating_unit = [a.get('id') for a in options.get('operating_unit') if a.get('selected', False)]
        if not operating_unit:
            operating_unit = [a.get('id') for a in options.get('operating_unit')]

        # Domain defined on the line.
        domain = self.domain and ast.literal_eval(ustr(self.domain)) or []

        # Take care of the tax exigibility.
        # /!\ Still needed as there are still some custom tax reports in localizations.
        if financial_report.tax_report:
            domain.append(('tax_exigible', '=', True))
        if branch:
            domain.append(('branch_id', 'in', branch))
        if operating_unit:
            domain.append(('operating_unit_id', 'in', operating_unit))
        return domain
