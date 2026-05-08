# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
import json


class CourierPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'courier_count' in counters:
            partner = request.env.user.partner_id
            values['courier_count'] = request.env['courier.request'].search_count([
                ('partner_id', 'child_of', partner.commercial_partner_id.id)
            ])
        return values

    # ── Lista de envíos del cliente en el portal ──────────────────────────────
    @http.route(['/my/courier', '/my/courier/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_my_couriers(self, page=1, sortby=None, filterby=None, **kw):
        partner = request.env.user.partner_id
        CourierRequest = request.env['courier.request']

        domain = [('partner_id', 'child_of', partner.commercial_partner_id.id)]

        searchbar_sortings = {
            'date': {'label': _('Fecha'), 'order': 'date_request desc'},
            'name': {'label': _('Número de Guía'), 'order': 'name desc'},
            'stage': {'label': _('Estado'), 'order': 'stage_id'},
        }
        searchbar_filters = {
            'all': {'label': _('Todos'), 'domain': []},
            'in_transit': {
                'label': _('En Tránsito'),
                'domain': [('stage_id.code', '=', 'in_transit')],
            },
            'delivered': {
                'label': _('Entregados'),
                'domain': [('stage_id.code', '=', 'delivered')],
            },
            'pending': {
                'label': _('Pendientes'),
                'domain': [('stage_id.code', 'in', ['draft', 'received'])],
            },
        }

        sortby = sortby or 'date'
        filterby = filterby or 'all'
        order = searchbar_sortings[sortby]['order']
        domain += searchbar_filters[filterby]['domain']

        total = CourierRequest.search_count(domain)
        pager = portal_pager(
            url='/my/courier',
            url_args={'sortby': sortby, 'filterby': filterby},
            total=total,
            page=page,
            step=10,
        )

        couriers = CourierRequest.search(
            domain,
            order=order,
            limit=10,
            offset=pager['offset'],
        )

        return request.render('conchita_courier.portal_my_couriers', {
            'couriers': couriers,
            'page_name': 'courier',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
            'default_url': '/my/courier',
        })

    # ── Detalle de un envío en el portal ──────────────────────────────────────
    @http.route(['/my/courier/<int:courier_id>'],
                type='http', auth='user', website=True)
    def portal_courier_detail(self, courier_id, **kw):
        try:
            courier = self._document_check_access(
                'courier.request', courier_id
            )
        except (AccessError, MissingError):
            return request.redirect('/my/courier')

        return request.render('conchita_courier.portal_courier_detail', {
            'courier': courier,
            'page_name': 'courier',
        })

    # ── Formulario de nuevo envío desde portal ────────────────────────────────
    @http.route('/my/courier/new', type='http', auth='user', website=True)
    def portal_new_courier(self, **kw):
        partner = request.env.user.partner_id
        routes = request.env['courier.route'].sudo().search([('active', '=', True)])

        # Destinatarios disponibles para este cliente (privados + públicos)
        commercial = partner.commercial_partner_id
        recipients = request.env['res.partner'].sudo().search([
            ('is_courier_recipient', '=', True),
            '|',
            ('courier_owner_ids', 'in', [commercial.id]),
            ('courier_owner_ids', '=', False),
        ])

        return request.render('conchita_courier.portal_new_courier', {
            'partner': partner,
            'routes': routes,
            'recipients': recipients,
            'page_name': 'courier',
        })

    @http.route('/my/courier/submit', type='http', auth='user',
                website=True, methods=['POST'])
    def portal_submit_courier(self, **post):
        partner = request.env.user.partner_id
        commercial = partner.commercial_partner_id
        error = {}

        # Validaciones básicas
        required = ['route_id', 'package_description', 'weight', 'package_type']
        for field in required:
            if not post.get(field):
                error[field] = True
        if not post.get('recipient_address'):
            error['recipient_address'] = True
        if not post.get('recipient_city'):
            error['recipient_city'] = True

        if error:
            routes = request.env['courier.route'].sudo().search([('active', '=', True)])
            recipients = request.env['res.partner'].sudo().search([
                ('is_courier_recipient', '=', True),
                '|',
                ('courier_owner_ids', 'in', [commercial.id]),
                ('courier_owner_ids', '=', False),
            ])
            return request.render('conchita_courier.portal_new_courier', {
                'partner': commercial,
                'routes': routes,
                'recipients': recipients,
                'error': error,
                'post': post,
                'page_name': 'courier',
            })

        # ── Gestión del destinatario ──
        recipient_id = post.get('recipient_id')

        if recipient_id:
            # Destinatario existente seleccionado
            recipient_id = int(recipient_id)
        elif post.get('new_recipient_name'):
            # Crear nuevo destinatario
            new_rec_vals = {
                'name': post['new_recipient_name'],
                'phone': post.get('new_recipient_phone', ''),
                'street': post.get('recipient_address', ''),
                'city': post.get('recipient_city', ''),
                'is_courier_recipient': True,
            }
            # Si marcó "guardar", vincularlo a este cliente
            if post.get('save_recipient'):
                new_rec_vals['courier_owner_ids'] = [(4, commercial.id)]
            new_rec = request.env['res.partner'].sudo().create(new_rec_vals)
            recipient_id = new_rec.id
        else:
            error['new_recipient_name'] = True
            routes = request.env['courier.route'].sudo().search([('active', '=', True)])
            recipients = request.env['res.partner'].sudo().search([
                ('is_courier_recipient', '=', True),
                '|',
                ('courier_owner_ids', 'in', [commercial.id]),
                ('courier_owner_ids', '=', False),
            ])
            return request.render('conchita_courier.portal_new_courier', {
                'partner': commercial,
                'routes': routes,
                'recipients': recipients,
                'error': error,
                'post': post,
                'page_name': 'courier',
            })

        # ── Crear la solicitud de envío ──
        vals = {
            'partner_id': commercial.id,
            'recipient_id': recipient_id,
            'route_id': int(post['route_id']),
            'package_description': post['package_description'],
            'weight': float(post.get('weight', 1.0)),
            'package_type': post['package_type'],
            'recipient_address': post.get('recipient_address', ''),
            'recipient_city': post.get('recipient_city', ''),
            'special_instructions': post.get('special_instructions', ''),
            'declared_value': float(post.get('declared_value', 0.0) or 0.0),
            'is_fragile': bool(post.get('is_fragile')),
        }

        courier = request.env['courier.request'].sudo().create(vals)
        return request.redirect(f'/my/courier/{courier.id}')

    # ── Guardar calificación del cliente ──────────────────────────────────────
    @http.route('/courier/rate', type='json', auth='user', website=True)
    def rate_courier(self, courier_id, rating, feedback='', **kw):
        courier = request.env['courier.request'].browse(int(courier_id))
        if courier and courier.partner_id == request.env.user.partner_id:
            courier.sudo().write({
                'rating_value': str(rating),
                'rating_feedback': feedback,
                'rating_date': fields.Datetime.now(),
            })
            return {'success': True}
        return {'success': False, 'error': 'No autorizado'}

    # ── Tracking público (sin login) ──────────────────────────────────────────
    @http.route('/courier/track', type='http', auth='public', website=True)
    def public_tracking(self, ref=None, **kw):
        courier = None
        error = None

        if ref:
            courier = request.env['courier.request'].sudo().search([
                ('name', '=', ref.strip().upper()),
            ], limit=1)
            if not courier:
                error = _('No se encontró ningún envío con el número: %s') % ref

        return request.render('conchita_courier.public_tracking', {
            'courier': courier,
            'ref': ref,
            'error': error,
        })


class CourierControllers(http.Controller):

    # ── API para obtener precio estimado (AJAX desde portal) ──────────────────
    @http.route('/courier/get_price', type='json', auth='user', website=True)
    def get_price(self, route_id, weight, partner_id=None, **kw):
        try:
            route = request.env['courier.route'].sudo().browse(int(route_id))
            weight = float(weight)

            rule = request.env['courier.price.rule'].sudo().search([
                ('route_id', '=', route.id),
                ('weight_from', '<=', weight),
                ('weight_to', '>=', weight),
                ('active', '=', True),
            ], limit=1, order='weight_from asc')

            if rule:
                partner = request.env.user.partner_id
                price = rule.get_price_for_partner(partner.commercial_partner_id.id)
                return {
                    'success': True,
                    'price': price,
                    'route_name': route.name,
                    'delivery_days': route.delivery_days,
                }
            else:
                return {
                    'success': True,
                    'price': route.base_price,
                    'route_name': route.name,
                    'delivery_days': route.delivery_days,
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}
