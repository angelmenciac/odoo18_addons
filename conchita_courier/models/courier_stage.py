# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CourierStage(models.Model):
    _name = 'courier.stage'
    _description = 'Estado de Envío'
    _order = 'sequence, id'

    name = fields.Char(
        string='Estado',
        required=True,
        translate=True,
    )
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
    )
    code = fields.Selection([
        ('draft', 'Borrador'),
        ('received', 'Recibido en Bodega'),
        ('in_transit', 'En Tránsito'),
        ('out_delivery', 'En Reparto'),
        ('delivered', 'Entregado'),
        ('cancelled', 'Cancelado'),
        ('returned', 'Devuelto'),
    ], string='Código de Estado', required=True, default='draft')
    description = fields.Text(string='Descripción')
    fold = fields.Boolean(
        string='Plegado en Kanban',
        default=False,
    )
    is_final = fields.Boolean(
        string='Estado Final',
        default=False,
        help='Indica que el envío ha concluido (entregado, cancelado, devuelto)',
    )
    color = fields.Integer(string='Color', default=0)
    # Email template para notificaciones automáticas al cambiar a este estado
    mail_template_id = fields.Many2one(
        'mail.template',
        string='Plantilla de Correo',
        domain=[('model', '=', 'courier.request')],
        help='Se enviará este correo automáticamente cuando el envío llegue a este estado',
    )
    # Notificar al destinatario también
    notify_recipient = fields.Boolean(
        string='Notificar al Destinatario',
        default=False,
        help='Además del remitente, notifica al destinatario del paquete',
    )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)',
         'Ya existe un estado con ese código. Cada código debe ser único.'),
    ]
