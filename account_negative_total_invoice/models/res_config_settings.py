from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    allow_negative_total_invoice = fields.Boolean(
        related="company_id.allow_negative_total_invoice",
        readonly=False,
    )
