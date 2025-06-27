/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

// Patch del FormController per aggiungere testo ai pulsanti
patch(FormController.prototype, {
    
    setup() {
        super.setup();
        // Attende il rendering completo prima di aggiungere i testi
        this.env.bus.addEventListener("DOM_UPDATED", () => {
            this._addButtonTexts();
        });
    },

    /**
     * Aggiunge testo ai pulsanti di azione del modulo
     * @private
     */
    _addButtonTexts() {
        // Attende un piccolo ritardo per garantire che il DOM sia pronto
        setTimeout(() => {
            this._addSaveButtonText();
            this._addDiscardButtonText();
            this._addActionsButtonText();
        }, 100);
    },

    /**
     * Aggiunge testo al pulsante Salva
     * @private
     */
    _addSaveButtonText() {
        const saveButton = document.querySelector('.o_form_status_indicator_buttons .o_form_button_save');
        if (saveButton && !saveButton.querySelector('.button-text')) {
            const textSpan = document.createElement('span');
            textSpan.className = 'button-text ms-2';
            textSpan.textContent = 'Salva manualmente';
            textSpan.style.fontSize = '12px';
            textSpan.style.fontWeight = '500';
            textSpan.style.color = '#6c757d';
            saveButton.appendChild(textSpan);
        }
    },

    /**
     * Aggiunge testo al pulsante Scarta
     * @private
     */
    _addDiscardButtonText() {
        const discardButton = document.querySelector('.o_form_status_indicator_buttons .o_form_button_cancel');
        if (discardButton && !discardButton.querySelector('.button-text')) {
            const textSpan = document.createElement('span');
            textSpan.className = 'button-text ms-2';
            textSpan.textContent = 'Scarta tutte le modifiche';
            textSpan.style.fontSize = '12px';
            textSpan.style.fontWeight = '500';
            textSpan.style.color = '#6c757d';
            discardButton.appendChild(textSpan);
        }
    },

    /**
     * Aggiunge testo al pulsante Azioni
     * @private
     */
    _addActionsButtonText() {
        const actionsButton = document.querySelector('.o_cp_action_menus .btn');
        if (actionsButton && !actionsButton.querySelector('.button-text')) {
            const textSpan = document.createElement('span');
            textSpan.className = 'button-text ms-2';
            textSpan.textContent = 'Azioni';
            textSpan.style.fontSize = '12px';
            textSpan.style.fontWeight = '500';
            textSpan.style.color = '#6c757d';
            actionsButton.appendChild(textSpan);
        }
    },
}); 