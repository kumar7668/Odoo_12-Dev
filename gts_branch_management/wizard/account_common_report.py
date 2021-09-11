# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.tools.misc import get_lang


class AccountCommonReport(models.TransientModel):
    _inherit = "account.common.report"

    branch_id = fields.Many2one('res.branch', string='Branch')
    operating_unit_id = fields.Many2one('operating.unit', string='Operating Unit')

    def _build_contexts(self, data):
        print('branch_id11111', data)
        result = {}

        data['form']['branch_id'] = self.read(['branch_id'])[0]
        result['branch_id'] = 'branch_id' in data['form'] and data['form']['branch_id'] or False
        branch_name_long = ''
        if result['branch_id'].get('branch_id'):
                branch_name = self.env['res.branch'].browse(result['branch_id'].get('branch_id')[0]).name
                print(branch_name, 'branch_name')
                branch_name_long += branch_name  
        result['branch_id'] = branch_name_long

        data['form']['operating_unit_id'] = self.read(['operating_unit_id'])[0]
        result['operating_unit_id'] = 'operating_unit_id' in data['form'] and data['form']['operating_unit_id'] or False
        operating_unit_id = ''
        if result['operating_unit_id'].get('operating_unit_id'):
            operating_unit_id_name = self.env['operating.unit'].browse(result['operating_unit_id'].get('operating_unit_id')[0]).name
            print(operating_unit_id_name, 'operating_unit_id_name')
            operating_unit_id += operating_unit_id_name
        result['operating_unit_id'] = operating_unit_id
        # print('jjjjjjj', data['form']['operating_unit_id'][0])
        # result['operating_unit_id'] = data['form']['operating_unit_id'][0]



        result['journal_ids'] = 'journal_ids' in data['form'] and \
                                data['form']['journal_ids'] or False
        result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
        result['date_from'] = data['form']['date_from'] or False
        result['date_to'] = data['form']['date_to'] or False
        result['strict_range'] = True if result['date_from'] else False
        print('result', result)
        return result


    def check_report(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'company_id', 'branch_id', 'operating_unit_id'])[0]
        used_context = self._build_contexts(data)
        print('used_context', used_context)
        data['form']['used_context'] = dict(used_context, lang=get_lang(self.env).code)
        return self.with_context(discard_logo_check=True)._print_report(data)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
