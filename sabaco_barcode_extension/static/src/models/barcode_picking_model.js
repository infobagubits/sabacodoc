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
            // CORREZIONE: Mantém la quantità specifica della move_line, non la quantità totale del move
            // Ogni lotto ha la sua quantità propria (es: lotto1=3, lotto2=6, lotto3=3)
            // NON sobrescreve smlData.quantity con move.product_uom_qty
            // La quantità di smlData viene dal server ed è corretta per ogni move_line
        }
        // Garante que product_uom_id seja sempre um objeto válido (não null)
        // Isso pode acontecer se o cache não tiver o registro ainda
        if (!smlData.product_uom_id && smlData.product_id) {
            const product = this.cache.getRecord('product.product', smlData.product_id);
            if (product && product.uom_id) {
                smlData.product_uom_id = this.cache.getRecord('uom.uom', product.uom_id);
            }
        }
        // Garante que location_dest_id seja sempre um objeto válido
        if (!smlData.location_dest_id && smlData.location_id) {
            smlData.location_dest_id = smlData.location_id;
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
        
        // Obtém product_uom_id - prioriza move.product_uom, depois product.uom_id
        const productUomId = move.product_uom || product.uom_id;
        if (!productUomId) {
            return null; // Não pode criar linha sem UOM
        }
        const productUom = this.cache.getRecord('uom.uom', productUomId);
        if (!productUom) {
            return null; // Não pode criar linha sem UOM válido
        }
        
        // Obtém location_id e location_dest_id - devem ser objetos válidos para ordenação
        const locationId = this.cache.getRecord('stock.location', move.location_id);
        const locationDestId = this.cache.getRecord('stock.location', move.location_dest_id);
        
        // Garante que location_id não seja null (necessário para ordenação)
        if (!locationId) {
            return null;
        }
        
        // Garante que location_dest_id seja sempre um objeto válido (necessário para template)
        // Se não existir no cache, usa location_id como fallback
        const validLocationDestId = locationDestId || locationId;
        
        // Cria dados de linha virtual a partir do move
        // Usa virtual_id como dummy_id para permitir que a linha seja encontrada em onOpenProductPage
        const virtualId = existingLine?.virtual_id || this._uniqueVirtualId;
        const lineData = {
            id: null, // Não tem ID porque não existe move_line ainda
            virtual_id: virtualId,
            dummy_id: virtualId, // Usa virtual_id como dummy_id para permitir busca em onOpenProductPage
            move_id: move,
            product_id: product,
            product_uom_id: productUom, // Sempre um objeto válido (não null)
            location_id: locationId,
            location_dest_id: validLocationDestId, // Sempre um objeto válido (não null)
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
        
        if (!picking) {
            return lines;
        }
        
        // 1. Adiciona todas as linhas existentes (move_line_ids)
        for (const id of picking.move_line_ids || []) {
            const smlData = this._getMoveLineData(id);
            if (smlData) {
                lines.push(smlData);
            }
        }

        // 2. Adiciona produtos de move_ids que não têm move_line_ids correspondentes
        // Normaliza move_ids para garantir comparação correta
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
        // Normaliza moveId para garantir comparação correta (pode ser objeto ou número)
        for (const moveIdRaw of picking.move_ids || []) {
            // Normaliza moveId: pode ser objeto (com .id) ou número direto
            const moveId = typeof moveIdRaw === 'object' ? moveIdRaw.id : moveIdRaw;
            
            // Se este move não tem move_line correspondente, cria uma linha virtual
            if (moveId && !existingMoveIds.has(moveId)) {
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
     * Estende getEditedLineParams para lidar com linhas virtuais (sem id)
     * Retorna null como currentId se a linha não tiver id, permitindo criar nova linha
     * Também armazena a linha para uso no contexto
     */
    getEditedLineParams(line) {
        // Armazena a linha atual para uso no contexto
        this._currentEditedLine = line;
        // Se a linha não tem id (é virtual), retorna null para permitir criar nova linha
        if (!line || !line.id) {
            return { currentId: null, isVirtual: true };
        }
        return super.getEditedLineParams(...arguments);
    },

    /**
     * Limpa a referência da linha editada quando necessário
     */
    displayBarcodeLines(lineId) {
        // Limpa a referência da linha editada
        this._currentEditedLine = null;
        return super.displayBarcodeLines(...arguments);
    },

    /**
     * Estende _getNewLineDefaultContext para incluir dados da linha virtual quando editada
     */
    _getNewLineDefaultContext() {
        const context = super._getNewLineDefaultContext(...arguments);
        
        // Se estamos editando uma linha virtual (sem id), adiciona os dados da linha ao contexto
        if (this._currentEditedLine && !this._currentEditedLine.id) {
            const line = this._currentEditedLine;
            
            // Adiciona product_id se disponível
            if (line.product_id && line.product_id.id) {
                context.default_product_id = line.product_id.id;
            }
            
            // Adiciona move_id se disponível
            if (line.move_id) {
                const moveId = typeof line.move_id === 'object' ? line.move_id.id : line.move_id;
                if (moveId) {
                    context.default_move_id = moveId;
                }
            }
            
            // Adiciona location_id se disponível (sobrescreve o padrão)
            if (line.location_id && line.location_id.id) {
                context.default_location_id = line.location_id.id;
            }
            
            // Adiciona location_dest_id se disponível (sobrescreve o padrão)
            if (line.location_dest_id && line.location_dest_id.id) {
                context.default_location_dest_id = line.location_dest_id.id;
            }
            
            // Adiciona product_uom_id se disponível
            if (line.product_uom_id && line.product_uom_id.id) {
                context.default_product_uom_id = line.product_uom_id.id;
            }
            
            // Adiciona quantity se disponível (como qty_done inicial)
            if (line.quantity !== undefined && line.quantity > 0) {
                context.default_qty_done = line.quantity;
                context.default_quantity = line.quantity;
            }
        }
        
        return context;
    },

    /**
     * Sobrescreve getQtyDemand para retornar a quantidade ESPECÍFICA de cada move_line
     * (não a quantidade total do transferimento)
     * Se o produto tem 3 lotti (3, 6, 3) PZ, deve mostrare 3, 6, 3 rispettivamente
     */
    getQtyDemand(line) {
        // Retorna a quantidade específica da move_line do servidor
        // Usa o método padrão que já retorna corretamente a quantidade de cada linha
        return super.getQtyDemand(...arguments);
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

