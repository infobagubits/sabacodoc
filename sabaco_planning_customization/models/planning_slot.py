from odoo import api, models


class PlanningSlot(models.Model):
    _inherit = 'planning.slot'

    @api.onchange('role_id')
    def _onchange_role_id_filter_resource(self):
        if (
            self.resource_id
            and self.role_id
            and self.role_id not in self.resource_id.role_ids
        ):
            self.resource_id = False
