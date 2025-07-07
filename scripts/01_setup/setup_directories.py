#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Directory Setup Script for CFDI Processing System v4

This script creates all necessary directories for the CFDI processing system.
Must be run before processing any XML files.
"""

import os
import sys
from pathlib import Path
from typing import List


def create_directory_structure() -> None:
    """Create all required directories for the CFDI processing system."""
    
    print("📁 Setting up CFDI Processing System v4 Directory Structure")
    print("=" * 65)
    
    # Define all required directories
    directories: List[str] = [
        # Data processing directories
        "data/inbox",           # XML files to be processed
        "data/processed",       # Successfully processed XML files
        "data/failed",          # Failed processing XML files
        "data/database",        # SQLite database location
        
        # Log directories
        "logs",                 # Application logs
        
        # Analysis directories 
        "notebooks",            # Jupyter notebooks for analysis
        
        # Test directories
        "tests/fixtures",       # Test data and sample files
        
        # Additional directories that might be needed
        "temp",                 # Temporary files during processing
        "backups",              # Database backups
    ]
    
    created_dirs = []
    existing_dirs = []
    
    # Create each directory
    for directory in directories:
        dir_path = Path(directory)
        
        if dir_path.exists():
            existing_dirs.append(directory)
            print(f"   ✅ Already exists: {directory}")
        else:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                created_dirs.append(directory)
                print(f"   🆕 Created: {directory}")
            except Exception as e:
                print(f"   ❌ Failed to create {directory}: {e}")
    
    # Create .gitkeep files to preserve empty directories in git
    gitkeep_dirs = [
        "data/inbox",
        "data/processed", 
        "data/failed",
        "logs",
        "temp"
    ]
    
    print(f"\n📄 Creating .gitkeep files...")
    for directory in gitkeep_dirs:
        gitkeep_path = Path(directory) / ".gitkeep"
        try:
            gitkeep_path.touch()
            print(f"   ✅ Created: {gitkeep_path}")
        except Exception as e:
            print(f"   ❌ Failed to create {gitkeep_path}: {e}")
    
    # Summary
    print(f"\n" + "=" * 65)
    print(f"📊 DIRECTORY SETUP SUMMARY")
    print(f"   🆕 Created: {len(created_dirs)} directories")
    print(f"   ✅ Existing: {len(existing_dirs)} directories") 
    print(f"   📁 Total: {len(directories)} directories")
    
    if created_dirs:
        print(f"\n🆕 New directories created:")
        for directory in created_dirs:
            print(f"   • {directory}")
    
    if existing_dirs:
        print(f"\n✅ Existing directories:")
        for directory in existing_dirs:
            print(f"   • {directory}")


def create_sample_env_file() -> None:
    """Create a sample .env file if it doesn't exist."""
    env_path = Path("config/.env")
    
    if env_path.exists():
        print(f"\n⚙️  Environment file already exists: {env_path}")
        return
    
    print(f"\n⚙️  Creating sample environment file...")
    
    env_content = """# CFDI Processing System v4 - Environment Configuration
# IMPORTANT: Update GEMINI_API_KEY with your actual API key

# Environment (dev, test, prod)
ENVIRONMENT=dev
DEBUG=True

# API Configuration - *** UPDATE THIS ***
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash
GEMINI_TIMEOUT=30
GEMINI_MAX_RETRIES=3

# Database Configuration  
DATABASE_URL=sqlite:///data/database/cfdi_system_v4.db
DATABASE_ECHO=False

# File Paths (automatically created by this script)
INBOX_PATH=data/inbox
PROCESSED_PATH=data/processed
FAILED_PATH=data/failed
LOGS_PATH=logs

# P62 Configuration
P62_CATEGORIES_PATH=config/p62_categories.json

# Processing Configuration
BATCH_SIZE=10
MAX_FILE_SIZE_MB=50
PROCESSING_TIMEOUT=300

# Currency Configuration
DEFAULT_CURRENCY=MXN

# Logging Configuration
LOG_LEVEL=INFO
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5

# Performance Configuration
ENABLE_PROFILING=True
MEMORY_LIMIT_MB=512

# Security Configuration
ENCRYPT_LOGS=False
"""
    
    try:
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print(f"   ✅ Created: {env_path}")
        print(f"   ⚠️  IMPORTANT: Update GEMINI_API_KEY in {env_path}")
    except Exception as e:
        print(f"   ❌ Failed to create {env_path}: {e}")


def create_sample_xml() -> None:
    """Create a sample XML file for testing."""
    sample_xml_path = Path("data/inbox/sample_test.xml")
    
    if sample_xml_path.exists():
        print(f"\n📄 Sample XML already exists: {sample_xml_path}")
        return
    
    print(f"\n📄 Creating sample test XML file...")
    
    sample_xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" 
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.sat.gob.mx/cfd/4 http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd"
    Version="4.0"
    Serie="A"
    Folio="TEST123"
    Fecha="2024-01-15T10:30:00"
    Sello="sample_seal"
    NoCertificado="00001000000123456789"
    Certificado="sample_certificate"
    SubTotal="1000.00"
    Descuento="0.00"
    Moneda="MXN"
    TipoCambio="1"
    Total="1160.00"
    TipoDeComprobante="I"
    Exportacion="01"
    MetodoPago="PUE"
    LugarExpedicion="06000">
    
    <cfdi:Emisor 
        Rfc="AAA010101AAA" 
        Nombre="Empresa de Prueba SA de CV"
        RegimenFiscal="601"/>
    
    <cfdi:Receptor 
        Rfc="BBB020202BBB" 
        Nombre="Cliente de Prueba SA de CV"
        DomicilioFiscalReceptor="06000"
        RegimenFiscalReceptor="601"
        UsoCFDI="G03"/>
    
    <cfdi:Conceptos>
        <cfdi:Concepto 
            ClaveProdServ="01010101"
            NoIdentificacion="CERV001"
            Cantidad="3"
            ClaveUnidad="H87"
            Unidad="Caja"
            Descripcion="Caja cerveza tecate 24 piezas"
            ValorUnitario="200.00"
            Importe="600.00"
            Descuento="0.00"
            ObjetoImp="02">
            <cfdi:Impuestos>
                <cfdi:Traslados>
                    <cfdi:Traslado Base="600.00" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="96.00"/>
                </cfdi:Traslados>
            </cfdi:Impuestos>
        </cfdi:Concepto>
        
        <cfdi:Concepto 
            ClaveProdServ="01010102"
            NoIdentificacion="VEG001"
            Cantidad="5"
            ClaveUnidad="KGM"
            Unidad="Kilogramo"
            Descripcion="Cebolla blanca"
            ValorUnitario="25.00"
            Importe="125.00"
            Descuento="0.00"
            ObjetoImp="02">
            <cfdi:Impuestos>
                <cfdi:Traslados>
                    <cfdi:Traslado Base="125.00" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="20.00"/>
                </cfdi:Traslados>
            </cfdi:Impuestos>
        </cfdi:Concepto>
        
        <cfdi:Concepto 
            ClaveProdServ="01010103"
            NoIdentificacion="HUEV001"
            Cantidad="2"
            ClaveUnidad="PZA"
            Unidad="Pieza"
            Descripcion="Huevos blancos paquete 12 piezas"
            ValorUnitario="45.00"
            Importe="90.00"
            Descuento="0.00"
            ObjetoImp="02">
            <cfdi:Impuestos>
                <cfdi:Traslados>
                    <cfdi:Traslado Base="90.00" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="14.40"/>
                </cfdi:Traslados>
            </cfdi:Impuestos>
        </cfdi:Concepto>
        
        <cfdi:Concepto 
            ClaveProdServ="01010104"
            NoIdentificacion="ACEIT001"
            Cantidad="4"
            ClaveUnidad="PZA"
            Unidad="Pieza"
            Descripcion="Aceite vegetal 1 litro"
            ValorUnitario="35.00"
            Importe="140.00"
            Descuento="0.00"
            ObjetoImp="02">
            <cfdi:Impuestos>
                <cfdi:Traslados>
                    <cfdi:Traslado Base="140.00" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="22.40"/>
                </cfdi:Traslados>
            </cfdi:Impuestos>
        </cfdi:Concepto>
        
        <cfdi:Concepto 
            ClaveProdServ="80161500"
            NoIdentificacion="SERV001"
            Cantidad="1"
            ClaveUnidad="E48"
            Unidad="Servicio"
            Descripcion="Servicio de entrega"
            ValorUnitario="45.00"
            Importe="45.00"
            Descuento="0.00"
            ObjetoImp="02">
            <cfdi:Impuestos>
                <cfdi:Traslados>
                    <cfdi:Traslado Base="45.00" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="7.20"/>
                </cfdi:Traslados>
            </cfdi:Impuestos>
        </cfdi:Concepto>
    </cfdi:Conceptos>
    
    <cfdi:Impuestos TotalImpuestosTrasladados="160.00">
        <cfdi:Traslados>
            <cfdi:Traslado Base="1000.00" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="160.00"/>
        </cfdi:Traslados>
    </cfdi:Impuestos>
    
    <cfdi:Complemento>
        <tfd:TimbreFiscalDigital 
            xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
            Version="1.1"
            UUID="12345678-1234-1234-1234-123456789012"
            FechaTimbrado="2024-01-15T10:35:00"
            RfcProvCertif="SAT970701NN3"
            SelloCFD="sample_seal_cfd"
            NoCertificadoSAT="00001000000987654321"/>
    </cfdi:Complemento>
    
</cfdi:Comprobante>'''
    
    try:
        with open(sample_xml_path, 'w', encoding='utf-8') as f:
            f.write(sample_xml_content)
        print(f"   ✅ Created: {sample_xml_path}")
        print(f"   📝 This XML contains 5 test items perfect for testing units per package:")
        print(f"      • Caja cerveza tecate 24 piezas (should detect 24 units per caja)")
        print(f"      • Cebolla blanca (should detect 1 unit per kg)")
        print(f"      • Huevos blancos paquete 12 piezas (should detect 12 units per package)")
        print(f"      • Aceite vegetal 1 litro (should detect 1 liter per piece)")
        print(f"      • Servicio de entrega (should detect 1 unit for service)")
    except Exception as e:
        print(f"   ❌ Failed to create {sample_xml_path}: {e}")


def display_next_steps() -> None:
    """Display next steps for the user."""
    print(f"\n" + "🚀" * 25)
    print(f"NEXT STEPS - READY FOR TESTING")
    print(f"🚀" * 25)
    print(f"\n1️⃣  UPDATE API KEY:")
    print(f"   📝 Edit config/.env")
    print(f"   🔑 Set GEMINI_API_KEY=your_actual_api_key")
    
    print(f"\n2️⃣  INITIALIZE DATABASE:")
    print(f"   💾 python main.py --setup")
    
    print(f"\n3️⃣  TEST THE SYSTEM:")
    print(f"   🧪 python main.py --file data/inbox/sample_test.xml")
    
    print(f"\n4️⃣  PROCESS MULTIPLE FILES:")
    print(f"   📁 Drop your XML files in: data/inbox/")
    print(f"   ▶️  Run: python main.py")
    
    print(f"\n5️⃣  ANALYZE RESULTS:")
    print(f"   📊 Create Jupyter notebook in: notebooks/")
    print(f"   🔍 Query database: data/database/cfdi_system_v4.db")
    
    print(f"\n📂 WHERE TO DROP XML FILES:")
    print(f"   📥 data/inbox/           ← PUT YOUR XML FILES HERE")
    print(f"   ✅ data/processed/       ← Successfully processed files")
    print(f"   ❌ data/failed/          ← Failed files")
    print(f"   💾 data/database/        ← SQLite database")
    print(f"   📝 logs/                 ← Processing logs")


def main():
    """Main setup function."""
    try:
        # Create directory structure
        create_directory_structure()
        
        # Create sample environment file
        create_sample_env_file()
        
        # Create sample XML for testing
        create_sample_xml()
        
        # Display next steps
        display_next_steps()
        
        print(f"\n✅ DIRECTORY SETUP COMPLETE!")
        print(f"   The CFDI Processing System v4 is ready for configuration and testing.")
        
    except Exception as e:
        print(f"\n❌ SETUP FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 