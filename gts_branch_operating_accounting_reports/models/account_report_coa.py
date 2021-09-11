from copy import deepcopy

from odoo import models, api, _, fields


class AccountChartOfAccountReport(models.AbstractModel):
    _inherit = "account.coa.report"

    filter_branch = True
    filter_operating_unit = True
