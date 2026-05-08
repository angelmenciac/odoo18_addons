# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Marca este contacto como destinatario de envíos
    is_courier_recipient = fields.Boolean(
        string='Es Destinatario de Envíos',
        default=False,
        help='Marca este contacto como destinatario de envíos de Transporte Conchita',
    )

    # Many2many: un destinatario puede ser compartido entre varios clientes.
    # Si está vacío → destinatario PÚBLICO (visible para todos los clientes).
    # Si tiene clientes → destinatario PRIVADO/COMPARTIDO (visible solo para esos clientes).
    courier_owner_ids = fields.Many2many(
        'res.partner',
        'courier_recipient_owner_rel',
        'recipient_id',
        'owner_id',
        string='Clientes con acceso',
        domain=[('customer_rank', '>', 0)],
        help='Clientes que pueden ver y usar este destinatario. '
             'Si está vacío, es público para todos los clientes.',
    )

    # Computed: indica si es público (sin clientes asignados)
    is_public_recipient = fields.Boolean(
        string='Destinatario Público',
        compute='_compute_is_public_recipient',
        store=True,
    )

    # Número de envíos como destinatario
    recipient_courier_count = fields.Integer(
        string='Envíos Recibidos',
        compute='_compute_recipient_courier_count',
    )

    @api.depends('courier_owner_ids', 'is_courier_recipient')
    def _compute_is_public_recipient(self):
        for partner in self:
            partner.is_public_recipient = (
                partner.is_courier_recipient
                and not partner.courier_owner_ids
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
        - Sus destinatarios privados/compartidos (partner_id en courier_owner_ids)
        - Destinatarios públicos (courier_owner_ids vacío, is_courier_recipient=True)
        """
        return self.search([
            ('is_courier_recipient', '=', True),
            '|',
            ('courier_owner_ids', 'in', [partner_id]),
            ('courier_owner_ids', '=', False),
        ])
