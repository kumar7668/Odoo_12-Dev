
{
    'name': 'GTS Branch Management | Multiple Branch(Unit) Operation Setup for All Applications Odoo/OpenERP',
    'version': '12.0.0.1',
    'category': 'Sales',
    'author': 'Geo Technosoft',
    'website': 'https://www.geotechnosoft.com',
    'summary': 'Manage multiple Branch or multiple Unit Operations in company',
    'sequence': 1,
    'description':
        """
            This module allows to manage multiple branch or manage multiple unit or manage multiple operation 
            in Sales, Purchases, Accounting, Payment, Voucher, Accounting Reports
            inside single company. 
            Do you have multiple unit for single company? Do you want them to be work as 
            separate entity inside the company? Here you go, we have make plugin that helps users to 
            make different branch for single company with multi branch concept which works same as multi-company environment.
Also Don't worry about the access rights too, We have added branch user/manager roles inside the module, 
Branch user can only access records of its specific branch and Branch manager can see records of all Branches.
Branch functionality added to Sale Order, Purchase Order, Invoice, Warehouse
    """,
    'depends': ['base', 'sale_management', 'purchase',
        'stock', 'account', 'point_of_sale'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/account_common_report_wizard.xml',
        'views/res_branch_views.xml',
        'views/pos_view.xml',
        'views/res_users.xml',
        # 'report/account_analysis_report.xml',
        # 'report/report_account_financial.xml',
        # 'report/report_trial_balance.xml',
    ],
    # 'qweb': ['static/src/xml/*.xml'],
    'images': ['static/description/banner.png'],
    'price': 39.99,
    'currency': 'EUR',
    'license': 'OPL-1',
    'installable': True,
    'application': True
}
