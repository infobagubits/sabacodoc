# -*- coding: utf-8 -*-
"""Testes MELHORIA-022 — avviso sui corrispettivi quando o conto não quadra.

Cobre o campo calculado ``account.move.corrispettivi_mismatch_warning`` de
``sabaco_customizations``: nas registrazioni dos giornali cujo nome começa pelo
prefixo configurado, o total Dare e o total Avere das righe do conto configurado
têm de coincidir; caso contrário o campo traz a mensagem de avviso.

Os dois ``ir.config_parameter`` são apontados para um conto e um giornale de
teste, isolando os testes do dado semeado em ``data/`` e do banco real.
"""

from odoo.tests.common import TransactionCase
from odoo.tests import tagged

from odoo.addons.sabaco_customizations.models.account_move import (
    CORRISPETTIVI_ACCOUNT_PARAM,
    CORRISPETTIVI_JOURNAL_PREFIX_PARAM,
)


@tagged('post_install', '-at_install')
class TestCorrispettiviMismatch(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.params = cls.env['ir.config_parameter'].sudo()

        # Conti di test: 'asset_current' evita i vincoli dei conti
        # cliente/fornitore (partner obbligatorio sulla riga).
        cls.account_target = cls._new_account('Corrispettivi Test')
        cls.account_contra = cls._new_account('Contropartita Test')
        cls.account_other = cls._new_account('Altro Conto Test')

        cls.journal_corr = cls.env['account.journal'].create({
            'name': 'Corrispettivi Test',
            'code': 'CRTST',
            'type': 'general',
        })
        cls.journal_bank = cls.env['account.journal'].create({
            'name': 'Banca Test',
            'code': 'BKTST',
            'type': 'general',
        })

        cls.params.set_param(CORRISPETTIVI_ACCOUNT_PARAM, cls.account_target.code)
        cls.params.set_param(CORRISPETTIVI_JOURNAL_PREFIX_PARAM, 'Corrispettivi')

    @classmethod
    def _new_account(cls, name):
        """Crea un conto con il primo codice libero (DB reale: codici occupati)."""
        Account = cls.env['account.account']
        code = next(
            str(c) for c in range(999900, 999999)
            if not Account.search_count([('code', '=', str(c))])
        )
        return Account.create({
            'name': name,
            'code': code,
            'account_type': 'asset_current',
        })

    def _entry(self, journal, lines):
        """Crea una registrazione bilanciata nel totale.

        ``lines``: lista di ``(conto, dare, avere)``. Lo sbilancio introdotto
        sul conto target è compensato da una riga sulla contropartita, così il
        move resta valido anche se lo squadro interno esiste.
        """
        vals = [
            (0, 0, {
                'account_id': account.id,
                'name': 'Riga test',
                'debit': debit,
                'credit': credit,
            })
            for account, debit, credit in lines
        ]
        imbalance = sum(d for _a, d, _c in lines) - sum(c for _a, _d, c in lines)
        if imbalance:
            vals.append((0, 0, {
                'account_id': self.account_contra.id,
                'name': 'Contropartita',
                'debit': max(-imbalance, 0.0),
                'credit': max(imbalance, 0.0),
            }))
        return self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': '2026-01-15',
            'line_ids': vals,
        })

    def _warning(self, move):
        """Rilegge il campo calcolato (non memorizzato) forzando il recompute."""
        move.invalidate_recordset(['corrispettivi_mismatch_warning'])
        return move.corrispettivi_mismatch_warning

    # ------------------------------------------------------------------
    # ✅ Nessun avviso — il conto quadra
    # ------------------------------------------------------------------
    def test_due_righe_quadrate_nessun_avviso(self):
        move = self._entry(self.journal_corr, [
            (self.account_target, 100.0, 0.0),
            (self.account_target, 0.0, 100.0),
        ])
        self.assertFalse(
            self._warning(move), "Conto quadrato: nessun avviso",
        )

    def test_tre_righe_somma_quadrata_nessun_avviso(self):
        """La somma conta, non il numero di righe."""
        move = self._entry(self.journal_corr, [
            (self.account_target, 100.0, 0.0),
            (self.account_target, 0.0, 40.0),
            (self.account_target, 0.0, 60.0),
        ])
        self.assertFalse(self._warning(move))

    def test_nessuna_riga_sul_conto_nessun_avviso(self):
        move = self._entry(self.journal_corr, [
            (self.account_other, 50.0, 0.0),
            (self.account_contra, 0.0, 50.0),
        ])
        self.assertFalse(self._warning(move))

    # ------------------------------------------------------------------
    # ⚠️ Avviso — il conto non quadra
    # ------------------------------------------------------------------
    def test_due_righe_squadrate_avviso(self):
        move = self._entry(self.journal_corr, [
            (self.account_target, 100.0, 0.0),
            (self.account_target, 0.0, 60.0),
        ])
        msg = self._warning(move)
        self.assertTrue(msg, "Conto squadrato: avviso atteso")
        self.assertIn(self.account_target.code, msg)
        self.assertIn('Dare', msg)
        self.assertIn('Avere', msg)

    def test_una_sola_riga_sul_conto_avviso(self):
        move = self._entry(self.journal_corr, [
            (self.account_target, 100.0, 0.0),
        ])
        self.assertTrue(self._warning(move))

    def test_prefisso_case_insensitive_e_spazi(self):
        """Nome giornale con spazio iniziale e minuscole: avviso comunque."""
        journal = self.env['account.journal'].create({
            'name': '  corrispettivi minuscolo',
            'code': 'CRMIN',
            'type': 'general',
        })
        move = self._entry(journal, [
            (self.account_target, 100.0, 0.0),
            (self.account_target, 0.0, 60.0),
        ])
        self.assertTrue(self._warning(move))

    # ------------------------------------------------------------------
    # Giornali fuori dal prefisso — protegge BAM / BCC / OV
    # ------------------------------------------------------------------
    def test_giornale_fuori_prefisso_nessun_avviso(self):
        move = self._entry(self.journal_bank, [
            (self.account_target, 100.0, 0.0),
            (self.account_target, 0.0, 60.0),
        ])
        self.assertFalse(
            self._warning(move),
            "Giornale fuori dal prefisso non deve generare avviso",
        )

    # ------------------------------------------------------------------
    # Parametri non configurati — nessun avviso, nessuna eccezione
    # ------------------------------------------------------------------
    def test_parametro_conto_vuoto_nessun_avviso(self):
        move = self._entry(self.journal_corr, [
            (self.account_target, 100.0, 0.0),
            (self.account_target, 0.0, 60.0),
        ])
        self.params.set_param(CORRISPETTIVI_ACCOUNT_PARAM, '')
        self.assertFalse(self._warning(move))

    def test_parametro_prefisso_vuoto_nessun_avviso(self):
        move = self._entry(self.journal_corr, [
            (self.account_target, 100.0, 0.0),
            (self.account_target, 0.0, 60.0),
        ])
        self.params.set_param(CORRISPETTIVI_JOURNAL_PREFIX_PARAM, '')
        self.assertFalse(self._warning(move))
