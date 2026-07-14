# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PlanningSchedulePrintWizard(models.TransientModel):
    _name = 'planning.schedule.print.wizard'
    _description = 'Stampa programma per ruolo'

    date_from = fields.Date(
        string='Dal',
        required=True,
        default=fields.Date.context_today,
    )
    date_to = fields.Date(
        string='Al',
        required=True,
        default=fields.Date.context_today,
    )

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for wizard in self:
            if wizard.date_to < wizard.date_from:
                raise ValidationError(_(
                    "La data finale non può essere precedente alla data iniziale."
                ))
            if (wizard.date_to - wizard.date_from).days > 6:
                raise ValidationError(_(
                    "È possibile stampare al massimo 7 giorni (una settimana)."
                ))

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref(
            'sabaco_planning_customization.action_report_planning_schedule_by_role'
        ).report_action(self, data={
            'date_from': fields.Date.to_string(self.date_from),
            'date_to': fields.Date.to_string(self.date_to),
        })

    @api.model
    def action_print_pdf_from_gantt(self, date_str, date_to_str=None):
        date_from = fields.Date.from_string(date_str)
        date_to = fields.Date.from_string(date_to_str) if date_to_str else date_from
        wizard = self.create({'date_from': date_from, 'date_to': date_to})
        return wizard.action_print_pdf()
