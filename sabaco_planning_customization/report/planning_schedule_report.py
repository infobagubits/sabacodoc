# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class ReportPlanningScheduleByRole(models.AbstractModel):
    _name = 'report.sabaco_planning_customization.schedule_by_role_document'
    _description = 'Report programma per ruolo'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        wizard = self.env['planning.schedule.print.wizard'].browse(docids).exists()
        if wizard:
            date_from = wizard.date_from
            date_to = wizard.date_to
        elif data.get('date_from') and data.get('date_to'):
            date_from = fields.Date.from_string(data['date_from'])
            date_to = fields.Date.from_string(data['date_to'])
        elif data.get('report_date'):
            # Retrocompatibilità: singola data legacy trattata come intervallo di 1 giorno.
            date_from = date_to = fields.Date.from_string(data['report_date'])
        else:
            date_from = date_to = fields.Date.context_today(self)

        # Guardie di sicurezza: intervallo valido e al massimo 7 giorni.
        if date_to < date_from:
            date_to = date_from
        if (date_to - date_from).days > 6:
            date_to = date_from + timedelta(days=6)

        slot_model = self.env['planning.slot']
        days = []
        current = date_from
        while current <= date_to:
            days.append(
                slot_model._sabaco_get_schedule_by_role_report_values(current)
            )
            current += timedelta(days=1)

        return {'days': days, 'company': self.env.company}
