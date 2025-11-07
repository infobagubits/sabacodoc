/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import BarcodePickingModel from "@stock_barcode/models/barcode_picking_model";

/**
 * Patch do BarcodePickingModel para resolver move_id como objeto completo,
 * permitindo acesso aos campos de stock.move (como x_studio_confezioni_richieste)
 */
patch(BarcodePickingModel.prototype, {
    _getMoveLineData(id) {
        const smlData = super._getMoveLineData(...arguments);
        // Resolve move_id como objeto completo do cache para acessar seus campos
        if (smlData.move_id) {
            smlData.move_id = this.cache.getRecord('stock.move', smlData.move_id);
        }
        return smlData;
    },
});

