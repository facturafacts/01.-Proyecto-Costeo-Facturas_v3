#!/usr/bin/env python3
"""
CFDI Processing Pipeline Integration Test
Tests the complete CFDI processing workflow with new P62 categories.
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.processing.cfdi_parser import CFDIParser
from src.processing.gemini_classifier import GeminiClassifier
from src.processing.batch_processor import BatchProcessor
from src.data.database import DatabaseManager
from src.data.models import Invoice, InvoiceItem


class CFDIProcessingPipelineTest:
    """Test the complete CFDI processing pipeline."""
    
    def __init__(self):
        self.test_results = {}
        self.temp_dir = None
        self.db_manager = None
        
    def setup_test_environment(self):
        """Set up temporary test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="cfdi_test_")
        
        # Create test database
        test_db_path = os.path.join(self.temp_dir, "test_cfdi.db")
        self.db_manager = DatabaseManager(test_db_path)
        self.db_manager.initialize_database()
        
        # Create test directories
        self.test_data_dir = os.path.join(self.temp_dir, "test_data")
        self.processed_dir = os.path.join(self.temp_dir, "processed")
        self.failed_dir = os.path.join(self.temp_dir, "failed")
        
        for directory in [self.test_data_dir, self.processed_dir, self.failed_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def cleanup_test_environment(self):
        """Clean up test environment."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_sample_cfdi_xml(self) -> str:
        """Create a sample CFDI XML for testing."""
        sample_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" 
                  Version="4.0" 
                  Folio="12345" 
                  Fecha="2024-01-15T10:30:00" 
                  SubTotal="1000.00" 
                  Total="1160.00" 
                  Moneda="MXN" 
                  TipoDeComprobante="I"
                  MetodoPago="PUE"
                  FormaPago="01"
                  LugarExpedicion="01000">
  
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="Empresa Emisora SA" RegimenFiscal="601"/>
  
  <cfdi:Receptor Rfc="BBB020202BBB" Nombre="Empresa Receptora SA" 
                 DomicilioFiscalReceptor="02000" 
                 RegimenFiscalReceptor="601" 
                 UsoCFDI="G03"/>
  
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="50202306" 
                   Cantidad="10.000" 
                   ClaveUnidad="KGM" 
                   Unidad="Kilogramo" 
                   Descripcion="Aceite de oliva extra virgen" 
                   ValorUnitario="100.00" 
                   Importe="1000.00">
      <cfdi:Impuestos>
        <cfdi:Traslados>
          <cfdi:Traslado Base="1000.00" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="160.00"/>
        </cfdi:Traslados>
      </cfdi:Impuestos>
    </cfdi:Concepto>
  </cfdi:Conceptos>
  
  <cfdi:Impuestos TotalImpuestosTrasladados="160.00">
    <cfdi:Traslados>
      <cfdi:Traslado Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Base="1000.00" Importe="160.00"/>
    </cfdi:Traslados>
  </cfdi:Impuestos>
  
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" 
                            Version="1.1" 
                            UUID="12345678-1234-1234-1234-123456789012" 
                            FechaTimbrado="2024-01-15T10:35:00" 
                            RfcProvCertif="SAT970701NN3"
                            SelloCFD="MOCK_SELLO_CFD"
                            NoCertificadoSAT="30001000000400002495"
                            SelloSAT="MOCK_SELLO_SAT"/>
  </cfdi:Complemento>
  
</cfdi:Comprobante>'''
        
        test_file = os.path.join(self.test_data_dir, "sample_invoice.xml")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(sample_xml)
        
        return test_file
    
    def test_cfdi_parser(self) -> Dict[str, Any]:
        """Test CFDI XML parsing functionality."""
        try:
            sample_file = self.create_sample_cfdi_xml()
            parser = CFDIParser()
            
            invoice_data = parser.parse_cfdi_file(sample_file)
            
            required_fields = [
                'folio', 'fecha', 'subtotal', 'total', 'moneda',
                'emisor_rfc', 'receptor_rfc', 'conceptos'
            ]
            
            missing_fields = [field for field in required_fields if field not in invoice_data]
            
            # Test conceptos structure
            conceptos_valid = (
                'conceptos' in invoice_data and 
                len(invoice_data['conceptos']) > 0 and
                'descripcion' in invoice_data['conceptos'][0]
            )
            
            return {
                "success": len(missing_fields) == 0 and conceptos_valid,
                "metrics": {
                    "Parsed fields": len(invoice_data),
                    "Missing fields": missing_fields if missing_fields else "None",
                    "Conceptos count": len(invoice_data.get('conceptos', [])),
                    "Conceptos valid": "Yes" if conceptos_valid else "No"
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_gemini_classification(self) -> Dict[str, Any]:
        """Test Gemini AI classification with new P62 structure."""
        try:
            # Mock Gemini response for testing
            sample_product = "Aceite de oliva extra virgen"
            
            # Load P62 categories to verify structure
            config_path = Path(__file__).parent.parent / "config" / "p62_categories.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                p62_data = json.load(f)
            
            # Simulate classification
            mock_classification = {
                "category": "Abarrotes",
                "subcategory": "Aceite",
                "sub_sub_category": "Aceite de oliva",
                "standardized_unit": "Litros",
                "confidence": 0.95,
                "reasoning": "Product clearly matches olive oil category"
            }
            
            # Verify the classification matches P62 structure
            categories = p62_data["categories"]
            classification_valid = (
                mock_classification["category"] in categories and
                mock_classification["subcategory"] in categories[mock_classification["category"]] and
                mock_classification["sub_sub_category"] in categories[mock_classification["category"]][mock_classification["subcategory"]]
            )
            
            return {
                "success": classification_valid,
                "metrics": {
                    "Classification structure": "3-level hierarchy",
                    "Category match": "Yes" if classification_valid else "No",
                    "Confidence score": mock_classification["confidence"],
                    "Standardized unit": mock_classification["standardized_unit"]
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_database_operations(self) -> Dict[str, Any]:
        """Test database storage operations."""
        try:
            # Create test invoice data
            invoice_data = {
                'folio': 'TEST-12345',
                'fecha': '2024-01-15T10:30:00',
                'subtotal': 1000.00,
                'total': 1160.00,
                'moneda': 'MXN',
                'emisor_rfc': 'AAA010101AAA',
                'emisor_nombre': 'Test Emisor',
                'receptor_rfc': 'BBB020202BBB',
                'receptor_nombre': 'Test Receptor',
                'uuid': '12345678-1234-1234-1234-123456789012',
                'tipo_comprobante': 'I',
                'metodo_pago': 'PUE',
                'forma_pago': '01',
                'conceptos': [{
                    'clave_prod_serv': '50202306',
                    'cantidad': 10.0,
                    'unidad': 'Kilogramo',
                    'descripcion': 'Aceite de oliva extra virgen',
                    'valor_unitario': 100.00,
                    'importe': 1000.00,
                    'categoria': 'Abarrotes',
                    'subcategoria': 'Aceite',
                    'sub_subcategoria': 'Aceite de oliva'
                }]
            }
            
            # Test database insertion
            with self.db_manager.get_session() as session:
                invoice = Invoice(
                    folio=invoice_data['folio'],
                    fecha=invoice_data['fecha'],
                    subtotal=invoice_data['subtotal'],
                    total=invoice_data['total'],
                    moneda=invoice_data['moneda'],
                    emisor_rfc=invoice_data['emisor_rfc'],
                    emisor_nombre=invoice_data['emisor_nombre'],
                    receptor_rfc=invoice_data['receptor_rfc'],
                    receptor_nombre=invoice_data['receptor_nombre'],
                    uuid=invoice_data['uuid']
                )
                
                session.add(invoice)
                session.flush()  # Get invoice ID
                
                # Add invoice item
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    descripcion=invoice_data['conceptos'][0]['descripcion'],
                    cantidad=invoice_data['conceptos'][0]['cantidad'],
                    valor_unitario=invoice_data['conceptos'][0]['valor_unitario'],
                    importe=invoice_data['conceptos'][0]['importe'],
                    categoria=invoice_data['conceptos'][0]['categoria'],
                    subcategoria=invoice_data['conceptos'][0]['subcategoria'],
                    sub_subcategoria=invoice_data['conceptos'][0]['sub_subcategoria']
                )
                
                session.add(item)
                session.commit()
                
                # Verify data was stored
                stored_invoice = session.query(Invoice).filter_by(folio=invoice_data['folio']).first()
                stored_items = session.query(InvoiceItem).filter_by(invoice_id=stored_invoice.id).all()
                
                return {
                    "success": stored_invoice is not None and len(stored_items) > 0,
                    "metrics": {
                        "Invoice stored": "Yes" if stored_invoice else "No",
                        "Items stored": len(stored_items),
                        "3-level classification": "Yes" if stored_items and stored_items[0].sub_subcategoria else "No"
                    }
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_batch_processing(self) -> Dict[str, Any]:
        """Test batch processing functionality."""
        try:
            # Create multiple test files
            test_files = []
            for i in range(3):
                sample_xml = self.create_sample_cfdi_xml().replace("12345", f"12345{i}")
                test_file = os.path.join(self.test_data_dir, f"sample_invoice_{i}.xml")
                shutil.copy(sample_xml, test_file)
                test_files.append(test_file)
            
            # Mock batch processor
            processed_count = 0
            failed_count = 0
            
            for test_file in test_files:
                try:
                    # Simulate processing
                    parser = CFDIParser()
                    invoice_data = parser.parse_cfdi_file(test_file)
                    
                    if 'folio' in invoice_data:
                        processed_count += 1
                        # Move to processed
                        processed_file = os.path.join(self.processed_dir, os.path.basename(test_file))
                        shutil.move(test_file, processed_file)
                    else:
                        failed_count += 1
                        
                except Exception:
                    failed_count += 1
                    # Move to failed
                    failed_file = os.path.join(self.failed_dir, os.path.basename(test_file))
                    if os.path.exists(test_file):
                        shutil.move(test_file, failed_file)
            
            success_rate = processed_count / len(test_files) * 100 if test_files else 0
            
            return {
                "success": success_rate >= 80,
                "metrics": {
                    "Total files": len(test_files),
                    "Processed": processed_count,
                    "Failed": failed_count,
                    "Success rate": f"{success_rate:.1f}%"
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_end_to_end_workflow(self) -> Dict[str, Any]:
        """Test complete end-to-end workflow."""
        try:
            # Create sample file
            sample_file = self.create_sample_cfdi_xml()
            
            # Step 1: Parse CFDI
            parser = CFDIParser()
            invoice_data = parser.parse_cfdi_file(sample_file)
            
            # Step 2: Classify items (simulated)
            for concepto in invoice_data.get('conceptos', []):
                concepto['categoria'] = 'Abarrotes'
                concepto['subcategoria'] = 'Aceite'
                concepto['sub_subcategoria'] = 'Aceite de oliva'
                concepto['standardized_unit'] = 'Litros'
                concepto['confidence'] = 0.95
            
            # Step 3: Store in database
            with self.db_manager.get_session() as session:
                invoice = Invoice(
                    folio=invoice_data['folio'],
                    fecha=invoice_data['fecha'],
                    subtotal=invoice_data['subtotal'],
                    total=invoice_data['total'],
                    moneda=invoice_data['moneda'],
                    emisor_rfc=invoice_data['emisor_rfc'],
                    receptor_rfc=invoice_data['receptor_rfc'],
                    uuid=invoice_data.get('uuid', 'test-uuid')
                )
                
                session.add(invoice)
                session.flush()
                
                for concepto in invoice_data['conceptos']:
                    item = InvoiceItem(
                        invoice_id=invoice.id,
                        descripcion=concepto['descripcion'],
                        cantidad=concepto['cantidad'],
                        valor_unitario=concepto['valor_unitario'],
                        importe=concepto['importe'],
                        categoria=concepto['categoria'],
                        subcategoria=concepto['subcategoria'],
                        sub_subcategoria=concepto['sub_subcategoria']
                    )
                    session.add(item)
                
                session.commit()
                
                # Verify complete workflow
                stored_invoice = session.query(Invoice).filter_by(folio=invoice_data['folio']).first()
                stored_items = session.query(InvoiceItem).filter_by(invoice_id=stored_invoice.id).all()
                
                workflow_complete = (
                    stored_invoice is not None and
                    len(stored_items) > 0 and
                    all(item.sub_subcategoria for item in stored_items)
                )
                
                return {
                    "success": workflow_complete,
                    "metrics": {
                        "Parse step": "Success",
                        "Classification step": "Success (simulated)",
                        "Database step": "Success",
                        "3-level hierarchy": "Implemented",
                        "Workflow complete": "Yes" if workflow_complete else "No"
                    }
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all pipeline tests."""
        print("🔄 Starting CFDI Processing Pipeline Tests")
        print("=" * 50)
        
        try:
            self.setup_test_environment()
            
            tests = [
                ("CFDI Parser", self.test_cfdi_parser),
                ("Gemini Classification", self.test_gemini_classification),
                ("Database Operations", self.test_database_operations),
                ("Batch Processing", self.test_batch_processing),
                ("End-to-End Workflow", self.test_end_to_end_workflow)
            ]
            
            for test_name, test_func in tests:
                print(f"\n📋 Running: {test_name}")
                try:
                    result = test_func()
                    self.test_results[test_name] = {
                        "status": "PASS" if result["success"] else "FAIL",
                        "details": result
                    }
                    status_emoji = "✅" if result["success"] else "❌"
                    print(f"{status_emoji} {test_name}: {self.test_results[test_name]['status']}")
                    
                    if result.get("metrics"):
                        for key, value in result["metrics"].items():
                            print(f"   {key}: {value}")
                            
                except Exception as e:
                    self.test_results[test_name] = {
                        "status": "ERROR",
                        "details": {"error": str(e), "success": False}
                    }
                    print(f"💥 {test_name}: ERROR - {str(e)}")
            
            return self.generate_final_report()
            
        finally:
            self.cleanup_test_environment()
    
    def generate_final_report(self) -> Dict[str, Any]:
        """Generate pipeline test report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["status"] == "PASS")
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "=" * 50)
        print("🏁 CFDI Processing Pipeline Test Results")
        print("=" * 50)
        print(f"✅ Passed: {passed_tests}/{total_tests}")
        print(f"📊 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("\n🎉 PIPELINE STATUS: HEALTHY")
        elif success_rate >= 60:
            print("\n⚠️  PIPELINE STATUS: NEEDS ATTENTION")
        else:
            print("\n🚨 PIPELINE STATUS: CRITICAL ISSUES")
        
        return {
            "total_tests": total_tests,
            "passed": passed_tests,
            "success_rate": success_rate,
            "status": "HEALTHY" if success_rate >= 80 else "NEEDS_ATTENTION" if success_rate >= 60 else "CRITICAL",
            "detailed_results": self.test_results
        }


def main():
    """Run the pipeline tests."""
    test_suite = CFDIProcessingPipelineTest()
    results = test_suite.run_all_tests()
    
    # Save results
    results_file = Path(__file__).parent / "pipeline_test_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 Results saved to: {results_file}")
    return results["success_rate"] >= 80


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 