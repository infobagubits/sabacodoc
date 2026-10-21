# -*- coding: utf-8 -*-
"""Test MELHORIA-025 — data differita nelle transazioni bancarie.

Scenari portati dalla MELHORIA-020 della Moris (v19) sul widget di
riconciliazione v18: "modificare" una transazione = Reset + nuova validazione.
Il saldo considera la registrazione della banca e i differimenti non annullati.
"""

from odoo import Command, fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

DATA_BANCA = '2026-07-15'


@tagged('post_install', '-at_install')
class TestDifferitaBanca(TransactionCase):
    """Sulla società reale (come gli altri test del cliente): la base di test del core
    crea una nuova società, che nel database del cliente non è consentito."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        Account = cls.env['account.account']
        # Codici fuori dai prefissi con analitica obbligatoria del cliente.
        cls.conto_costo = Account.create({'name': 'Assicurazioni Test', 'code': 'SABDIFC', 'account_type': 'expense'})
        cls.conto_costo_2 = Account.create({'name': 'Altri costi Test', 'code': 'SABDIFC2', 'account_type': 'expense'})
        cls.conto_ricavo = Account.create({'name': 'Affitti attivi Test', 'code': 'SABDIFR', 'account_type': 'income'})
        cls.risconto_attivo = Account.create({'name': 'Risconti attivi Test', 'code': 'SABDIFRA', 'account_type': 'asset_current'})
        cls.risconto_passivo = Account.create({'name': 'Risconti passivi Test', 'code': 'SABDIFRP', 'account_type': 'liability_current'})
        cls.giornale_differiti = cls.env['account.journal'].create({
            'name': 'Differimenti Test',
            'code': 'SDIF',
            'type': 'general',
        })
        cls.giornale_banca = cls.env['account.journal'].create({
            'name': 'Banca Differita Test',
            'code': 'SDIFB',
            'type': 'bank',
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Fornitore Differita Test'})
        # Il cliente blocca la conferma di fatture senza imposta (BUG-007).
        cls.iva_acquisti = cls.env['account.tax'].search([
            ('company_id', '=', cls.company.id),
            ('type_tax_use', '=', 'purchase'),
            ('amount_type', '=', 'percent'),
            ('amount', '=', 22.0),
        ], limit=1)
        cls.company.write({
            'deferred_expense_journal_id': cls.giornale_differiti.id,
            'deferred_revenue_journal_id': cls.giornale_differiti.id,
            'deferred_expense_account_id': cls.risconto_attivo.id,
            'deferred_revenue_account_id': cls.risconto_passivo.id,
            'generate_deferred_expense_entries_method': 'on_validation',
            'generate_deferred_revenue_entries_method': 'on_validation',
            'deferred_expense_amount_computation_method': 'month',
            'deferred_revenue_amount_computation_method': 'month',
        })

    # -------------------------------------------------------------------------
    # Helper
    # -------------------------------------------------------------------------

    def _create_st_line(self, amount, date=DATA_BANCA):
        return self.env['account.bank.statement.line'].create({
            'amount': amount,
            'date': date,
            'payment_ref': 'Assicurazione test',
            'journal_id': self.giornale_banca.id,
        })

    def _wizard(self, st_line):
        return self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})

    def _imposta(self, wizard, line, campo, valore):
        """Simula la modifica di un campo nel form delle operazioni manuali."""
        line[campo] = valore
        wizard._js_action_line_changed(line.index, campo)

    def _riga_in_modifica(self, wizard, flag='auto_balance'):
        line = wizard.line_ids.filtered(lambda x: x.flag == flag)[:1]
        wizard._js_action_mount_line_in_edit(line.index)
        return wizard.line_ids.filtered(lambda x: x.index == wizard.form_index)

    def _valida(self, st_line, conto, inizio=False, fine=False):
        wizard = self._wizard(st_line)
        line = self._riga_in_modifica(wizard)
        self._imposta(wizard, line, 'account_id', conto)
        if inizio:
            self._imposta(wizard, line, 'deferred_start_date', fields.Date.to_date(inizio))
        if fine:
            self._imposta(wizard, line, 'deferred_end_date', fields.Date.to_date(fine))
        wizard._js_action_validate()
        return wizard

    def _reset(self, st_line):
        self._wizard(st_line)._js_action_reset()

    def _saldo(self, st_line, conto, al=None):
        move = st_line.move_id
        moves = move | move.deferred_move_ids.filtered(lambda m: m.state != 'cancel')
        lines = moves.line_ids.filtered(
            lambda l: l.account_id == conto and (not al or l.date <= fields.Date.to_date(al))
        )
        return sum(lines.mapped('balance'))

    def _attivi(self, st_line):
        return st_line.move_id._sabaco_differimenti_attivi()

    # -------------------------------------------------------------------------
    # Test
    # -------------------------------------------------------------------------

    def test_costo_12_mesi(self):
        st_line = self._create_st_line(-1200.0, date=DATA_BANCA)
        self._valida(st_line, self.conto_costo, '2026-07-01', '2027-06-30')

        riga = st_line.move_id.line_ids.filtered(lambda l: l.account_id == self.conto_costo)
        self.assertRecordValues(riga, [{
            'deferred_start_date': fields.Date.to_date('2026-07-01'),
            'deferred_end_date': fields.Date.to_date('2027-06-30'),
        }])
        # 1 registrazione di storno totale + 12 quote mensili
        self.assertEqual(len(self._attivi(st_line)), 13)
        self.assertAlmostEqual(self._saldo(st_line, self.conto_costo, '2026-07-31'), 100.0)
        self.assertAlmostEqual(self._saldo(st_line, self.conto_costo, '2026-12-31'), 600.0)
        self.assertAlmostEqual(self._saldo(st_line, self.conto_costo), 1200.0)
        self.assertAlmostEqual(self._saldo(st_line, self.risconto_attivo, '2026-12-31'), 600.0)

    def test_ricavo(self):
        st_line = self._create_st_line(600.0, date=DATA_BANCA)
        self._valida(st_line, self.conto_ricavo, '2026-07-01', '2026-12-31')

        self.assertTrue(self._attivi(st_line))
        self.assertAlmostEqual(self._saldo(st_line, self.conto_ricavo, '2026-07-31'), -100.0)
        self.assertAlmostEqual(self._saldo(st_line, self.conto_ricavo), -600.0)
        self.assertAlmostEqual(self._saldo(st_line, self.risconto_passivo, '2026-07-31'), -500.0)

    def test_stesso_mese(self):
        st_line = self._create_st_line(-1200.0, date=DATA_BANCA)
        self._valida(st_line, self.conto_costo, '2026-07-01', '2026-07-31')

        self.assertFalse(st_line.move_id.deferred_move_ids)
        self.assertAlmostEqual(self._saldo(st_line, self.conto_costo, '2026-07-31'), 1200.0)

    def test_nuovo_periodo_senza_duplicati(self):
        st_line = self._create_st_line(-1200.0, date=DATA_BANCA)
        self._valida(st_line, self.conto_costo, '2026-07-01', '2027-06-30')
        vecchi = self._attivi(st_line)

        self._reset(st_line)
        self.assertFalse(self._attivi(st_line))

        self._valida(st_line, self.conto_costo, '2026-08-01', '2027-01-31')
        nuovi = self._attivi(st_line)
        self.assertFalse(nuovi & vecchi)
        self.assertEqual(len(nuovi), 7)
        self.assertAlmostEqual(self._saldo(st_line, self.conto_costo, '2026-07-31'), 0.0)
        self.assertAlmostEqual(self._saldo(st_line, self.conto_costo, '2026-08-31'), 200.0)
        self.assertAlmostEqual(self._saldo(st_line, self.conto_costo), 1200.0)

    def test_validare_due_volte_non_duplica(self):
        st_line = self._create_st_line(-1200.0, date=DATA_BANCA)
        self._valida(st_line, self.conto_costo, '2026-07-01', '2027-06-30')

        # Transazione gia' riconciliata: la riga 'aml' rilegge le date dalla registrazione.
        wizard = self._wizard(st_line)
        riga_aml = wizard.line_ids.filtered(lambda l: l.flag == 'aml')
        self.assertRecordValues(riga_aml, [{
            'deferred_start_date': fields.Date.to_date('2026-07-01'),
            'deferred_end_date': fields.Date.to_date('2027-06-30'),
            'sabaco_differita_ammessa': True,
        }])
        wizard._action_validate()

        self.assertEqual(len(self._attivi(st_line)), 13)
        self.assertAlmostEqual(self._saldo(st_line, self.conto_costo, '2026-07-31'), 100.0)
        self.assertAlmostEqual(self._saldo(st_line, self.conto_costo), 1200.0)

    def test_modifica_importo_riga(self):
        st_line = self._create_st_line(-1200.0, date=DATA_BANCA)
        self._valida(st_line, self.conto_costo, '2026-07-01', '2027-06-30')
        self._reset(st_line)

        # Solo 600 sul costo differito, il resto su un altro conto senza date.
        wizard = self._wizard(st_line)
        line = self._riga_in_modifica(wizard)
        self._imposta(wizard, line, 'account_id', self.conto_costo)
        self._imposta(wizard, line, 'deferred_start_date', fields.Date.to_date('2026-07-01'))
        self._imposta(wizard, line, 'deferred_end_date', fields.Date.to_date('2027-06-30'))
        self._imposta(wizard, line, 'balance', 600.0)
        resto = self._riga_in_modifica(wizard)
        self._imposta(wizard, resto, 'account_id', self.conto_costo_2)
        wizard._js_action_validate()

        riga = st_line.move_id.line_ids.filtered(lambda l: l.account_id == self.conto_costo)
        self.assertEqual(riga.deferred_start_date, fields.Date.to_date('2026-07-01'))
        self.assertAlmostEqual(self._saldo(st_line, self.conto_costo, '2026-07-31'), 50.0)
        self.assertAlmostEqual(self._saldo(st_line, self.conto_costo), 600.0)

    def test_togliere_date(self):
        st_line = self._create_st_line(-1200.0, date=DATA_BANCA)
        self._valida(st_line, self.conto_costo, '2026-07-01', '2027-06-30')
        self._reset(st_line)
        self._valida(st_line, self.conto_costo)

        self.assertFalse(self._attivi(st_line))
        self.assertAlmostEqual(self._saldo(st_line, self.conto_costo, '2026-07-31'), 1200.0)

    def test_eliminare_riga(self):
        st_line = self._create_st_line(-1200.0, date=DATA_BANCA)
        self._valida(st_line, self.conto_costo, '2026-07-01', '2027-06-30')
        self._reset(st_line)
        self._valida(st_line, self.conto_costo_2)

        self.assertFalse(st_line.move_id.line_ids.filtered(lambda l: l.account_id == self.conto_costo))
        self.assertFalse(self._attivi(st_line))

    def test_senza_date(self):
        st_line = self._create_st_line(-1200.0, date=DATA_BANCA)
        self._valida(st_line, self.conto_costo)

        self.assertFalse(st_line.move_id.deferred_move_ids)
        self.assertFalse(st_line.move_id.line_ids.filtered('deferred_start_date'))

    def test_data_fine_uguale_inizio(self):
        st_line = self._create_st_line(-1200.0, date=DATA_BANCA)
        wizard = self._wizard(st_line)
        line = self._riga_in_modifica(wizard)
        self._imposta(wizard, line, 'account_id', self.conto_costo)
        self._imposta(wizard, line, 'deferred_start_date', fields.Date.to_date('2026-09-10'))
        self.assertEqual(line.deferred_end_date, fields.Date.to_date('2026-09-10'))

    def test_solo_costi_ricavi(self):
        st_line = self._create_st_line(-1200.0, date=DATA_BANCA)
        conti = [
            (self.risconto_attivo, False),
            (self.conto_costo, True),
            (self.conto_ricavo, True),
        ]
        for conto, atteso in conti:
            with self.subTest(conto=conto.name):
                wizard = self._wizard(st_line)
                line = self._riga_in_modifica(wizard)
                self._imposta(wizard, line, 'account_id', conto)
                self.assertEqual(line.sabaco_differita_ammessa, atteso)

        # Su un conto non ammesso le date non arrivano alla registrazione.
        wizard = self._wizard(st_line)
        line = self._riga_in_modifica(wizard)
        self._imposta(wizard, line, 'account_id', self.risconto_attivo)
        line.deferred_start_date = fields.Date.to_date('2026-07-01')
        line.deferred_end_date = fields.Date.to_date('2027-06-30')
        wizard._js_action_validate()
        self.assertFalse(st_line.move_id.line_ids.filtered('deferred_start_date'))
        self.assertFalse(st_line.move_id.deferred_move_ids)

    def test_regressione_fattura_fornitore(self):
        """Le fatture con data differita continuano a usare il percorso del core."""
        fattura = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner.id,
            'invoice_date': DATA_BANCA,
            'date': DATA_BANCA,
            'invoice_line_ids': [Command.create({
                'name': 'Assicurazione',
                'quantity': 1,
                'price_unit': 1200.0,
                'account_id': self.conto_costo.id,
                'tax_ids': [Command.set(self.iva_acquisti.ids)],
                'deferred_start_date': '2026-07-01',
                'deferred_end_date': '2027-06-30',
            })],
        })
        fattura.action_post()
        self.assertEqual(len(fattura.deferred_move_ids), 13)
        self.assertEqual(fattura._get_deferred_entries_method(), 'on_validation')
