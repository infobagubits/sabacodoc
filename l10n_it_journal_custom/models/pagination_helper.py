from odoo import api, models


class PaginationHelper(models.AbstractModel):
    _name = 'pagination.helper'
    _description = 'Helper per numerazione dinamica delle pagine nei report italiani'

    @api.model
    def get_page_offset(self):
        """
        Restituisce l'offset delle pagine basato sulla configurazione di sistema
        """
        config = self.env['ir.config_parameter'].sudo()
        offset = int(config.get_param('l10n_it_custom.page_offset', '0'))
        return offset

    @api.model
    def calculate_page_number(self, current_page, total_pages):
        """
        Calcola il numero della pagina con offset personalizzato
        
        :param current_page: Numero pagina corrente
        :param total_pages: Numero totale di pagine
        :return: Tupla (pagina_corrente_personalizzata, totale_pagine_personalizzato)
        """
        offset = self.get_page_offset()
        
        # Se ha offset configurato, applicalo
        if offset > 0:
            custom_current = current_page + offset - 1
            custom_total = total_pages + offset - 1
            return custom_current, custom_total
        
        # Altrimenti, usa numerazione standard
        return current_page, total_pages

    @api.model
    def format_page_display(self, current_page, total_pages):
        """
        Formatta la visualizzazione della pagina per i report (es: "12/15")
        
        :param current_page: Numero pagina corrente
        :param total_pages: Numero totale di pagine
        :return: Stringa formattata "pagina_corrente/totale_pagine"
        """
        custom_current, custom_total = self.calculate_page_number(current_page, total_pages)
        return f"{custom_current}/{custom_total}"

    @api.model
    def get_current_page_js(self):
        """
        Restituisce codice JavaScript per rilevare la pagina corrente e applicare offset
        Utilizzato nei template QWeb per la numerazione dinamica
        
        :return: Codice JavaScript come stringa
        """
        offset = self.get_page_offset()
        if offset > 0:
            return f"""
            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    // Rileva pagina corrente e applica offset personalizzato
                    const pageSpan = document.querySelector('.page');
                    const topageSpan = document.querySelector('.topage');
                    
                    if (pageSpan && topageSpan) {{
                        const currentPage = parseInt(pageSpan.textContent) || 1;
                        const totalPages = parseInt(topageSpan.textContent) || 1;
                        
                        // Applica offset: pagina corrente + offset - 1
                        pageSpan.textContent = currentPage + {offset - 1};
                        topageSpan.textContent = totalPages + {offset - 1};
                    }}
                }});
            </script>
            """
        return "" 