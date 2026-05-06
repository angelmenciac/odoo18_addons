# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CourierDriver(models.Model):
    _name = 'courier.driver'
    _description = 'Motorista / Conductor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Nombre Completo', required=True, tracking=True)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado Relacionado',
        help='Vincula este motorista con su registro de empleado en RRHH',
    )
    phone = fields.Char(string='Teléfono / WhatsApp', tracking=True)
    license_plate = fields.Char(string='Placa del Vehículo', tracking=True)
    vehicle_type = fields.Selection([
        ('moto', 'Motocicleta'),
        ('pickup', 'Pickup'),
        ('van', 'Van / Camioneta'),
        ('truck', 'Camión'),
    ], string='Tipo de Vehículo', default='moto')
    active = fields.Boolean(default=True, tracking=True)
    note = fields.Text(string='Notas')

    # Zonas asignadas habitualmente
    route_ids = fields.Many2many(
        'courier.route',
        'route_driver_rel',
        'driver_id',
        'route_id',
        string='Zonas Habituales',
    )

    # Estadísticas
    delivery_count = fields.Integer(
        string='Envíos Realizados',
        compute='_compute_delivery_count',
    )
    pending_count = fields.Integer(
        string='Envíos Pendientes',
        compute='_compute_delivery_count',
    )

    @api.depends()
    def _compute_delivery_count(self):
        for driver in self:
            all_requests = self.env['courier.request'].search([
                ('driver_id', '=', driver.id)
            ])
            driver.delivery_count = len(all_requests.filtered(
                lambda r: r.stage_id.code == 'delivered'
            ))
            driver.pending_count = len(all_requests.filtered(
                lambda r: r.stage_id.code in ('in_transit', 'out_delivery')
            ))

    def action_view_deliveries(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Envíos de {self.name}',
            'res_model': 'courier.request',
            'view_mode': 'list,form',
            'domain': [('driver_id', '=', self.id)],
        }
