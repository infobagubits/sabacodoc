# -*- coding: utf-8 -*-
"""Testes MELHORIA-024 — PDF "Programma per ruolo" respeita os filtros da busca do Gantt.

Cobre:
- builder por dia sem domain → todos os turnos do dia (comportamento anterior preservado);
- `slot_domain` em `data` do report → só os turnos que casam com o filtro;
- `action_print_pdf_from_gantt` repassa o domain para `data['slot_domain']`;
- assinatura antiga (sem domain) continua funcionando.
"""
import datetime

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMelhoria024(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.day = datetime.date(2030, 1, 15)
        Role = cls.env['planning.role']
        cls.role_a = Role.create({'name': 'M024 Ruolo A'})
        cls.role_b = Role.create({'name': 'M024 Ruolo B'})
        Slot = cls.env['planning.slot']
        cls.slot_a = Slot.create({
            'role_id': cls.role_a.id,
            'start_datetime': datetime.datetime(2030, 1, 15, 9, 0),
            'end_datetime': datetime.datetime(2030, 1, 15, 13, 0),
        })
        cls.slot_b = Slot.create({
            'role_id': cls.role_b.id,
            'start_datetime': datetime.datetime(2030, 1, 15, 14, 0),
            'end_datetime': datetime.datetime(2030, 1, 15, 18, 0),
        })
        cls.report = cls.env['report.sabaco_planning_customization.schedule_by_role_document']
        cls.wizard_model = cls.env['planning.schedule.print.wizard']

    def _role_names(self, day_values):
        return {group['name'] for group in day_values['role_groups']}

    def test_builder_without_domain_keeps_all_slots(self):
        vals = self.env['planning.slot']._sabaco_get_schedule_by_role_report_values(self.day)
        names = self._role_names(vals)
        self.assertIn(self.role_a.name, names)
        self.assertIn(self.role_b.name, names)

    def test_builder_with_domain_filters_slots(self):
        vals = self.env['planning.slot']._sabaco_get_schedule_by_role_report_values(
            self.day, domain=[('role_id', '=', self.role_a.id)]
        )
        names = self._role_names(vals)
        self.assertEqual(names, {self.role_a.name})

    def test_report_values_apply_slot_domain(self):
        data = {
            'date_from': '2030-01-15',
            'date_to': '2030-01-15',
            'slot_domain': [('role_id', '=', self.role_b.id)],
        }
        values = self.report._get_report_values([], data=data)
        self.assertEqual(len(values['days']), 1)
        self.assertEqual(self._role_names(values['days'][0]), {self.role_b.name})

    def test_report_values_with_wizard_and_domain(self):
        """Pulsante PDF: wizard esiste E domain arriva in `data`."""
        wizard = self.wizard_model.create({'date_from': self.day, 'date_to': self.day})
        values = self.report._get_report_values(
            wizard.ids, data={'slot_domain': [('role_id', '=', self.role_a.id)]}
        )
        self.assertEqual(self._role_names(values['days'][0]), {self.role_a.name})

    def test_gantt_action_passes_domain(self):
        domain = [('role_id', '=', self.role_a.id)]
        action = self.wizard_model.action_print_pdf_from_gantt(
            '2030-01-15', '2030-01-15', domain
        )
        self.assertEqual(action['data']['slot_domain'], domain)

    def test_gantt_action_legacy_signature(self):
        action = self.wizard_model.action_print_pdf_from_gantt('2030-01-15')
        self.assertEqual(action['data']['slot_domain'], [])
        self.assertEqual(action['data']['date_from'], '2030-01-15')
        self.assertEqual(action['data']['date_to'], '2030-01-15')
