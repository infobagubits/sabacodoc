# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestInvoicePartnerFlags(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        recv = cls.env['account.account'].search([
            ('account_type', '=', 'asset_receivable'), ('deprecated', '=', False),
        ], limit=1)
        pay = cls.env['account.account'].search([
            ('account_type', '=', 'liability_payable'), ('deprecated', '=', False),
        ], limit=1)
        partner_vals = {
            'name': 'Partner Flag Test',
            'is_customer': False,
            'is_supplier': False,
        }
        if recv:
            partner_vals['property_account_receivable_id'] = recv.id
        if pay:
            partner_vals['property_account_payable_id'] = pay.id
        cls.partner = cls.env['res.partner'].create(partner_vals)
        cls.tax_sale = cls.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'), ('amount', '>', 0),
            ('company_id', '=', company.id),
        ], limit=1)
        cls.tax_purchase = cls.env['account.tax'].search([
            ('type_tax_use', '=', 'purchase'), ('amount', '>', 0),
            ('company_id', '=', company.id),
        ], limit=1)
        cls.product = cls.env['product.product'].search([], limit=1)

    def _simulate_posted_and_mark(self, move):
        """Evita il vincolo di sequenza del DB: forza state in SQL e chiama l'hook."""
        self.env.cr.execute(
            "UPDATE account_move SET state = 'posted' WHERE id = %s",
            (move.id,),
        )
        move.invalidate_recordset(['state'])
        move._sabaco_mark_partner_flags()

    def test_out_invoice_marks_customer(self):
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_date': '2026-01-15',
            'invoice_line_ids': [(0, 0, {
                'name': 'Riga',
                'quantity': 1,
                'price_unit': 10,
                'product_id': self.product.id,
                'tax_ids': [(6, 0, self.tax_sale.ids)] if self.tax_sale else [(5, 0, 0)],
            })],
        })
        self.assertFalse(self.partner.is_customer)
        self._simulate_posted_and_mark(move)
        self.assertTrue(self.partner.is_customer)
        self.assertFalse(self.partner.is_supplier)

    def test_in_invoice_marks_supplier(self):
        partner = self.env['res.partner'].create({
            'name': 'Supplier Flag Test',
            'is_customer': False,
            'is_supplier': False,
        })
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': '2026-01-15',
            'invoice_line_ids': [(0, 0, {
                'name': 'Riga',
                'quantity': 1,
                'price_unit': 10,
                'product_id': self.product.id,
                'tax_ids': [(6, 0, self.tax_purchase.ids)] if self.tax_purchase else [(5, 0, 0)],
            })],
        })
        self.assertFalse(partner.is_supplier)
        self._simulate_posted_and_mark(move)
        self.assertTrue(partner.is_supplier)
        self.assertFalse(partner.is_customer)

    def test_draft_does_not_mark(self):
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_date': '2026-01-15',
            'invoice_line_ids': [(0, 0, {
                'name': 'Riga',
                'quantity': 1,
                'price_unit': 10,
                'product_id': self.product.id,
            })],
        })
        self.assertEqual(move.state, 'draft')
        self.assertFalse(self.partner.is_customer)
