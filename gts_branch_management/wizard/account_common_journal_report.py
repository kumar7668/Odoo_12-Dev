# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountCommonJournalReport(models.TransientModel):
    _inherit = "account.common.journal.report"

    branch_ids = fields.Many2one('res.branch', string='Branch')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
