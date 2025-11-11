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
        if (!product) {
            return null;
        }
        
        const productUomId = product.uom_id || move.product_uom;
        const productUom = productUomId ? this.cache.getRecord('uom.uom', productUomId) : null;
        
        // Obtém location_id e location_dest_id - devem ser objetos válidos para ordenação
        const locationId = this.cache.getRecord('stock.location', move.location_id);
        const locationDestId = this.cache.getRecord('stock.location', move.location_dest_id);
        
        // Garante que location_id não seja null (necessário para ordenação)
        if (!locationId) {
            return null;
        }
        
        // Cria dados de linha virtual a partir do move
        const lineData = {
            id: null, // Não tem ID porque não existe move_line ainda
            virtual_id: existingLine?.virtual_id || this._uniqueVirtualId,
            move_id: move,
            product_id: product,
            product_uom_id: productUom,
            location_id: locationId,
            location_dest_id: locationDestId || null,
            quantity: move.product_uom_qty || 0,
            qty_done: 0,
            picked: false,
            reserved_uom_qty: 0, // Não tem reserva porque não tem estoque disponível
            lot_id: null,
            lot_name: null,
            owner_id: null,
            package_id: null, // null é OK, o sortingMethod verifica isso
            result_package_id: null, // null é OK, o sortingMethod verifica isso
            product_packaging_id: null,
            dummy_id: null,
            product_category_name: product.categ_id?.complete_name || product.category_name || '',
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

    /**
     * Estende _sortingMethod para lidar com valores null nas linhas virtuais
     */
    _sortingMethod(l1, l2) {
        // Sort by source location - proteção contra null
        const sourceLocation1 = l1.location_id?.display_name || '';
        const sourceLocation2 = l2.location_id?.display_name || '';
        if (sourceLocation1 < sourceLocation2) {
            return -1;
        } else if (sourceLocation1 > sourceLocation2) {
            return 1;
        }
        // Sort by (source) package - proteção contra null
        const package1 = l1.package_id?.name || '';
        const package2 = l2.package_id?.name || '';
        if (package1 < package2) {
            return -1;
        } else if (package1 > package2) {
            return 1;
        }
        // Sort by destination location - já tem verificação de null
        if (l1.location_dest_id && l2.location_dest_id) {
            const destinationLocation1 = l1.location_dest_id.display_name || '';
            const destinationLocation2 = l2.location_dest_id.display_name || '';
            if (destinationLocation1 < destinationLocation2) {
                return -1;
            } else if (destinationLocation1 > destinationLocation2) {
                return 1;
            }
        }
        // Sort by result package - já tem verificação de null
        if (l1.result_package_id && l2.result_package_id) {
            const resultPackage1 = l1.result_package_id.name || '';
            const resultPackage2 = l2.result_package_id.name || '';
            if (resultPackage1 < resultPackage2) {
                return -1;
            } else if (resultPackage1 > resultPackage2) {
                return 1;
            }
        }
        // Sort by product's category - proteção contra null
        const categ1 = l1.product_category_name || '';
        const categ2 = l2.product_category_name || '';
        if (categ1 < categ2) {
            return -1;
        } else if (categ1 > categ2) {
            return 1;
        }
        // Sort by product's display name - proteção contra null
        const product1 = l1.product_id?.display_name || '';
        const product2 = l2.product_id?.display_name || '';
        if (product1 < product2) {
            return -1;
        } else if (product1 > product2) {
            return 1;
        }
        return 0;
    },
});

