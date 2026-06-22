# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ReportPlanningScheduleByRole(models.AbstractModel):
    _name = 'report.sabaco_planning_customization.schedule_by_role_document'
    _description = 'Report programma per ruolo'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        wizard = self.env['planning.schedule.print.wizard'].browse(docids).exists()
        if wizard:
            report_date = wizard.date
        elif data.get('report_date'):
            report_date = fields.Date.from_string(data['report_date'])
        else:
            report_date = fields.Date.context_today(self)
        return self.env['planning.slot']._sabaco_get_schedule_by_role_report_values(
            report_date
        )
