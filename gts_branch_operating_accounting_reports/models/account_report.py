import calendar
import copy
import json
import io
import logging
import lxml.html
from odoo import models, fields, api, _
from datetime import timedelta, datetime, date
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, pycompat
from babel.dates import get_quarter_names
from odoo.tools.misc import formatLang, format_date
from odoo.tools import config
from odoo.addons.web.controllers.main import clean_action
from odoo.tools.safe_eval import safe_eval
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    # TODO saas-17: remove the try/except to directly import from misc
    import xlsxwriter

_logger = logging.getLogger(__name__)


class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    filter_branch = None
    filter_operating_unit = None

    @api.model
    def _get_options(self, previous_options=None):
        # Create default options.
        options = {
            'unfolded_lines': previous_options and previous_options.get('unfolded_lines') or [],
        }

        # Multi-company is there for security purpose and can't be disabled by a filter.
        if self.filter_multi_company:
            if self._context.get('allowed_company_ids'):
                # Retrieve the companies through the multi-companies widget.
                companies = self.env['res.company'].browse(self._context['allowed_company_ids'])
            else:
                # When called from testing files, 'allowed_company_ids' is missing.
                # Then, give access to all user's companies.
                companies = self.env.companies
            if len(companies) > 1:
                options['multi_company'] = [
                    {'id': c.id, 'name': c.name} for c in companies
                    ]

        # Call _init_filter_date/_init_filter_comparison because the second one must be called after the first one.
        if self.filter_date:
            self._init_filter_date(options, previous_options=previous_options)
        if self.filter_comparison:
            self._init_filter_comparison(options, previous_options=previous_options)
        if self.filter_analytic:
            options['analytic'] = self.filter_analytic
        # options['branch'] = self.get_branch()
        # options['operating_unit'] = self.get_operating_unit()
        self._init_filter_branch(options, previous_options=previous_options)
        self._init_filter_operating_unit(options, previous_options=previous_options)

        filter_list = [attr
                       for attr in dir(self)
                       if (attr.startswith('filter_') or attr.startswith('order_'))
                       and attr not in ('filter_date', 'filter_comparison', 'filter_multi_company')
                       and len(attr) > 7
                       and not callable(getattr(self, attr))]
        for filter_key in filter_list:
            options_key = filter_key[7:]
            init_func = getattr(self, '_init_%s' % filter_key, None)
            if init_func:
                init_func(options, previous_options=previous_options)
            else:
                filter_opt = getattr(self, filter_key, None)
                if filter_opt is not None:
                    if previous_options and options_key in previous_options:
                        options[options_key] = previous_options[options_key]
                    else:
                        options[options_key] = filter_opt
        return options

    # def get_branch(self):
    #     branch_read = self.env['res.branch'].search([], order="name")
    #     branch = []
    #     for c in branch_read:
    #         branch.append({'id': c.id, 'name': c.name, 'selected': False})
    #     return branch
    #
    # def get_operating_unit(self):
    #     operating_unit_read = self.env['operating.unit'].search([], order="name")
    #     operating_unit = []
    #     for c in operating_unit_read:
    #         operating_unit.append({'id': c.id, 'name': c.name, 'selected': False})
    #     return operating_unit

    def _init_filter_branch(self, options, previous_options=None):
        if self.filter_branch is None:
            return
        if previous_options and previous_options.get('branch'):
            branch_previous = dict((opt['id'], opt['selected']) for opt in previous_options['branch'] if 'selected' in
                                   opt)
        else:
            branch_previous = {}
        options['branch'] = []
        branch_read = self.env['res.branch'].search([], order="name")
        for c in branch_read:
            options['branch'].append({'id': c.id, 'name': c.name, 'selected': branch_previous.get(c.id)})

    def _init_filter_operating_unit(self, options, previous_options=None):
        if self.filter_operating_unit is None:
            return
        if previous_options and previous_options.get('operating_unit'):
            operating_unit_previous = dict((opt['id'], opt['selected']) for opt in previous_options['operating_unit'] if
                                           'selected' in opt)
        else:
            operating_unit_previous = {}
        operating_unit_read = self.env['operating.unit'].search([], order="name")
        options['operating_unit'] = []
        for c in operating_unit_read:
            options['operating_unit'].append(
                {'id': c.id, 'name': c.name, 'selected': operating_unit_previous.get(c.id)})
