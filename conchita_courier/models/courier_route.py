# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CourierRoute(models.Model):
    _name = 'courier.route'
    _description = 'Zona / Ruta de Entrega'
    _order = 'name'

    name = fields.Char(string='Nombre de Zona', required=True)
    code = fields.Char(string='Código', size=10)
    description = fields.Text(string='Ciudades / Municipios incluidos')
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color', default=0)

    # Días estimados de entrega
    delivery_days = fields.Integer(
        string='Días Estimados de Entrega',
        default=1,
    )

    # Precio base de la zona (puede sobreescribirse por reglas de peso)
    base_price = fields.Float(
        string='Precio Base (L.)',
        digits=(10, 2),
        default=0.0,
    )

    # Relación con reglas de precio específicas de esta zona
    price_rule_ids = fields.One2many(
        'courier.price.rule',
        'route_id',
        string='Reglas de Precio',
    )

    # Motoristas habituales de esta ruta
    driver_ids = fields.Many2many(
        'courier.driver',
        'route_driver_rel',
        'route_id',
        'driver_id',
        string='Motoristas de esta Ruta',
    )

    courier_count = fields.Integer(
        string='Envíos',
        compute='_compute_courier_count',
    )

    @api.depends()
    def _compute_courier_count(self):
        for rec in self:
            rec.courier_count = self.env['courier.request'].search_count([
                ('route_id', '=', rec.id)
            ])

    def action_view_couriers(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Envíos — {self.name}',
            'res_model': 'courier.request',
            'view_mode': 'list,form',
            'domain': [('route_id', '=', self.id)],
            'context': {'default_route_id': self.id},
        }
