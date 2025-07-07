#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CFDI Parser for v4 System

Comprehensive XML parser that extracts ALL CFDI fields for the enhanced schema.
Handles CFDI 3.3 and 4.0 versions with complete field extraction.
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CFDIParser:
    """
    Enhanced CFDI XML parser for comprehensive data extraction.
    Extracts all fields required for the 5-table v4 schema.
    """
    
    def __init__(self):
        """Initialize parser with namespace definitions."""
        self.namespaces = {
            'cfdi': 'http://www.sat.gob.mx/cfd/4',
            'cfdi3': 'http://www.sat.gob.mx/cfd/3',
            'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
        }
        logger.info("CFDI Parser initialized")
    
    def parse_xml_file(self, xml_path: str) -> Dict[str, Any]:
        """
        Parse XML file and extract all invoice data.
        
        Args:
            xml_path: Path to XML file
            
        Returns:
            Dictionary with comprehensive invoice data
        """
        try:
            with open(xml_path, 'r', encoding='utf-8') as file:
                xml_content = file.read()
            
            return self.parse_xml_content(xml_content)
            
        except Exception as e:
            logger.error(f"Error parsing XML file {xml_path}: {e}")
            raise
    
    def parse_xml_content(self, xml_content: str) -> Dict[str, Any]:
        """
        Parse XML content and extract comprehensive data.
        
        Args:
            xml_content: Raw XML content
            
        Returns:
            Dictionary with all extracted fields
        """
        try:
            root = ET.fromstring(xml_content)
            self._detect_cfdi_version(root)
            
            # Extract all data sections
            invoice_data = {
                **self._extract_basic_invoice_data(root),
                **self._extract_issuer_data(root),
                **self._extract_receiver_data(root),
                **self._extract_payment_data(root),
                **self._extract_tax_data(root),
                **self._extract_digital_stamp_data(root),
                **self._extract_location_data(root),
                'items': self._extract_items(root),
                **self._extract_metadata(root)
            }
            
            logger.info("Successfully parsed CFDI XML")
            return invoice_data
            
        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            raise ValueError(f"Invalid XML format: {e}")
        except Exception as e:
            logger.error(f"CFDI parsing error: {e}")
            raise
    
    def _detect_cfdi_version(self, root: ET.Element) -> None:
        """Detect CFDI version and set appropriate namespace."""
        version = root.get('Version') or root.get('version')
        if version and version.startswith('3'):
            self.current_ns = 'cfdi3'
        else:
            self.current_ns = 'cfdi'
        
        logger.debug(f"Detected CFDI version: {version}, using namespace: {self.current_ns}")
    
    def _extract_basic_invoice_data(self, root: ET.Element) -> Dict[str, Any]:
        """Extract comprehensive basic invoice information."""
        return {
            'uuid': self._get_uuid(root),
            'version': root.get('Version') or root.get('version'),
            'series': root.get('Serie'),
            'folio': root.get('Folio'),
            'issue_date': self._parse_datetime(root.get('Fecha')),
            'certification_date': self._parse_datetime(root.get('FechaTimbrado')),
            'invoice_type': root.get('TipoDeComprobante', 'I'),
            'subtotal': self._to_decimal(root.get('SubTotal')),
            'total_discount': self._to_decimal(root.get('Descuento')),
            'total_amount': self._to_decimal(root.get('Total')),
            'currency': root.get('Moneda', 'MXN'),
            'exchange_rate': self._to_decimal(root.get('TipoCambio'))
        }
    
    def _extract_issuer_data(self, root: ET.Element) -> Dict[str, Any]:
        """Extract comprehensive issuer data."""
        emisor = root.find(f'{{{self.namespaces[self.current_ns]}}}Emisor')
        if emisor is None:
            return {}
        
        issuer_data = {
            'issuer_rfc': emisor.get('Rfc'),
            'issuer_name': emisor.get('Nombre'),
            'issuer_fiscal_regime': emisor.get('RegimenFiscal'),
            'issuer_use_cfdi': emisor.get('UsoCFDI'),
            'issuer_residence': emisor.get('ResidenciaFiscal'),
            'issuer_tax_id': emisor.get('NumRegIdTrib')
        }
        
        # Extract additional issuer fields that may be present
        issuer_data.update({
            'issuer_business_name': emisor.get('RazonSocial'),
            'issuer_commercial_name': emisor.get('NombreComercial'),
            'issuer_curp': emisor.get('Curp'),
            'issuer_foreign_tax_id': emisor.get('NumRegIdTribExtranjero')
        })
        
        return issuer_data
    
    def _extract_receiver_data(self, root: ET.Element) -> Dict[str, Any]:
        """Extract comprehensive receiver data."""
        receptor = root.find(f'{{{self.namespaces[self.current_ns]}}}Receptor')
        if receptor is None:
            return {}
        
        receiver_data = {
            'receiver_rfc': receptor.get('Rfc'),
            'receiver_name': receptor.get('Nombre'),
            'receiver_fiscal_address': receptor.get('DomicilioFiscalReceptor'),
            'receiver_residence': receptor.get('ResidenciaFiscal'),
            'receiver_tax_id': receptor.get('NumRegIdTrib'),
            'receiver_use_cfdi': receptor.get('UsoCFDI')
        }
        
        # Extract additional receiver fields
        receiver_data.update({
            'receiver_business_name': receptor.get('RazonSocial'),
            'receiver_commercial_name': receptor.get('NombreComercial'),
            'receiver_curp': receptor.get('Curp'),
            'receiver_foreign_tax_id': receptor.get('NumRegIdTribExtranjero'),
            'receiver_postal_code': receptor.get('CodigoPostal')
        })
        
        return receiver_data
    
    def _extract_payment_data(self, root: ET.Element) -> Dict[str, Any]:
        """Extract comprehensive payment method and terms."""
        payment_data = {
            'payment_method': root.get('FormaPago'),
            'payment_method_desc': self._get_payment_method_desc(root.get('FormaPago')),
            'payment_terms': root.get('MetodoPago'),
            'payment_conditions': root.get('CondicionesDePago')
        }
        
        # Extract additional payment fields
        payment_data.update({
            'payment_account': root.get('NumCtaPago'),
            'payment_confirmation': root.get('Confirmacion'),
            'payment_date': self._parse_datetime(root.get('FechaPago')),
            'installment_number': root.get('NumParcialidad')
        })
        
        return payment_data
    
    def _extract_tax_data(self, root: ET.Element) -> Dict[str, Any]:
        """Extract comprehensive tax information."""
        impuestos = root.find(f'{{{self.namespaces[self.current_ns]}}}Impuestos')
        if impuestos is None:
            return {
                'total_transferred_taxes': Decimal('0'),
                'total_withheld_taxes': Decimal('0')
            }
        
        tax_data = {
            'total_transferred_taxes': self._to_decimal(impuestos.get('TotalImpuestosTrasladados')) or Decimal('0'),
            'total_withheld_taxes': self._to_decimal(impuestos.get('TotalImpuestosRetenidos')) or Decimal('0')
        }
        
        # Extract detailed tax information
        traslados = impuestos.find(f'{{{self.namespaces[self.current_ns]}}}Traslados')
        retenciones = impuestos.find(f'{{{self.namespaces[self.current_ns]}}}Retenciones')
        
        if traslados is not None:
            tax_data['transferred_taxes_detail'] = self._extract_tax_details(traslados, 'Traslado')
        
        if retenciones is not None:
            tax_data['withheld_taxes_detail'] = self._extract_tax_details(retenciones, 'Retencion')
        
        return tax_data
    
    def _extract_digital_stamp_data(self, root: ET.Element) -> Dict[str, Any]:
        """Extract digital stamp and certification data."""
        stamp_data = {
            'digital_stamp': root.get('Sello'),
            'certificate_number': root.get('NoCertificado'),
            'certificate': root.get('Certificado')
        }
        
        # Extract TimbreFiscalDigital (SAT stamp) information
        tfd = root.find(f'.//{{{self.namespaces["tfd"]}}}TimbreFiscalDigital')
        if tfd is not None:
            stamp_data.update({
                'sat_seal': tfd.get('SelloSAT'),
                'sat_certificate': tfd.get('NoCertificadoSAT'),
                'fiscal_folio': tfd.get('UUID'),
                'stamp_datetime': self._parse_datetime(tfd.get('FechaTimbrado')),
                'stamp_version': tfd.get('Version'),
                'rfc_provider': tfd.get('RfcProvCertif'),
                'stamp_legend': tfd.get('Leyenda')
            })
        
        return stamp_data
    
    def _extract_location_data(self, root: ET.Element) -> Dict[str, Any]:
        """Extract location and export data."""
        location_data = {
            'expedition_place': root.get('LugarExpedicion'),
            'export_operation': root.get('Exportacion'),
            'confirmation': root.get('Confirmacion')
        }
        
        # Extract additional location fields if present
        location_data.update({
            'issuer_postal_code': root.get('CodigoPostalEmisor'),
            'receiver_postal_code': root.get('CodigoPostalReceptor'),
            'issuer_country': root.get('PaisEmisor'),
            'receiver_country': root.get('PaisReceptor')
        })
        
        return location_data
    
    def _extract_items(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract all invoice items with enhanced data."""
        conceptos = root.find(f'{{{self.namespaces[self.current_ns]}}}Conceptos')
        if conceptos is None:
            return []
        
        items = []
        for i, concepto in enumerate(conceptos.findall(f'{{{self.namespaces[self.current_ns]}}}Concepto'), 1):
            item = {
                'line_number': i,
                'product_code': concepto.get('ClaveProdServ'),
                'internal_code': concepto.get('NoIdentificacion'),
                'description': concepto.get('Descripcion', ''),
                'quantity': self._to_decimal(concepto.get('Cantidad')),
                'unit_code': concepto.get('ClaveUnidad'),
                'unit_description': concepto.get('Unidad'),
                'unit_price': self._to_decimal(concepto.get('ValorUnitario')),
                'subtotal': self._to_decimal(concepto.get('Importe')),
                'discount': self._to_decimal(concepto.get('Descuento')) or Decimal('0'),
                'total_amount': self._calculate_item_total(concepto)
            }
            
            # Extract enhanced unit information
            item.update(self._extract_item_unit_data(concepto))
            
            # Extract tax information for this item
            item.update(self._extract_item_taxes(concepto))
            
            # Extract additional item fields
            item.update({
                'customs_number': concepto.get('NumeroAduana'),
                'customs_date': concepto.get('FechaAduana'),
                'customs_receiver': concepto.get('AduneroReceptor'),
                'predial_account': concepto.get('CuentaPredial'),
                'part_number': concepto.get('NumeroParte')
            })
            
            items.append(item)
        
        return items
    
    def _extract_metadata(self, root: ET.Element) -> Dict[str, Any]:
        """Extract processing metadata."""
        return {
            'processing_timestamp': datetime.utcnow(),
            'xml_size': len(ET.tostring(root, encoding='unicode'))
        }
    
    # Utility methods
    def _get_uuid(self, root: ET.Element) -> Optional[str]:
        """Extract UUID from TimbreFiscalDigital."""
        tfd = root.find(f'.//{{{self.namespaces["tfd"]}}}TimbreFiscalDigital')
        if tfd is not None:
            return tfd.get('UUID')
        return None
    
    def _to_decimal(self, value: Optional[str]) -> Optional[Decimal]:
        """Convert string to Decimal safely."""
        if not value:
            return None
        try:
            return Decimal(str(value))
        except:
            return None
    
    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Parse datetime string with robust handling for CFDI formats.
        
        Handles all common CFDI datetime formats without fallbacks.
        
        Args:
            date_str: Date string from CFDI XML attribute
            
        Returns:
            Parsed datetime or None if parsing fails
        """
        if not date_str:
            return None
        
        # Clean the date string first
        clean_date = date_str.strip()
        
        # List of common CFDI datetime formats
        datetime_formats = [
            '%Y-%m-%dT%H:%M:%S',           # 2024-03-15T10:30:00 (most common)
            '%Y-%m-%d %H:%M:%S',           # 2024-03-15 10:30:00
            '%Y-%m-%dT%H:%M:%S.%f',        # 2024-03-15T10:30:00.123456
            '%Y-%m-%dT%H:%M:%SZ',          # 2024-03-15T10:30:00Z
            '%Y-%m-%dT%H:%M:%S.%fZ',       # 2024-03-15T10:30:00.123Z
            '%Y-%m-%d',                    # 2024-03-15 (date only)
            '%d/%m/%Y %H:%M:%S',           # 15/03/2024 10:30:00 (Mexican format)
            '%d/%m/%Y',                    # 15/03/2024 (Mexican date only)
        ]
        
        # Remove timezone indicators that Python can't handle easily
        clean_date = clean_date.replace('Z', '').replace('+00:00', '').replace('-06:00', '').replace('-05:00', '')
        
        # Try each format
        for fmt in datetime_formats:
            try:
                parsed_date = datetime.strptime(clean_date, fmt)
                logger.debug(f"CFDI Parser: Successfully parsed datetime '{date_str}' using format '{fmt}' -> {parsed_date}")
                return parsed_date
            except ValueError:
                continue
        
        # Try fromisoformat as last resort (handles some edge cases)
        try:
            # Clean for fromisoformat
            iso_clean = clean_date.replace('T', ' ').replace('Z', '')
            parsed_date = datetime.fromisoformat(iso_clean)
            logger.debug(f"CFDI Parser: Successfully parsed datetime '{date_str}' using fromisoformat -> {parsed_date}")
            return parsed_date
        except ValueError:
            pass
        
        # Log the error and return None to preserve data integrity
        logger.warning(f"CFDI Parser: Could not parse datetime '{date_str}' - returning NULL")
        return None
    
    def _get_payment_method_desc(self, code: Optional[str]) -> Optional[str]:
        """Get payment method description from code."""
        payment_methods = {
            '01': 'Efectivo',
            '02': 'Cheque nominativo',
            '03': 'Transferencia electrónica de fondos',
            '04': 'Tarjeta de crédito',
            '05': 'Monedero electrónico',
            '06': 'Dinero electrónico',
            '08': 'Vales de despensa',
            '12': 'Dación en pago',
            '13': 'Pago por subrogación',
            '14': 'Pago por consignación',
            '15': 'Condonación',
            '17': 'Compensación',
            '23': 'Novación',
            '24': 'Confusión',
            '25': 'Remisión de deuda',
            '26': 'Prescripción o caducidad',
            '27': 'A satisfacción del acreedor',
            '28': 'Tarjeta de débito',
            '29': 'Tarjeta de servicios',
            '30': 'Aplicación de anticipos',
            '99': 'Por definir'
        }
        return payment_methods.get(code)
    
    def _calculate_item_total(self, concepto: ET.Element) -> Optional[Decimal]:
        """Calculate total amount for item including taxes."""
        importe = self._to_decimal(concepto.get('Importe'))
        descuento = self._to_decimal(concepto.get('Descuento', '0'))
        
        if importe is None:
            return None
        
        subtotal = importe - (descuento or Decimal('0'))
        
        # Add taxes if present
        impuestos = concepto.find(f'{{{self.namespaces[self.current_ns]}}}Impuestos')
        if impuestos is not None:
            traslados = impuestos.find(f'{{{self.namespaces[self.current_ns]}}}Traslados')
            if traslados is not None:
                for traslado in traslados.findall(f'{{{self.namespaces[self.current_ns]}}}Traslado'):
                    tax_amount = self._to_decimal(traslado.get('Importe'))
                    if tax_amount:
                        subtotal += tax_amount
        
        return subtotal
    
    def _extract_item_unit_data(self, concepto: ET.Element) -> Dict[str, Any]:
        """Extract enhanced unit information for items."""
        return {
            'units_per_package': self._to_decimal(concepto.get('UnidadesPorPaquete')),
            'package_description': concepto.get('DescripcionPaquete'),
            'net_weight': self._to_decimal(concepto.get('PesoNeto')),
            'gross_weight': self._to_decimal(concepto.get('PesoBruto'))
        }
    
    def _extract_item_taxes(self, concepto: ET.Element) -> Dict[str, Any]:
        """Extract tax information for individual items."""
        taxes_data = {
            'transferred_taxes': [],
            'withheld_taxes': [],
            'total_tax_amount': Decimal('0')
        }
        
        impuestos = concepto.find(f'{{{self.namespaces[self.current_ns]}}}Impuestos')
        if impuestos is None:
            return taxes_data
        
        # Extract transferred taxes (traslados)
        traslados = impuestos.find(f'{{{self.namespaces[self.current_ns]}}}Traslados')
        if traslados is not None:
            for traslado in traslados.findall(f'{{{self.namespaces[self.current_ns]}}}Traslado'):
                tax_info = {
                    'tax_type': traslado.get('Impuesto'),
                    'tax_rate': self._to_decimal(traslado.get('TasaOCuota')),
                    'tax_amount': self._to_decimal(traslado.get('Importe')),
                    'tax_base': self._to_decimal(traslado.get('Base')),
                    'factor_type': traslado.get('TipoFactor')
                }
                taxes_data['transferred_taxes'].append(tax_info)
                if tax_info['tax_amount']:
                    taxes_data['total_tax_amount'] += tax_info['tax_amount']
        
        # Extract withheld taxes (retenciones)
        retenciones = impuestos.find(f'{{{self.namespaces[self.current_ns]}}}Retenciones')
        if retenciones is not None:
            for retencion in retenciones.findall(f'{{{self.namespaces[self.current_ns]}}}Retencion'):
                tax_info = {
                    'tax_type': retencion.get('Impuesto'),
                    'tax_rate': self._to_decimal(retencion.get('TasaOCuota')),
                    'tax_amount': self._to_decimal(retencion.get('Importe')),
                    'tax_base': self._to_decimal(retencion.get('Base')),
                    'factor_type': retencion.get('TipoFactor')
                }
                taxes_data['withheld_taxes'].append(tax_info)
                if tax_info['tax_amount']:
                    taxes_data['total_tax_amount'] -= tax_info['tax_amount']  # Subtract withheld taxes
        
        return taxes_data
    
    def _extract_tax_details(self, tax_element: ET.Element, tax_type: str) -> List[Dict[str, Any]]:
        """Extract detailed tax information from tax elements."""
        tax_details = []
        
        for tax in tax_element.findall(f'{{{self.namespaces[self.current_ns]}}}{tax_type}'):
            tax_info = {
                'tax_type': tax.get('Impuesto'),
                'tax_rate': self._to_decimal(tax.get('TasaOCuota')),
                'tax_amount': self._to_decimal(tax.get('Importe')),
                'tax_base': self._to_decimal(tax.get('Base')),
                'factor_type': tax.get('TipoFactor')
            }
            tax_details.append(tax_info)
        
        return tax_details 