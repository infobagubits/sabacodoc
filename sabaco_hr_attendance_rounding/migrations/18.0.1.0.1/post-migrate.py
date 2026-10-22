from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Ricalcola l'ultima presenza dei dipendenti con una presenza aperta.

    Prima della correzione l'ingresso arrotondato nel futuro non veniva visto:
    questi dipendenti risultano usciti pur avendo una presenza aperta.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    aperte = env['hr.attendance'].search([('check_out', '=', False)])
    dipendenti = aperte.employee_id
    if dipendenti:
        env.add_to_compute(env['hr.employee']._fields['last_attendance_id'], dipendenti)
        env.flush_all()
