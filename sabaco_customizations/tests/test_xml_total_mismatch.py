# -*- coding: utf-8 -*-
"""Testes BUG-008 — avviso totale XML durante a edição da fattura.

O compute ``_compute_xml_total_mismatch_warning`` busca o totale XML por
``res_id``. Em edição (onchange) o record tem ``NewId``: a busca deve ser
feita no record salvo (``_origin``) e comparada com o total corrente do form.
O totale XML vem do fallback do chatter ("Valore totale dal file XML: …"),
sem precisar de um XML EDI real.
"""

from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestXmlTotalMismatch(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        # Conti non deprecati (nel DB restore alcuni conti standard sono deprecati).
        recv = cls.env['account.account'].search([
            ('account_type', '=', 'asset_receivable'), ('deprecated', '=', False),
        ], limit=1)
        pay = cls.env['account.account'].search([
            ('account_type', '=', 'liability_payable'), ('deprecated', '=', False),
        ], limit=1)
        partner_vals = {'name': 'Partner Test XML'}
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
        cls.product = cls.env['product.product'].search([
            ('property_account_income_id', '!=', False),
        ], limit=1) or cls.env['product.product'].create({
            'name': 'Prodotto Test', 'type': 'consu',
        })

    def _invoice_with_xml_total(self, move_type='out_invoice'):
        """Fattura con 1 riga e messaggio chatter con il totale uguale."""
        tax = self.tax_sale if move_type.startswith('out') else self.tax_purchase
        inv = self.env['account.move'].create({
            'move_type': move_type,
            'partner_id': self.partner.id,
            'invoice_date': '2026-01-15',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': 'Riga',
                'quantity': 1,
                'price_unit': 100.0,
                'tax_ids': [(6, 0, tax.ids)],
            })],
        })
        inv.message_post(body=f"Valore totale dal file XML: {inv.amount_total:.2f}")
        inv.invalidate_recordset(['xml_total_mismatch_warning', 'l10n_it_xml_amount_total'])
        return inv

    # ------------------------------------------------------------------
    # Record salvato (comportamento atual — não pode regredir)
    # ------------------------------------------------------------------
    def test_salvato_totale_uguale_nessun_avviso(self):
        inv = self._invoice_with_xml_total()
        self.assertFalse(inv.xml_total_mismatch_warning)
        self.assertEqual(inv.l10n_it_xml_amount_total, inv.amount_total)

    def test_salvato_totale_diverso_avviso(self):
        inv = self._invoice_with_xml_total()
        inv.invoice_line_ids.price_unit = 100.01
        self.assertTrue(inv.xml_total_mismatch_warning)
        self.assertIn('differisce', inv.xml_total_mismatch_warning)

    # ------------------------------------------------------------------
    # Edição não salva (BUG-008)
    # ------------------------------------------------------------------
    def test_modifica_non_salvata_avviso(self):
        inv = self._invoice_with_xml_total()
        with Form(inv) as f:
            with f.invoice_line_ids.edit(0) as line:
                line.price_unit = 100.01
            self.assertTrue(f.xml_total_mismatch_warning)
            # Torna al valore originale: l'avviso sparisce.
            with f.invoice_line_ids.edit(0) as line:
                line.price_unit = 100.0
            self.assertFalse(f.xml_total_mismatch_warning)

    def test_modifica_non_salvata_avviso_fornitore(self):
        inv = self._invoice_with_xml_total('in_invoice')
        with Form(inv) as f:
            with f.invoice_line_ids.edit(0) as line:
                line.price_unit = 100.01
            self.assertTrue(f.xml_total_mismatch_warning)
            with f.invoice_line_ids.edit(0) as line:
                line.price_unit = 100.0

    def test_nuova_fattura_senza_xml_nessun_avviso(self):
        with Form(self.env['account.move'].with_context(
            default_move_type='out_invoice',
        )) as f:
            f.partner_id = self.partner
            f.invoice_date = '2026-01-15'
            with f.invoice_line_ids.new() as line:
                line.product_id = self.product
                line.price_unit = 50.0
            self.assertFalse(f.xml_total_mismatch_warning)
