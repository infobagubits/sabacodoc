/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import BarcodePickingModel from "@stock_barcode/models/barcode_picking_model";

/**
 * Patch do BarcodePickingModel para:
 * 1. Resolver move_id como objeto completo, permitindo acesso aos campos de stock.move
 * 2. Mostrare tutti i prodotti dell'ordine, anche quelli non disponibili
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

    /**
     * Cria dados de linha a partir de um stock.move (para produtos sem move_line)
     */
    _getMoveData(moveId) {
        const move = this.cache.getRecord('stock.move', moveId);
        if (!move) {
            return null;
        }

        // Verifica se já existe uma linha para este move
        const existingLine = this.currentState?.lines.find(line => 
            line.move_id && (line.move_id.id === moveId || line.move_id === moveId)
        );
        
        // Obtém product_uom_id do produto se não estiver disponível no move
        const product = this.cache.getRecord('product.product', move.product_id);
        const productUomId = product?.uom_id || move.product_uom || move.product_id?.uom_id;
        
        // Cria dados de linha virtual a partir do move
        const lineData = {
            id: null, // Não tem ID porque não existe move_line ainda
            virtual_id: existingLine?.virtual_id || this._uniqueVirtualId,
            move_id: move,
            product_id: product,
            product_uom_id: this.cache.getRecord('uom.uom', productUomId),
            location_id: this.cache.getRecord('stock.location', move.location_id),
            location_dest_id: this.cache.getRecord('stock.location', move.location_dest_id),
            quantity: move.product_uom_qty || 0,
            qty_done: 0,
            picked: false,
            reserved_uom_qty: 0, // Não tem reserva porque não tem estoque disponível
            lot_id: null,
            lot_name: null,
            owner_id: null,
            package_id: null,
            result_package_id: null,
            product_packaging_id: null,
            dummy_id: null,
            sortIndex: existingLine?.sortIndex,
        };

        return lineData;
    },

    /**
     * Estende _createLinesState para incluir produtos de move_ids que não têm move_line_ids
     * Mostra TODOS os produtos do pedido, mesmo os sem estoque disponível
     */
    _createLinesState() {
        const lines = [];
        const picking = this.cache.getRecord(this.resModel, this.resId);
        
        // 1. Adiciona todas as linhas existentes (move_line_ids)
        for (const id of picking.move_line_ids) {
            const smlData = this._getMoveLineData(id);
            lines.push(smlData);
        }

        // 2. Adiciona produtos de move_ids que não têm move_line_ids correspondentes
        const existingMoveIds = new Set();
        for (const line of lines) {
            if (line.move_id) {
                const moveId = typeof line.move_id === 'object' ? line.move_id.id : line.move_id;
                if (moveId) {
                    existingMoveIds.add(moveId);
                }
            }
        }

        // Itera sobre todos os moves do picking
        for (const moveId of picking.move_ids || []) {
            // Se este move não tem move_line correspondente, cria uma linha virtual
            if (!existingMoveIds.has(moveId)) {
                const moveData = this._getMoveData(moveId);
                if (moveData) {
                    lines.push(moveData);
                }
            }
        }

        return lines;
    },

    /**
     * Estende _getNewLineDefaultValues para garantir que linhas virtuais (sem move_line)
     * tenham o move_id configurado corretamente quando editadas
     */
    _getNewLineDefaultValues(fieldsParams) {
        const defaultValues = super._getNewLineDefaultValues(...arguments);
        
        // Se a linha selecionada não tem ID (é virtual) mas tem move_id, usa esse move_id
        if (this.selectedLine && !this.selectedLine.id && this.selectedLine.move_id) {
            const moveId = typeof this.selectedLine.move_id === 'object' 
                ? this.selectedLine.move_id.id 
                : this.selectedLine.move_id;
            if (moveId && !fieldsParams.move_id) {
                defaultValues.move_id = moveId;
            }
        }
        
        return defaultValues;
    },
});

