# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Campo para marcar que este contacto es un destinatario privado
    # Solo visible para el cliente propietario (courier_owner_id)
    is_courier_recipient = fields.Boolean(
        string='Es Destinatario de Envíos',
        default=False,
        help='Marca este contacto como destinatario de envíos de Transporte Conchita',
    )

    # El cliente (empresa) dueño de este destinatario
    # Si está vacío, es un destinatario público/compartido
    courier_owner_id = fields.Many2one(
        'res.partner',
        string='Cliente Propietario del Destinatario',
        help='Si se establece, este destinatario solo será visible para este cliente',
        domain=[('customer_rank', '>', 0)],
        ondelete='set null',
    )

    # Número de envíos como destinatario
    recipient_courier_count = fields.Integer(
        string='Envíos Recibidos',
        compute='_compute_recipient_courier_count',
    )

    @api.depends()
    def _compute_recipient_courier_count(self):
        for partner in self:
            partner.recipient_courier_count = self.env['courier.request'].search_count([
                ('recipient_id', '=', partner.id)
            ])

    @api.model
    def get_my_recipients(self, partner_id):
        """
        Retorna los destinatarios disponibles para un cliente:
        - Sus destinatarios privados (courier_owner_id = partner_id)
        - Destinatarios públicos (courier_owner_id = False, is_courier_recipient = True)
        """
        return self.search([
            '|',
            ('courier_owner_id', '=', partner_id),
            '&',
            ('courier_owner_id', '=', False),
            ('is_courier_recipient', '=', True),
        ])
