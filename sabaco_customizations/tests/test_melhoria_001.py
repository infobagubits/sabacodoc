# -*- coding: utf-8 -*-
"""Testes MELHORIA-001 — bloqueio de confirmação de fattura sem imposta.

Cobre o override de ``account.move.action_post`` em ``sabaco_customizations``:
fatture cliente/fornecedor (``out_invoice``/``in_invoice``) não podem ser
confirmadas quando têm linhas de produto sem ``tax_ids``.
"""

from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestMelhoria001(TransactionCase):

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
        partner_vals = {'name': 'Cliente Test'}
        if recv:
            partner_vals['property_account_receivable_id'] = recv.id
        if pay:
            partner_vals['property_account_payable_id'] = pay.id
        cls.partner = cls.env['res.partner'].create(partner_vals)
        # Reusa imposte esistenti da DB: la localizzazione italiana impone
        # vincoli (codice esenzione) sulla creazione di imposte allo 0%.
        cls.tax_sale = cls.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'), ('amount', '>', 0),
            ('company_id', '=', company.id),
        ], limit=1)
        cls.tax_sale_zero = cls.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'), ('amount', '=', 0),
            ('company_id', '=', company.id),
        ], limit=1)
        cls.tax_purchase = cls.env['account.tax'].search([
            ('type_tax_use', '=', 'purchase'), ('amount', '>', 0),
            ('company_id', '=', company.id),
        ], limit=1)
        # Prodotto reale già configurato (conti contabili) per permettere il post.
        cls.product = cls.env['product.product'].search([
            ('property_account_income_id', '!=', False),
        ], limit=1) or cls.env['product.product'].create({
            'name': 'Prodotto Test', 'type': 'consu',
        })

    def _line(self, tax=None, product=True, display_type=False):
        vals = {'quantity': 1, 'price_unit': 100.0}
        if display_type:
            vals['display_type'] = display_type
            vals['name'] = 'Sezione/Nota'
        else:
            if product:
                vals['product_id'] = self.product.id
            vals['name'] = 'Riga'
            vals['tax_ids'] = [(6, 0, tax.ids)] if tax else [(5, 0, 0)]
        return (0, 0, vals)

    def _invoice(self, move_type, lines):
        return self.env['account.move'].create({
            'move_type': move_type,
            'partner_id': self.partner.id,
            'invoice_date': '2026-01-15',
            'invoice_line_ids': lines,
        })

    # ------------------------------------------------------------------
    # ❌ Cenário de erro — bloqueio
    # ------------------------------------------------------------------
    def test_out_invoice_sem_imposta_bloqueia(self):
        inv = self._invoice('out_invoice', [self._line(tax=None)])
        with self.assertRaises(UserError):
            inv.action_post()
        self.assertEqual(inv.state, 'draft', "Fattura non deve essere confermata")

    def test_in_invoice_sem_imposta_bloqueia(self):
        inv = self._invoice('in_invoice', [self._line(tax=None)])
        with self.assertRaises(UserError):
            inv.action_post()
        self.assertEqual(inv.state, 'draft')

    # ------------------------------------------------------------------
    # ✅ Happy path — confirma
    # ------------------------------------------------------------------
    def test_out_invoice_com_imposta_confirma(self):
        inv = self._invoice('out_invoice', [self._line(tax=self.tax_sale)])
        inv.action_post()
        self.assertEqual(inv.state, 'posted')

    def test_out_invoice_imposta_zero_confirma(self):
        """Imposta 0% conta como imposta — não deve bloquear."""
        inv = self._invoice('out_invoice', [self._line(tax=self.tax_sale_zero)])
        inv.action_post()
        self.assertEqual(inv.state, 'posted')

    def test_in_invoice_com_imposta_confirma(self):
        inv = self._invoice('in_invoice', [self._line(tax=self.tax_purchase)])
        inv.action_post()
        self.assertEqual(inv.state, 'posted')

    # ------------------------------------------------------------------
    # Refund / receipts — não bloqueados
    # ------------------------------------------------------------------
    def test_out_refund_sem_imposta_nao_bloqueia(self):
        inv = self._invoice('out_refund', [self._line(tax=None)])
        inv.action_post()
        self.assertEqual(inv.state, 'posted')

    def test_in_refund_sem_imposta_nao_bloqueia(self):
        inv = self._invoice('in_refund', [self._line(tax=None)])
        inv.action_post()
        self.assertEqual(inv.state, 'posted')

    # ------------------------------------------------------------------
    # Só seção/nota — sem produto — confirma
    # ------------------------------------------------------------------
    def test_apenas_secao_nota_confirma(self):
        inv = self._invoice('out_invoice', [
            self._line(display_type='line_section'),
            self._line(display_type='line_note'),
        ])
        inv.action_post()
        self.assertEqual(inv.state, 'posted')

    # ------------------------------------------------------------------
    # Mensagem de erro — conteúdo e truncamento
    # ------------------------------------------------------------------
    def test_mensagem_cita_nome_e_produtos(self):
        inv = self._invoice('out_invoice', [self._line(tax=None)])
        with self.assertRaises(UserError) as cm:
            inv.action_post()
        msg = str(cm.exception)
        self.assertIn(self.product.name, msg)
        self.assertIn('senza imposta', msg)

    def test_mensagem_trunca_acima_de_cinco(self):
        products = self.env['product.product'].create([
            {'name': f'Prod {i}', 'type': 'consu'} for i in range(7)
        ])
        lines = [
            (0, 0, {
                'product_id': p.id,
                'name': 'Riga',
                'quantity': 1,
                'price_unit': 10.0,
                'tax_ids': [(5, 0, 0)],
            })
            for p in products
        ]
        inv = self._invoice('out_invoice', lines)
        with self.assertRaises(UserError) as cm:
            inv.action_post()
        self.assertIn('(+2 altri)', str(cm.exception))
