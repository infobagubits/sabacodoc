# -*- coding: utf-8 -*-
"""Test MELHORIA-026 — arrotondamento timbrature alla mezz'ora.

Orari in UTC (come nel database). Mattina UTC per stare lontani dalla pausa pranzo.
"""

from datetime import datetime

from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


def dt(ora, minuto, secondo=0, giorno=22):
    return datetime(2026, 10, giorno, ora, minuto, secondo)


@tagged('post_install', '-at_install')
class TestArrotondamentoPresenze(TransactionCase):
    """Sulla società reale (come gli altri test del cliente)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dipendente = cls.env['hr.employee'].create({
            'name': 'Dipendente Arrotondamento Test',
            'company_id': cls.env.company.id,
            'resource_calendar_id': False,
            'tz': 'Europe/Rome',
        })
        cls.dipendente_2 = cls.env['hr.employee'].create({
            'name': 'Dipendente Arrotondamento Test 2',
            'company_id': cls.env.company.id,
            'resource_calendar_id': False,
            'tz': 'Europe/Rome',
        })
        cls.Presenza = cls.env['hr.attendance']

    def _presenza(self, check_in, check_out=False, dipendente=None, **altri):
        vals = {'employee_id': (dipendente or self.dipendente).id, 'check_in': check_in, **altri}
        if check_out:
            vals['check_out'] = check_out
        return self.Presenza.create(vals)

    def test_ingresso_per_eccesso(self):
        casi = [
            (dt(6, 17), dt(6, 30)),
            (dt(6, 0, 59), dt(6, 0)),
            (dt(6, 1), dt(6, 30)),
            (dt(6, 30), dt(6, 30)),
            (dt(6, 45, 10), dt(7, 0)),
        ]
        for i, (reale, atteso) in enumerate(casi):
            with self.subTest(reale=reale):
                giorno = 1 + i
                presenza = self._presenza(reale.replace(day=giorno))
                self.assertEqual(presenza.check_in, atteso.replace(day=giorno))
                presenza.unlink()

    def test_ingresso_cambio_giorno(self):
        presenza = self._presenza(dt(23, 45))
        self.assertEqual(presenza.check_in, dt(0, 0, giorno=23))

    def test_uscita_per_difetto(self):
        casi = [
            (dt(9, 8), dt(9, 0)),
            (dt(9, 59, 59), dt(9, 30)),
            (dt(9, 0), dt(9, 0)),
            (dt(9, 30, 30), dt(9, 30)),
        ]
        for i, (reale, atteso) in enumerate(casi):
            with self.subTest(reale=reale):
                giorno = 1 + i
                presenza = self._presenza(dt(6, 0, giorno=giorno), reale.replace(day=giorno))
                self.assertEqual(presenza.check_out, atteso.replace(day=giorno))
                presenza.unlink()

    def test_ore_lavorate_su_orari_arrotondati(self):
        presenza = self._presenza(dt(6, 17), dt(9, 8))
        self.assertEqual((presenza.check_in, presenza.check_out), (dt(6, 30), dt(9, 0)))
        self.assertAlmostEqual(presenza.worked_hours, 2.5, places=4)

    def test_presenza_breve_zero_ore(self):
        presenza = self._presenza(dt(6, 17), dt(6, 25))
        self.assertEqual((presenza.check_in, presenza.check_out), (dt(6, 30), dt(6, 30)))
        self.assertEqual(presenza.worked_hours, 0)

    def test_nuovo_ingresso_dopo_presenza_zero(self):
        self._presenza(dt(6, 17), dt(6, 25))
        nuova = self._presenza(dt(6, 28))
        self.assertEqual(nuova.check_in, dt(6, 30))
        nuova.write({'check_out': dt(9, 8)})
        self.assertEqual(nuova.check_out, dt(9, 0))

    def test_correzione_manuale_uscita(self):
        presenza = self._presenza(dt(6, 17))
        presenza.write({'check_out': dt(6, 20)})
        self.assertEqual(presenza.check_out, dt(6, 30))
        self.assertEqual(presenza.worked_hours, 0)
        presenza.write({'check_out': '2026-10-22 08:44:00'})
        self.assertEqual(presenza.check_out, dt(8, 30))

    def test_correzione_manuale_ingresso(self):
        presenza = self._presenza(dt(6, 0), dt(8, 0))
        presenza.write({'check_in': dt(7, 10)})
        self.assertEqual(presenza.check_in, dt(7, 30))
        self.assertEqual(presenza.check_out, dt(8, 0))
        presenza.write({'check_in': dt(8, 10)})
        self.assertEqual((presenza.check_in, presenza.check_out), (dt(8, 30), dt(8, 30)))

    def test_scrittura_multipla(self):
        prima = self._presenza(dt(6, 17))
        seconda = self._presenza(dt(6, 50), dipendente=self.dipendente_2)
        (prima | seconda).write({'check_out': dt(6, 55)})
        self.assertEqual((prima.check_in, prima.check_out), (dt(6, 30), dt(6, 30)))
        self.assertEqual((seconda.check_in, seconda.check_out), (dt(7, 0), dt(7, 0)))

    def test_scrittura_senza_orari(self):
        presenza = self._presenza(dt(6, 17), dt(9, 8))
        presenza.write({'in_mode': 'kiosk'})
        self.assertEqual((presenza.check_in, presenza.check_out), (dt(6, 30), dt(9, 0)))

    def test_presenza_tecnica_non_arrotondata(self):
        presenza = self._presenza(dt(22, 0), dt(22, 0, 1), in_mode='technical', out_mode='technical')
        self.assertEqual((presenza.check_in, presenza.check_out), (dt(22, 0), dt(22, 0, 1)))

    def test_chiosco(self):
        with freeze_time(dt(6, 17, 40)):
            presenza = self.dipendente._attendance_action_change()
        self.assertEqual(presenza.check_in, dt(6, 30))
        with freeze_time(dt(9, 8, 15)):
            self.dipendente._attendance_action_change()
        self.assertEqual(presenza.check_out, dt(9, 0))
        self.assertAlmostEqual(presenza.worked_hours, 2.5, places=4)

    def test_chiosco_stato_dopo_ingresso_arrotondato(self):
        """Ingresso arrotondato nel futuro: il dipendente risulta comunque entrato."""
        with freeze_time(dt(6, 17)):
            presenza = self.dipendente._attendance_action_change()
            self.dipendente.invalidate_recordset()
            self.assertEqual(self.dipendente.last_attendance_id, presenza)
            self.assertEqual(self.dipendente.attendance_state, 'checked_in')

    def test_chiosco_uscita_prima_della_mezzora(self):
        """Ingresso 08:17 (-> 08:30) e uscita 08:25: niente errore, presenza di 0 ore."""
        with freeze_time(dt(6, 17)):
            presenza = self.dipendente._attendance_action_change()
        with freeze_time(dt(6, 25)):
            self.dipendente._attendance_action_change()
            self.dipendente.invalidate_recordset()
            self.assertEqual(self.dipendente.attendance_state, 'checked_out')
        self.assertEqual((presenza.check_in, presenza.check_out), (dt(6, 30), dt(6, 30)))
        self.assertEqual(presenza.worked_hours, 0)
