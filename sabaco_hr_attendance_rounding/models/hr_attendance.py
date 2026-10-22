from datetime import timedelta

from odoo import api, fields, models

MEZZORA = 30


def _arrotonda_ingresso(dt):
    """Per eccesso alla mezz'ora successiva; i secondi non contano (08:00:59 -> 08:00)."""
    if not dt:
        return dt
    dt = fields.Datetime.to_datetime(dt).replace(second=0, microsecond=0)
    resto = dt.minute % MEZZORA
    return dt + timedelta(minutes=MEZZORA - resto) if resto else dt


def _arrotonda_uscita(dt):
    """Per difetto alla mezz'ora precedente (13:08 -> 13:00)."""
    if not dt:
        return dt
    dt = fields.Datetime.to_datetime(dt)
    return dt.replace(minute=dt.minute - dt.minute % MEZZORA, second=0, microsecond=0)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    @api.model
    def _sabaco_arrotonda_vals(self, vals, check_in_attuale=False, check_out_attuale=False):
        """Arrotonda check_in/check_out presenti nei vals.

        Le presenze tecniche (rilevamento assenze del core) restano come sono.
        Gli orari in UTC: Europe/Rome ha offset a ore intere, quindi la mezz'ora
        in UTC coincide con quella locale.
        Se l'uscita arrotondata cade prima dell'ingresso la presenza vale 0 ore.
        """
        vals = dict(vals)
        if vals.get('check_in') and vals.get('in_mode') != 'technical':
            vals['check_in'] = _arrotonda_ingresso(vals['check_in'])
        if vals.get('check_out') and vals.get('out_mode') != 'technical':
            vals['check_out'] = _arrotonda_uscita(vals['check_out'])
        check_in = fields.Datetime.to_datetime(vals['check_in'] if 'check_in' in vals else check_in_attuale)
        check_out = fields.Datetime.to_datetime(vals['check_out'] if 'check_out' in vals else check_out_attuale)
        if check_in and check_out and check_out < check_in:
            vals['check_out'] = check_in
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._sabaco_arrotonda_vals(vals) for vals in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        if 'check_in' not in vals and 'check_out' not in vals:
            return super().write(vals)
        if len(self) > 1:
            # L'uscita minima dipende dall'ingresso di ogni presenza.
            for attendance in self:
                attendance.write(vals)
            return True
        vals = self._sabaco_arrotonda_vals(vals, self.check_in, self.check_out)
        return super().write(vals)
