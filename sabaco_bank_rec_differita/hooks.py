from odoo import _
from odoo.exceptions import UserError

MODULO_INCOMPATIBILE = 'bank_rec_deferred_dates'


def pre_init_hook(env):
    # bank_rec_deferred_dates definisce gli stessi campi sulla riga del widget e
    # modifica lo stesso template: i due moduli non possono convivere.
    incompatibile = env['ir.module.module'].search([
        ('name', '=', MODULO_INCOMPATIBILE),
        ('state', 'in', ('installed', 'to install', 'to upgrade')),
    ])
    if incompatibile:
        raise UserError(_(
            "Il modulo %s è installato ed è incompatibile con la data differita nelle transazioni "
            "bancarie. Disinstallarlo prima di installare questo modulo.",
            MODULO_INCOMPATIBILE,
        ))
