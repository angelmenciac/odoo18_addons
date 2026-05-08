# -*- coding: utf-8 -*-
{
    'name': 'Conchita Courier — Sistema de Gestión de Encomiendas',
    'version': '18.0.1.0.0',
    'category': 'Logistics',
    'summary': 'Sistema completo de gestión de envíos y encomiendas para Honduras',
    'description': """
        Módulo de gestión de courier y encomiendas adaptado para Transporte Conchita.
        Incluye:
        - Gestión completa de solicitudes de envío
        - Tarifas por zona, peso y cliente
        - Portal web para clientes con visibilidad restringida
        - Tracking público por número de guía con QR
        - Motoristas y rutas de entrega
        - Destinatarios privados por cliente
        - Facturación integrada
        - Firma digital y fotos del paquete
        - Dashboard de análisis
        - Zonas de Honduras precargadas
    """,
    'author': 'Neoversa — Transporte Conchita',
    'website': 'https://neoversa.net',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'portal',
        'account',
        'website',
        'hr',
        'sale_management',
    ],
    'data': [
        # Security
        'security/courier_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/courier_stages_data.xml',
        'data/courier_routes_hn_data.xml',
        # Views
        'views/courier_stage_views.xml',
        'views/courier_route_views.xml',
        'views/courier_price_rule_views.xml',
        'views/courier_driver_views.xml',
        'views/courier_request_views.xml',
        'views/res_partner_views.xml',
        'views/portal_templates.xml',
        'views/menu_views.xml',
        # Reports
        'report/courier_request_report.xml',
        'report/courier_label_report.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'conchita_courier/static/src/css/portal.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': [],
}
