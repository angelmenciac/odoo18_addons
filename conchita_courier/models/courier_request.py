# -*- coding: utf-8 -*-
import base64
import qrcode
import io
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class CourierRequest(models.Model):
    _name = 'courier.request'
    _description = 'Solicitud de Envío / Encomienda'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'date_request desc, id desc'
    _rec_name = 'name'

    # ── Identificación ────────────────────────────────────────────────────────
    name = fields.Char(
        string='Número de Guía',
        readonly=True,
        copy=False,
        default='Nuevo',
        tracking=True,
    )

    # ── Fechas ────────────────────────────────────────────────────────────────
    date_request = fields.Datetime(
        string='Fecha de Solicitud',
        default=fields.Datetime.now,
        required=True,
        tracking=True,
    )
    date_received = fields.Datetime(
        string='Fecha de Recepción en Bodega',
        tracking=True,
    )
    date_dispatched = fields.Datetime(
        string='Fecha de Despacho',
        tracking=True,
    )
    date_delivered = fields.Datetime(
        string='Fecha de Entrega',
        tracking=True,
    )
    estimated_delivery_date = fields.Date(
        string='Fecha Estimada de Entrega',
        compute='_compute_estimated_delivery',
        store=True,
    )

    # ── Estado ────────────────────────────────────────────────────────────────
    stage_id = fields.Many2one(
        'courier.stage',
        string='Estado',
        required=True,
        default=lambda self: self._default_stage(),
        tracking=True,
        group_expand='_read_group_stage_ids',
        copy=False,
    )
    # Campo auxiliar para decoradores de vista lista/kanban
    # Odoo 18 no permite stage_id.code directamente en decoration-*
    stage_code = fields.Selection(
        related='stage_id.code',
        string='Código de Estado',
        store=True,
        readonly=True,
    )
    kanban_state = fields.Selection([
        ('normal', 'En Proceso'),
        ('done', 'Listo'),
        ('blocked', 'Bloqueado'),
    ], string='Estado Kanban', default='normal', tracking=True)

    # ── Remitente (cliente de Transporte Conchita) ────────────────────────────
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente / Remitente',
        required=True,
        tracking=True,
        domain=[('customer_rank', '>', 0)],
    )
    sender_name = fields.Char(
        string='Nombre Remitente',
        related='partner_id.name',
        store=True,
    )
    sender_phone = fields.Char(
        string='Teléfono Remitente',
        related='partner_id.phone',
        store=True,
    )
    sender_address = fields.Char(
        string='Dirección Remitente',
        compute='_compute_sender_address',
        store=True,
    )

    # ── Destinatario ─────────────────────────────────────────────────────────
    recipient_id = fields.Many2one(
        'res.partner',
        string='Destinatario',
        required=True,
        tracking=True,
        domain="[('is_courier_recipient', '=', True), '|', ('courier_owner_ids', 'in', [partner_id]), ('courier_owner_ids', '=', False)]",
        help='Selecciona un destinatario existente o crea uno nuevo',
    )
    recipient_name = fields.Char(
        string='Nombre Destinatario',
        related='recipient_id.name',
        store=True,
    )
    recipient_phone = fields.Char(
        string='Teléfono Destinatario',
        related='recipient_id.phone',
        store=True,
    )
    recipient_address = fields.Char(
        string='Dirección de Entrega',
        tracking=True,
        help='Dirección exacta de entrega (colonia, calle, referencia)',
    )
    recipient_city = fields.Char(
        string='Ciudad Destino',
        tracking=True,
    )

    # ── Ruta y Motorista ──────────────────────────────────────────────────────
    route_id = fields.Many2one(
        'courier.route',
        string='Zona de Entrega',
        required=True,
        tracking=True,
    )
    driver_id = fields.Many2one(
        'courier.driver',
        string='Motorista Asignado',
        tracking=True,
        domain="[('route_ids', 'in', route_id)]",
    )

    # ── Detalles del Paquete ──────────────────────────────────────────────────
    package_description = fields.Text(
        string='Descripción del Contenido',
        required=True,
    )
    package_type = fields.Selection([
        ('sobre', 'Sobre / Documentos'),
        ('caja_pequena', 'Caja Pequeña'),
        ('caja_mediana', 'Caja Mediana'),
        ('caja_grande', 'Caja Grande'),
        ('paquete', 'Paquete Irregular'),
        ('fragil', 'Paquete Frágil'),
        ('refrigerado', 'Refrigerado'),
        ('otro', 'Otro'),
    ], string='Tipo de Paquete', default='caja_pequena', required=True)
    weight = fields.Float(
        string='Peso (kg)',
        digits=(10, 3),
        default=1.0,
        required=True,
        tracking=True,
    )
    dimension_length = fields.Float(string='Largo (cm)', digits=(10, 1))
    dimension_width = fields.Float(string='Ancho (cm)', digits=(10, 1))
    dimension_height = fields.Float(string='Alto (cm)', digits=(10, 1))
    declared_value = fields.Float(
        string='Valor Declarado (L.)',
        digits=(10, 2),
        default=0.0,
        help='Valor declarado del contenido para efectos de seguro',
    )
    is_fragile = fields.Boolean(string='Frágil', default=False)
    requires_refrigeration = fields.Boolean(string='Requiere Refrigeración', default=False)
    special_instructions = fields.Text(string='Instrucciones Especiales')

    # ── Imágenes del Paquete ──────────────────────────────────────────────────
    image_1 = fields.Binary(string='Foto del Paquete 1', attachment=True)
    image_2 = fields.Binary(string='Foto del Paquete 2', attachment=True)
    image_3 = fields.Binary(string='Foto del Paquete 3', attachment=True)

    # ── Firma Digital ─────────────────────────────────────────────────────────
    signature = fields.Binary(string='Firma del Remitente', attachment=True)
    signature_name = fields.Char(string='Nombre Firmante')
    delivery_signature = fields.Binary(
        string='Firma de Recepción (Destinatario)',
        attachment=True,
    )
    delivery_signature_name = fields.Char(string='Nombre de quien recibe')

    # ── Precios ───────────────────────────────────────────────────────────────
    price_rule_id = fields.Many2one(
        'courier.price.rule',
        string='Regla de Precio Aplicada',
        compute='_compute_price',
        store=True,
    )
    base_amount = fields.Float(
        string='Tarifa Base (L.)',
        digits=(10, 2),
        compute='_compute_price',
        store=True,
        tracking=True,
    )
    additional_charges = fields.Float(
        string='Cargos Adicionales (L.)',
        digits=(10, 2),
        default=0.0,
        tracking=True,
    )
    additional_charges_note = fields.Char(string='Concepto de Cargos Adicionales')
    discount_amount = fields.Float(
        string='Descuento (L.)',
        digits=(10, 2),
        default=0.0,
    )
    total_amount = fields.Float(
        string='Total (L.)',
        digits=(10, 2),
        compute='_compute_total',
        store=True,
        tracking=True,
    )

    # ── Facturación ───────────────────────────────────────────────────────────
    invoice_id = fields.Many2one(
        'account.move',
        string='Factura',
        copy=False,
        tracking=True,
    )
    invoice_state = fields.Selection(
        related='invoice_id.state',
        string='Estado de Factura',
        store=True,
    )
    is_invoiced = fields.Boolean(
        string='Facturado',
        compute='_compute_is_invoiced',
        store=True,
    )

    # ── QR Code ───────────────────────────────────────────────────────────────
    qr_code = fields.Binary(
        string='Código QR',
        compute='_compute_qr_code',
        store=True,
        attachment=True,
    )

    # ── Calificación del Servicio ─────────────────────────────────────────────
    rating_value = fields.Selection([
        ('1', '⭐ Muy Malo'),
        ('2', '⭐⭐ Malo'),
        ('3', '⭐⭐⭐ Regular'),
        ('4', '⭐⭐⭐⭐ Bueno'),
        ('5', '⭐⭐⭐⭐⭐ Excelente'),
    ], string='Calificación', tracking=True)
    rating_feedback = fields.Text(string='Comentario del Cliente')
    rating_date = fields.Datetime(string='Fecha de Calificación')

    # ── Portal ────────────────────────────────────────────────────────────────
    access_token = fields.Char(
        string='Token de Acceso',
        copy=False,
    )

    # ────────────────────────────────────────────────────────────────────────
    # Defaults y métodos del ORM
    # ────────────────────────────────────────────────────────────────────────

    def _default_stage(self):
        stage = self.env['courier.stage'].search(
            [('code', '=', 'draft')], limit=1
        )
        return stage.id if stage else False

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return self.env['courier.stage'].search([], order='sequence, id')

    # ── onchange: al seleccionar destinatario, autocompleta dirección y ciudad ──
    @api.onchange('recipient_id')
    def _onchange_recipient_id(self):
        if self.recipient_id:
            # Autocompletar dirección desde el contacto del destinatario
            parts = filter(None, [
                self.recipient_id.street,
                self.recipient_id.street2,
            ])
            address = ', '.join(parts)
            if address:
                self.recipient_address = address
            # Autocompletar ciudad
            if self.recipient_id.city:
                self.recipient_city = self.recipient_id.city
            # Autocompletar zona si el destinatario tiene ciudad configurada
            if self.recipient_id.zip and not self.route_id:
                pass  # espacio para lógica futura de zona automática

    # ── onchange: al cambiar cliente, limpiar destinatario si ya no aplica ──
    @api.onchange('partner_id')
    def _onchange_partner_id_recipient(self):
        if self.recipient_id and self.partner_id:
            owners = self.recipient_id.courier_owner_ids
            # Si el destinatario tiene clientes asignados y el cliente actual no está
            if owners and self.partner_id not in owners:
                self.recipient_id = False
                self.recipient_address = False
                self.recipient_city = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'courier.request'
                ) or 'Nuevo'
        records = super().create(vals_list)
        for record in records:
            record._generate_access_token()
        return records

    def _generate_access_token(self):
        import secrets
        for rec in self:
            if not rec.access_token:
                rec.access_token = secrets.token_urlsafe(32)

    # ────────────────────────────────────────────────────────────────────────
    # Computes
    # ────────────────────────────────────────────────────────────────────────

    @api.depends('partner_id')
    def _compute_sender_address(self):
        for rec in self:
            if rec.partner_id:
                parts = filter(None, [
                    rec.partner_id.street,
                    rec.partner_id.city,
                    rec.partner_id.country_id.name,
                ])
                rec.sender_address = ', '.join(parts)
            else:
                rec.sender_address = ''

    @api.depends('route_id', 'date_request')
    def _compute_estimated_delivery(self):
        from datetime import timedelta, date
        for rec in self:
            if rec.route_id and rec.date_request:
                days = rec.route_id.delivery_days or 1
                base = rec.date_request.date()
                rec.estimated_delivery_date = base + timedelta(days=days)
            else:
                rec.estimated_delivery_date = False

    @api.depends('weight', 'route_id', 'partner_id')
    def _compute_price(self):
        for rec in self:
            if not rec.route_id or not rec.weight:
                rec.base_amount = 0.0
                rec.price_rule_id = False
                continue

            rule = self.env['courier.price.rule'].search([
                ('route_id', '=', rec.route_id.id),
                ('weight_from', '<=', rec.weight),
                ('weight_to', '>=', rec.weight),
                ('active', '=', True),
            ], limit=1, order='weight_from asc')

            if rule:
                rec.price_rule_id = rule.id
                if rec.partner_id:
                    rec.base_amount = rule.get_price_for_partner(
                        rec.partner_id.id
                    )
                else:
                    rec.base_amount = rule.price
            else:
                # Si no hay regla, usar precio base de la zona
                rec.price_rule_id = False
                rec.base_amount = rec.route_id.base_price

    @api.depends('base_amount', 'additional_charges', 'discount_amount')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = (
                rec.base_amount
                + rec.additional_charges
                - rec.discount_amount
            )

    @api.depends('invoice_id', 'invoice_id.state')
    def _compute_is_invoiced(self):
        for rec in self:
            rec.is_invoiced = bool(
                rec.invoice_id and rec.invoice_id.state != 'cancel'
            )

    @api.depends('name')
    def _compute_qr_code(self):
        for rec in self:
            if rec.name and rec.name != 'Nuevo':
                try:
                    base_url = self.env['ir.config_parameter'].sudo().get_param(
                        'web.base.url'
                    )
                    tracking_url = (
                        f"{base_url}/courier/track?ref={rec.name}"
                    )
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_M,
                        box_size=6,
                        border=2,
                    )
                    qr.add_data(tracking_url)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color='black', back_color='white')
                    buffer = io.BytesIO()
                    img.save(buffer, format='PNG')
                    rec.qr_code = base64.b64encode(buffer.getvalue())
                except Exception:
                    rec.qr_code = False
            else:
                rec.qr_code = False

    # ────────────────────────────────────────────────────────────────────────
    # Acciones de cambio de estado
    # ────────────────────────────────────────────────────────────────────────

    def _change_stage(self, code):
        stage = self.env['courier.stage'].search([('code', '=', code)], limit=1)
        if not stage:
            raise UserError(_(f'No se encontró el estado con código: {code}'))
        for rec in self:
            rec.stage_id = stage
            # Enviar correo automático si la etapa tiene plantilla configurada
            if stage.mail_template_id:
                stage.mail_template_id.send_mail(rec.id, force_send=True)

    def action_receive(self):
        """Paquete recibido en bodega."""
        self._change_stage('received')
        self.write({'date_received': fields.Datetime.now()})

    def action_dispatch(self):
        """Paquete despachado / en tránsito."""
        if not self.driver_id:
            raise UserError(_(
                'Debe asignar un motorista antes de despachar el paquete.'
            ))
        self._change_stage('in_transit')
        self.write({'date_dispatched': fields.Datetime.now()})

    def action_out_delivery(self):
        """En reparto (última milla)."""
        self._change_stage('out_delivery')

    def action_deliver(self):
        """Marcar como entregado."""
        self._change_stage('delivered')
        self.write({'date_delivered': fields.Datetime.now()})

    def action_cancel(self):
        """Cancelar el envío."""
        if self.is_invoiced:
            raise UserError(_(
                'No se puede cancelar un envío que ya tiene factura. '
                'Cancele la factura primero.'
            ))
        self._change_stage('cancelled')

    def action_return(self):
        """Marcar como devuelto."""
        self._change_stage('returned')

    def action_reset_draft(self):
        """Regresar a borrador."""
        self._change_stage('draft')

    # ────────────────────────────────────────────────────────────────────────
    # Facturación
    # ────────────────────────────────────────────────────────────────────────

    def action_create_invoice(self):
        self.ensure_one()
        if self.is_invoiced:
            raise UserError(_('Este envío ya tiene una factura generada.'))
        if self.total_amount <= 0:
            raise UserError(_('El monto total debe ser mayor a cero para facturar.'))

        # Buscar o crear el producto de servicio de envío
        product = self.env['product.product'].search([
            ('default_code', '=', 'COURIER-SRV')
        ], limit=1)
        if not product:
            product = self.env['product.product'].create({
                'name': 'Servicio de Envío / Encomienda',
                'default_code': 'COURIER-SRV',
                'type': 'service',
                'invoice_policy': 'order',
                'list_price': 0.0,
            })

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.today(),
            'ref': self.name,
            'narration': (
                f'Envío {self.name} | '
                f'Destino: {self.recipient_city or ""} | '
                f'Destinatario: {self.recipient_name or ""}'
            ),
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id,
                'name': (
                    f'Servicio de Envío — Guía {self.name}\n'
                    f'Zona: {self.route_id.name or ""} | '
                    f'Peso: {self.weight} kg\n'
                    f'Destinatario: {self.recipient_name or ""} — '
                    f'{self.recipient_city or ""}'
                ),
                'quantity': 1,
                'price_unit': self.total_amount,
            })],
        }

        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice.id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Factura de Envío'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
        }

    def action_view_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Factura'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
        }

    # ────────────────────────────────────────────────────────────────────────
    # Portal mixin
    # ────────────────────────────────────────────────────────────────────────

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = f'/my/courier/{rec.id}'

    def _get_report_base_filename(self):
        self.ensure_one()
        return f'Envio-{self.name}'
