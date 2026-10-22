from datetime import timedelta

from odoo import api, fields, models

from .hr_attendance import MEZZORA


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.depends('attendance_ids')
    def _compute_last_attendance_id(self):
        """Come il core, ma vede anche l'ingresso arrotondato fino a mezz'ora nel futuro.

        Il core cerca solo check_in <= adesso: un ingresso alle 08:17 salvato come 08:30
        restava escluso, il dipendente risultava uscito e la timbratura successiva
        provava a creare una nuova presenza (errore "non ha registrato l'uscita").
        """
        limite = fields.Datetime.now() + timedelta(minutes=MEZZORA)
        for employee in self:
            employee.last_attendance_id = self.env['hr.attendance'].search([
                ('employee_id', 'in', employee.ids),
                ('check_in', '<=', limite),
            ], order="check_in desc", limit=1)
