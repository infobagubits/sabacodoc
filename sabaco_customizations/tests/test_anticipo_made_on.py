# -*- coding: utf-8 -*-
"""Test MELHORIA-023 — data del movimento bancario = ``made_on`` per anticipo fatture.

Copre l'override di ``account.online.account._format_transactions`` in
``sabaco_customizations``: se l'etichetta della transazione contiene il testo
configurato, la data diventa il ``made_on`` di ``transaction_details``; in ogni
altro caso la data resta quella restituita dal proxy.

``_format_transactions`` è chiamato direttamente: nessuna chiamata al proxy.
"""

import json
from datetime import date

from odoo import Command
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

from odoo.addons.sabaco_customizations.models.account_online_account import (
    ANTICIPO_MADE_ON_LABEL_PARAM,
)

LABEL = 'ANTICIPO S.B.F. CONTO UNICO ANTICIPO FATTURE DISTINTA'


@tagged('post_install', '-at_install')
class TestAnticipoMadeOn(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.params = cls.env['ir.config_parameter'].sudo()
        cls.params.set_param(ANTICIPO_MADE_ON_LABEL_PARAM, LABEL)

        journal = cls.env['account.journal'].create({
            'name': 'Banca Online Test',
            'code': 'BOTST',
            'type': 'bank',
        })
        link = cls.env['account.online.link'].create({
            'name': 'Banca Test',
            'client_id': 'client_id_test',
            'refresh_token': 'refresh_token',
            'access_token': 'access_token',
        })
        cls.online_account = cls.env['account.online.account'].create({
            'name': 'Conto Test',
            'account_online_link_id': link.id,
            'journal_ids': [Command.set(journal.id)],
        })

    def _format(self, payment_ref=f'{LABEL} N. 022972', details=None):
        transaction = {
            'online_transaction_identifier': 'tx-1',
            'date': '2026-08-31',
            'payment_ref': payment_ref,
            'amount': 1000.0,
        }
        if details is not None:
            transaction['transaction_details'] = details
        return self.online_account._format_transactions([transaction])[0]['date']

    def test_made_on_details_stringa_json(self):
        details = json.dumps({'made_on': '2026-08-28', 'extra': {'posting_date': '2026-09-20'}})
        self.assertEqual(self._format(details=details), date(2026, 8, 28))

    def test_made_on_details_dict(self):
        self.assertEqual(self._format(details={'made_on': '2026-08-28'}), date(2026, 8, 28))

    def test_etichetta_case_insensitive(self):
        date_res = self._format(payment_ref=f'{LABEL.lower()} n. 1', details={'made_on': '2026-08-28'})
        self.assertEqual(date_res, date(2026, 8, 28))

    def test_etichetta_diversa(self):
        date_res = self._format(payment_ref='SATISPAY EUROPE SA', details={'made_on': '2026-08-28'})
        self.assertEqual(date_res, date(2026, 8, 31))

    def test_senza_payment_ref(self):
        self.assertEqual(self._format(payment_ref=False, details={'made_on': '2026-08-28'}), date(2026, 8, 31))

    def test_senza_details(self):
        self.assertEqual(self._format(), date(2026, 8, 31))

    def test_details_json_non_valido(self):
        self.assertEqual(self._format(details='{non json'), date(2026, 8, 31))

    def test_details_non_dict(self):
        self.assertEqual(self._format(details=json.dumps(['2026-08-28'])), date(2026, 8, 31))

    def test_senza_made_on(self):
        self.assertEqual(self._format(details={'extra': {}}), date(2026, 8, 31))

    def test_made_on_non_valido(self):
        self.assertEqual(self._format(details={'made_on': '28/08/2026'}), date(2026, 8, 31))

    def test_parametro_vuoto(self):
        self.params.set_param(ANTICIPO_MADE_ON_LABEL_PARAM, '')
        self.assertEqual(self._format(details={'made_on': '2026-08-28'}), date(2026, 8, 31))
