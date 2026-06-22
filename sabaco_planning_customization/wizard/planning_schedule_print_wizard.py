# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PlanningSchedulePrintWizard(models.TransientModel):
    _name = 'planning.schedule.print.wizard'
    _description = 'Stampa programma per ruolo'

    date = fields.Date(
        string='Data',
        required=True,
        default=fields.Date.context_today,
    )

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref(
            'sabaco_planning_customization.action_report_planning_schedule_by_role'
        ).report_action(self, data={'report_date': fields.Date.to_string(self.date)})

    @api.model
    def action_print_pdf_from_gantt(self, date_str):
        wizard = self.create({'date': fields.Date.from_string(date_str)})
        return wizard.action_print_pdf()
