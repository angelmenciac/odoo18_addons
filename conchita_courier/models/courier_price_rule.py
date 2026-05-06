# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CourierPriceRule(models.Model):
    _name = 'courier.price.rule'
    _description = 'Regla de Precio de Envío'
    _order = 'route_id, weight_from'

    name = fields.Char(string='Descripción', compute='_compute_name', store=True)
    route_id = fields.Many2one(
        'courier.route',
        string='Zona / Ruta',
        required=True,
        ondelete='cascade',
    )

    # Tipo de regla
    rule_type = fields.Selection([
        ('weight', 'Por Peso'),
        ('weight_zone', 'Por Peso + Zona'),
    ], string='Tipo de Regla', required=True, default='weight_zone')

    # Rango de peso
    weight_from = fields.Float(string='Peso Desde (kg)', default=0.0)
    weight_to = fields.Float(string='Peso Hasta (kg)', default=5.0)

    # Precio para esta regla
    price = fields.Float(string='Precio (L.)', required=True, digits=(10, 2))

    # Precio especial por cliente (sobrescribe el precio base)
    partner_price_ids = fields.One2many(
        'courier.partner.price',
        'rule_id',
        string='Precios Especiales por Cliente',
    )

    active = fields.Boolean(default=True)

    @api.depends('route_id', 'weight_from', 'weight_to', 'price')
    def _compute_name(self):
        for rec in self:
            if rec.route_id:
                rec.name = (
                    f"{rec.route_id.name} | "
                    f"{rec.weight_from}–{rec.weight_to} kg | "
                    f"L. {rec.price:.2f}"
                )
            else:
                rec.name = f"{rec.weight_from}–{rec.weight_to} kg | L. {rec.price:.2f}"

    @api.constrains('weight_from', 'weight_to')
    def _check_weights(self):
        for rec in self:
            if rec.weight_from < 0:
                raise ValidationError('El peso mínimo no puede ser negativo.')
            if rec.weight_to <= rec.weight_from:
                raise ValidationError(
                    'El peso máximo debe ser mayor que el peso mínimo.'
                )

    def get_price_for_partner(self, partner_id):
        """Retorna el precio específico para un cliente, o el precio base."""
        self.ensure_one()
        special = self.partner_price_ids.filtered(
            lambda p: p.partner_id.id == partner_id
        )
        if special:
            return special[0].price
        return self.price


class CourierPartnerPrice(models.Model):
    """Precios especiales negociados por cliente para una ruta/peso específicos."""
    _name = 'courier.partner.price'
    _description = 'Precio Especial por Cliente'

    rule_id = fields.Many2one(
        'courier.price.rule',
        string='Regla de Precio',
        required=True,
        ondelete='cascade',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        domain=[('customer_rank', '>', 0)],
    )
    price = fields.Float(
        string='Precio Especial (L.)',
        required=True,
        digits=(10, 2),
    )
    note = fields.Char(string='Nota / Contrato')

    _sql_constraints = [
        ('rule_partner_unique', 'UNIQUE(rule_id, partner_id)',
         'Ya existe un precio especial para este cliente en esta regla.'),
    ]
