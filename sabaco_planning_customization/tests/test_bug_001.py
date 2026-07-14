# -*- coding: utf-8 -*-
"""Testes BUG-001 — label HH:MM na pill do relatório "Programma per ruolo".

Cobre a lógica script-testável da issue:
- `_sabaco_format_time_label`: conversão minutos-do-dia → HH:MM com clamp 0–1440.
- `time_range_label` em `_sabaco_slot_bar_values`: recorte à faixa visível (06:00–24:00),
  garantindo que turno iniciado antes das 06h rotula a pill começando em "06:00".

Ajustes puramente visuais (largura 160px, fonte 11px, pill sem total/nome) → roteiro manual.
"""
from datetime import datetime, time, timedelta

import pytz

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestBug001(TransactionCase):

    def setUp(self):
        super().setUp()
        self.PlanningSlot = self.env['planning.slot']

    # ------------------------------------------------------------------ #
    # _sabaco_format_time_label — happy path
    # ------------------------------------------------------------------ #
    def test_format_time_label_happy(self):
        f = self.PlanningSlot._sabaco_format_time_label
        self.assertEqual(f(0), '00:00')
        self.assertEqual(f(360), '06:00')        # 06h — início da faixa visível
        self.assertEqual(f(90), '01:30')
        self.assertEqual(f(1439), '23:59')

    def test_format_time_label_rounding(self):
        """Arredonda para o minuto mais próximo."""
        f = self.PlanningSlot._sabaco_format_time_label
        self.assertEqual(f(365.7), '06:06')      # 365.7 → 366
        self.assertEqual(f(365.2), '06:05')      # 365.2 → 365

    def test_format_time_label_clamp(self):
        """Fora de 0–1440 é fixado nos limites."""
        f = self.PlanningSlot._sabaco_format_time_label
        self.assertEqual(f(-50), '00:00')        # negativo → 00:00
        self.assertEqual(f(2000), '24:00')       # > 1440 → 24:00 (DAY_MINUTES)
        self.assertEqual(f(1440), '24:00')

    # ------------------------------------------------------------------ #
    # time_range_label na barra — recorte à faixa visível 06:00–24:00
    # ------------------------------------------------------------------ #
    def _make_slot(self, start_local, end_local, tz):
        """Cria planning.slot com start/end (naive local → UTC)."""
        start_utc = tz.localize(start_local).astimezone(pytz.UTC).replace(tzinfo=None)
        end_utc = tz.localize(end_local).astimezone(pytz.UTC).replace(tzinfo=None)
        return self.PlanningSlot.create({
            'start_datetime': start_utc,
            'end_datetime': end_utc,
        })

    def test_time_range_label_normal(self):
        report_date = datetime(2026, 7, 14).date()
        day_start, day_end, tz = self.PlanningSlot._sabaco_day_bounds(report_date)
        slot = self._make_slot(
            datetime.combine(report_date, time(9, 0)),
            datetime.combine(report_date, time(17, 30)),
            tz,
        )
        bar = self.PlanningSlot._sabaco_slot_bar_values(slot, day_start, day_end, tz)
        self.assertIsNotNone(bar)
        self.assertEqual(bar['time_range_label'], '09:00 - 17:30')

    def test_time_range_label_before_six_clamped(self):
        """Turno iniciando às 04:00 → label começa em 06:00 (coerente com barra recortada)."""
        report_date = datetime(2026, 7, 14).date()
        day_start, day_end, tz = self.PlanningSlot._sabaco_day_bounds(report_date)
        slot = self._make_slot(
            datetime.combine(report_date, time(4, 0)),
            datetime.combine(report_date, time(10, 0)),
            tz,
        )
        bar = self.PlanningSlot._sabaco_slot_bar_values(slot, day_start, day_end, tz)
        self.assertIsNotNone(bar)
        self.assertEqual(bar['time_range_label'], '06:00 - 10:00')

    def test_slot_entirely_before_six_hidden(self):
        """Turno inteiro na madrugada (02:00–05:00) → não gera barra."""
        report_date = datetime(2026, 7, 14).date()
        day_start, day_end, tz = self.PlanningSlot._sabaco_day_bounds(report_date)
        slot = self._make_slot(
            datetime.combine(report_date, time(2, 0)),
            datetime.combine(report_date, time(5, 0)),
            tz,
        )
        bar = self.PlanningSlot._sabaco_slot_bar_values(slot, day_start, day_end, tz)
        self.assertIsNone(bar)
