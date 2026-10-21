# -*- coding: utf-8 -*-
"""Testes BUG-010 — PDF "Programma per ruolo" no dia da troca de hora.

Cobre:
- 25/10/2026 (fim do horário de verão, dia de 25h): horários iguais ao Gantt, sem +1h;
- turno até 23:30 nesse dia não é cortado em "24:00";
- 28/03/2027 (início do horário de verão, dia de 23h): sem −1h;
- dia comum continua igual (regressão);
- alocação por hora usa horas de relógio;
- fuso do relatório é sempre Europe/Rome, mesmo com usuário em UTC.
"""
import datetime

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestBug010(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Slot = cls.env['planning.slot']
        cls.role = cls.env['planning.role'].create({'name': 'B010 Ruolo'})

    def _create_slot(self, start, end):
        return self.Slot.create({
            'role_id': self.role.id,
            'start_datetime': start,
            'end_datetime': end,
        })

    def _labels(self, report_date):
        vals = self.Slot._sabaco_get_schedule_by_role_report_values(
            report_date, domain=[('role_id', '=', self.role.id)]
        )
        return sorted(
            bar['time_range_label']
            for group in vals['role_groups']
            for row in group['rows']
            for bar in row['slots']
        )

    def test_dst_end_day_has_no_offset(self):
        # 25/10/2026 dopo le 03:00 è CET (UTC+1)
        self._create_slot(datetime.datetime(2026, 10, 25, 10, 0),
                          datetime.datetime(2026, 10, 25, 14, 0))
        self._create_slot(datetime.datetime(2026, 10, 25, 17, 0),
                          datetime.datetime(2026, 10, 25, 22, 30))
        self.assertEqual(
            self._labels(datetime.date(2026, 10, 25)),
            ['11:00 - 15:00', '18:00 - 23:30'],
        )

    def test_dst_start_day_has_no_offset(self):
        # 28/03/2027 dopo le 02:00 è CEST (UTC+2)
        self._create_slot(datetime.datetime(2027, 3, 28, 9, 0),
                          datetime.datetime(2027, 3, 28, 13, 0))
        self.assertEqual(self._labels(datetime.date(2027, 3, 28)), ['11:00 - 15:00'])

    def test_regular_day_unchanged(self):
        self._create_slot(datetime.datetime(2030, 1, 15, 9, 0),
                          datetime.datetime(2030, 1, 15, 13, 0))
        self.assertEqual(self._labels(datetime.date(2030, 1, 15)), ['10:00 - 14:00'])

    def test_day_after_dst_end_unchanged(self):
        self._create_slot(datetime.datetime(2026, 10, 24, 9, 0),
                          datetime.datetime(2026, 10, 24, 13, 0))
        self.assertEqual(self._labels(datetime.date(2026, 10, 24)), ['11:00 - 15:00'])

    def test_hourly_allocation_uses_wall_clock_hours(self):
        slot = self._create_slot(datetime.datetime(2026, 10, 25, 10, 0),
                                 datetime.datetime(2026, 10, 25, 14, 0))
        day_start, day_end, tz = self.Slot._sabaco_day_bounds(datetime.date(2026, 10, 25))
        hourly = slot._sabaco_compute_slot_hourly_allocation(
            slot, day_start, day_end, tz, {}, {}
        )
        self.assertEqual(sorted(h for h, v in hourly.items() if v > 0), [11, 12, 13, 14])

    def test_report_timezone_is_always_rome(self):
        self.env.user.tz = 'UTC'
        self._create_slot(datetime.datetime(2030, 1, 15, 9, 0),
                          datetime.datetime(2030, 1, 15, 13, 0))
        self.assertEqual(self.Slot._sabaco_report_timezone().zone, 'Europe/Rome')
        self.assertEqual(self._labels(datetime.date(2030, 1, 15)), ['10:00 - 14:00'])
