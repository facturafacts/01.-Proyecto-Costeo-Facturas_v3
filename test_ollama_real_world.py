#!/usr/bin/env python3
"""
Quick test script for Ollama direct integration using real-world samples.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.processing.ollama_classifier import OllamaClassifier

def test_ollama_real_world():
    """Test direct Ollama integration with real-world samples."""
    try:
        print("🔄 Testing Ollama Direct Integration with Real-World Samples...")
        print("=" * 60)

        # Initialize classifier
        classifier = OllamaClassifier()

        # Show configuration
        stats = classifier.get_classification_statistics()
        print(f"📊 Model: {stats['model_name']}")
        print(f"🔗 Connection: {stats['connection_type']}")
        print(f"🎯 Model Optimized: {stats['model_optimized']}")
        print(f"⚙️ Config: {stats['model_config']}")
        print()

        # Test items with known correct classifications from processed XMLs
        samples = [
            # From previous test
            {
                'description': 'Cerveza Tecate 12 piezas', 'product_code': '75012345', 'unit_code': 'PZA', 'quantity': 1,
                'expected': {'category': 'Bebidas', 'subcategory': 'Cerveza', 'sub_sub_category': 'Nacional', 'standardized_unit': 'Piezas', 'units_per_package': 12.0}
            },
            {
                'description': 'Refresco Coca-Cola 600 ml', 'product_code': '75000001', 'unit_code': 'ML', 'quantity': 1,
                'expected': {'category': 'Bebidas', 'subcategory': 'Refrescos', 'sub_sub_category': 'Cola', 'standardized_unit': 'Piezas', 'units_per_package': 1.0}
            },
            # From 01DDB3AF-A3DC-48E1-B457-DD93751910C3.xml
            {
                'description': 'ZANAHORIA', 'product_code': '0120ZA', 'unit_code': 'KGM', 'quantity': 0.54,
                'expected': {'category': 'Vegetales', 'subcategory': 'Verduras', 'sub_sub_category': 'Zanahoria', 'standardized_unit': 'Kilogramos', 'units_per_package': 1.0}
            },
            {
                'description': 'CEBOLLA BLANCA', 'product_code': '0018CB', 'unit_code': 'KGM', 'quantity': 3.08,
                'expected': {'category': 'Vegetales', 'subcategory': 'Verduras', 'sub_sub_category': 'Cebolla Blanca', 'standardized_unit': 'Kilogramos', 'units_per_package': 1.0}
            },
            {
                'description': 'PIERNA DE POLLO', 'product_code': '46PP', 'unit_code': 'KGM', 'quantity': 1.34,
                'expected': {'category': 'Proteinas', 'subcategory': 'Pollo', 'sub_sub_category': 'Pierna', 'standardized_unit': 'Kilogramos', 'units_per_package': 1.0}
            },
            {
                'description': 'HARINA SELECTA', 'product_code': '0141HA', 'unit_code': 'H87', 'quantity': 3,
                'expected': {'category': 'Abarrotes', 'subcategory': 'Harinas', 'sub_sub_category': 'Harina de trigo', 'standardized_unit': 'Piezas', 'units_per_package': 1.0}
            },
            {
                'description': 'SOPA BARILLA ESPAGUETTI 500GR', 'product_code': '59SB', 'unit_code': 'H87', 'quantity': 1,
                'expected': {'category': 'Abarrotes', 'subcategory': 'Otros-a', 'sub_sub_category': 'Pasta', 'standardized_unit': 'Piezas', 'units_per_package': 1.0}
            },
            {
                'description': 'AGUACATE', 'product_code': '0002AG', 'unit_code': 'KGM', 'quantity': 0.46,
                'expected': {'category': 'Vegetales', 'subcategory': 'Frutas', 'sub_sub_category': 'Aguacate', 'standardized_unit': 'Kilogramos', 'units_per_package': 1.0}
            },
            {
                'description': 'PEPINO', 'product_code': '0091PE', 'unit_code': 'KGM', 'quantity': 0.5,
                'expected': {'category': 'Vegetales', 'subcategory': 'Verduras', 'sub_sub_category': 'Pepino Verde', 'standardized_unit': 'Kilogramos', 'units_per_package': 1.0}
            },
            # From 89159A29-A821-4C4F-BD54-DCA2988FF3CD.xml
            {
                'description': 'CREMA ACIDA LALA', 'product_code': '19CR', 'unit_code': 'H87', 'quantity': 1,
                'expected': {'category': 'Lacteos', 'subcategory': 'Cremas', 'sub_sub_category': 'Crema agria', 'standardized_unit': 'Piezas', 'units_per_package': 1.0}
            },
            {
                'description': 'CHILE POBLANO', 'product_code': '0036CP', 'unit_code': 'KGM', 'quantity': 0.66,
                'expected': {'category': 'Vegetales', 'subcategory': 'Verduras', 'sub_sub_category': 'Chile Poblano', 'standardized_unit': 'Kilogramos', 'units_per_package': 1.0}
            },
            {
                'description': 'PANCO', 'product_code': 'PANC', 'unit_code': 'KGM', 'quantity': 1,
                'expected': {'category': 'Panaderia', 'subcategory': 'Otros-p', 'sub_sub_category': 'Empanizador', 'standardized_unit': 'Piezas', 'units_per_package': 1.0}
            },
            # Stress test cases
            {
                'description': 'JABON ZOTE 400GR', 'product_code': 'JABZ', 'unit_code': 'H87', 'quantity': 5,
                'expected': {'category': 'Limpieza', 'subcategory': 'Jabones', 'sub_sub_category': 'Lavanderia', 'standardized_unit': 'Piezas', 'units_per_package': 1.0}
            },
            {
                'description': 'BOLSA DE PLASTICO', 'product_code': 'BOLS', 'unit_code': 'H87', 'quantity': 1,
                'expected': {'category': 'Desechables', 'subcategory': 'Bolsas', 'sub_sub_category': 'Plastico', 'standardized_unit': 'Piezas', 'units_per_package': 1.0}
            },
            {
                'description': 'PASTA DE MOÑO LA MODERNA', 'product_code': 'PASTMO', 'unit_code': 'H87', 'quantity': 2,
                'expected': {'category': 'Abarrotes', 'subcategory': 'Otros-a', 'sub_sub_category': 'Pasta', 'standardized_unit': 'Piezas', 'units_per_package': 1.0}
            },
            {
                'description': 'ACEITE 123 1LT', 'product_code': 'ACE123', 'unit_code': 'LTR', 'quantity': 12,
                'expected': {'category': 'Abarrotes', 'subcategory': 'Aceites', 'sub_sub_category': 'Aceite vegetal', 'standardized_unit': 'Piezas', 'units_per_package': 1.0}
            },
            {
                'description': 'QUESO OAXACA 400GR', 'product_code': 'QOAX', 'unit_code': 'H87', 'quantity': 3,
                'expected': {'category': 'Lacteos', 'subcategory': 'Quesos', 'sub_sub_category': 'Queso Oaxaca', 'standardized_unit': 'Piezas', 'units_per_package': 1.0}
            }
        ]

        def compare_result(result, expected):
            """Compare classification result with expected values."""
            matches = []
            for key, exp_val in expected.items():
                actual = result.get(key)
                matches.append(
                    f"     {key}: {actual} {'✓' if actual == exp_val else f'✗ (expected: {exp_val})'}"
                )
            return '\n'.join(matches)

        for idx, item in enumerate(samples, start=1):
            print(f"\n🧪 Sample {idx}:")
            print(f"   Description: {item['description']}")
            print(f"   Product Code: {item['product_code']}")
            result = classifier.classify_item(item)
            print("\n   → Result:")
            print(compare_result(result, item['expected']))
            print(f"     Source: {result['source']}")
            print(f"     Confidence: {result.get('confidence', 0):.2f}")

            if result['source'] == 'ollama_fallback':
                print("\n   ⚠️ Got fallback classification!")
                print("   This means the model's output couldn't be parsed as valid JSON.")
                print("   Check the prompt and model parameters.")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("\n🔍 Troubleshooting:")
        print("   1. Make sure Ollama is running: ollama serve")
        print("   2. Verify model is available: ollama list")
        print("   3. Check model name in .env file")
        print("   4. Try: ollama pull qwen2.5:3B")

if __name__ == "__main__":
    test_ollama_real_world()
