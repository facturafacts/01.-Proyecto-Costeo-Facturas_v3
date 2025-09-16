#!/usr/bin/env python3
"""
Quick test script for Ollama direct integration
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.processing.ollama_classifier import OllamaClassifier

def test_ollama_direct():
    """Test direct Ollama integration"""
    try:
        print("🔄 Testing Ollama Direct Integration...")
        print("=" * 50)

        # Initialize classifier
        classifier = OllamaClassifier()

        # Show configuration
        stats = classifier.get_classification_statistics()
        print(f"📊 Model: {stats['model_name']}")
        print(f"🔗 Connection: {stats['connection_type']}")
        print(f"🎯 DeepSeek Optimized: {stats['deepseek_optimized']}")
        print(f"⚙️ Config: {stats['model_config']}")
        print()

        # Test items with known correct classifications
        samples = [
            {
                'description': 'Cerveza Tecate 12 piezas',
                'product_code': '75012345',
                'unit_code': 'PZA',
                'quantity': 1,
                'expected': {
                    'category': 'Bebidas',
                    'subcategory': 'Cerveza',
                    'sub_sub_category': 'Cerveza Nacional',
                    'standardized_unit': 'Piezas',
                    'units_per_package': 12.0
                }
            },
            {
                'description': 'Refresco Coca-Cola 600 ml',
                'product_code': '75000001',
                'unit_code': 'ML',
                'quantity': 1,
                'expected': {
                    'category': 'Bebidas',
                    'subcategory': 'Refrescos',
                    'sub_sub_category': 'Refresco Cola',
                    'standardized_unit': 'Litros',
                    'units_per_package': 1.0
                }
            },
            {
                'description': 'Arroz blanco 1 kg',
                'product_code': '75000002',
                'unit_code': 'KG',
                'quantity': 1,
                'expected': {
                    'category': 'Abarrotes',
                    'subcategory': 'Cereales',
                    'sub_sub_category': 'Arroz',
                    'standardized_unit': 'Kilogramos',
                    'units_per_package': 1.0
                }
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
        print("   4. Try: ollama pull qwen3:1.7b")

if __name__ == "__main__":
    test_ollama_direct()