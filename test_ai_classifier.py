#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Test Script for the Pluggable AI Classifier System

This script tests the active AI classifier (Gemini or OpenAI) as configured
in the application settings. It runs a standardized set of real-world
test cases to benchmark accuracy and ensure consistent output.

To switch the model being tested, simply change the `AI_PROVIDER`
variable in your .env file (`gemini` or `openai`).
"""

import os
import sys
import unittest
import time
from unittest.mock import patch

# Ensure the project root is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import settings
from src.processing.ai_classifier import get_classifier, AIClassifier
from src.utils.logging_config import get_logger
from src.processing.cfdi_parser import CFDIParser

logger = get_logger(__name__)

# --- Test Data: 17 Real-World Samples ---
# This list is the benchmark for classifier performance.
REAL_WORLD_SAMPLES = [
    {'description': 'Cerveza Tecate 12 piezas', 'expected': {'category': 'Bebidas', 'subcategory': 'Cerveza', 'sub_sub_category': 'Nacional'}},
    {'description': 'Refresco Coca-Cola 600 ml', 'expected': {'category': 'Bebidas', 'subcategory': 'Refrescos', 'sub_sub_category': 'Cola'}},
    {'description': 'ZANAHORIA', 'expected': {'category': 'Vegetales', 'subcategory': 'Verduras', 'sub_sub_category': 'Zanahoria'}},
    {'description': 'CEBOLLA BLANCA', 'expected': {'category': 'Vegetales', 'subcategory': 'Verduras', 'sub_sub_category': 'Cebolla Blanca'}},
    {'description': 'PIERNA DE POLLO', 'expected': {'category': 'Proteinas', 'subcategory': 'Pollo', 'sub_sub_category': 'Pierna'}},
    {'description': 'HARINA SELECTA', 'expected': {'category': 'Abarrotes', 'subcategory': 'Harinas', 'sub_sub_category': 'Harina de trigo'}},
    {'description': 'SOPA BARILLA ESPAGUETTI 500GR', 'expected': {'category': 'Abarrotes', 'subcategory': 'Otros-a', 'sub_sub_category': 'Pasta'}},
    {'description': 'AGUACATE', 'expected': {'category': 'Vegetales', 'subcategory': 'Frutas', 'sub_sub_category': 'Aguacate'}},
    {'description': 'PEPINO', 'expected': {'category': 'Vegetales', 'subcategory': 'Verduras', 'sub_sub_category': 'Pepino Verde'}},
    {'description': 'CREMA ACIDA LALA', 'expected': {'category': 'Lacteos', 'subcategory': 'Cremas', 'sub_sub_category': 'Crema agria'}},
    {'description': 'CHILE POBLANO', 'expected': {'category': 'Vegetales', 'subcategory': 'Verduras', 'sub_sub_category': 'Chile Poblano'}},
    {'description': 'PANCO', 'expected': {'category': 'Panaderia', 'subcategory': 'Otros-p', 'sub_sub_category': 'Empanizador'}},
    {'description': 'JABON ZOTE 400GR', 'expected': {'category': 'Limpieza', 'subcategory': 'Jabones', 'sub_sub_category': 'Lavanderia'}},
    {'description': 'BOLSA DE PLASTICO', 'expected': {'category': 'Desechables', 'subcategory': 'Bolsas', 'sub_sub_category': 'Plastico'}},
    {'description': 'PASTA DE MOÑO LA MODERNA', 'expected': {'category': 'Abarrotes', 'subcategory': 'Otros-a', 'sub_sub_category': 'Pasta'}},
    {'description': 'ACEITE 123 1LT', 'expected': {'category': 'Abarrotes', 'subcategory': 'Aceite', 'sub_sub_category': 'Aceite vegetal'}},
    {'description': 'QUESO OAXACA 400GR', 'expected': {'category': 'Lacteos', 'subcategory': 'Queso', 'sub_sub_category': 'Queso Oaxaca'}}
]

class TestPluggableAiClassifier(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up the classifier once for all tests."""
        try:
            cls.classifier: AIClassifier = get_classifier()
            cls.provider_stats = cls.classifier.get_statistics()
            logger.info(f"Successfully initialized classifier: {cls.provider_stats}")
        except ValueError as e:
            logger.error(f"Failed to initialize classifier: {e}")
            logger.error("Please ensure AI_PROVIDER and corresponding API keys are set in your .env file.")
            cls.classifier = None

    def test_real_world_samples(self):
        """
        Tests the currently configured AI classifier against 17 real-world samples.
        """
        if not self.classifier:
            self.skipTest("Classifier could not be initialized. Skipping tests.")

        total_tests = len(REAL_WORLD_SAMPLES)
        passed_tests = 0
        
        print("\n" + "="*70)
        print(f"🔄 Testing AI Classifier: {self.provider_stats.get('provider', 'N/A').upper()}")
        print(f"🧠 Model: {self.provider_stats.get('model', 'N/A')}")
        print("="*70)

        for i, sample in enumerate(REAL_WORLD_SAMPLES):
            description = sample['description']
            expected = sample['expected']
            
            print(f"\n🧪 Sample {i+1}/{total_tests}: '{description}'")

            try:
                # Mock item_data structure
                item_data = {'description': description, 'unit_code': 'PZA'}
                result = self.classifier.classify_item(item_data)
                
                # --- Validation ---
                cat_ok = result.get('category') == expected['category']
                sub_ok = result.get('subcategory') == expected['subcategory']
                subsub_ok = result.get('sub_sub_category') == expected['sub_sub_category']

                print(f"   - Category:     {result.get('category')} {'✓' if cat_ok else '✗'} (Expected: {expected['category']})")
                print(f"   - Subcategory:  {result.get('subcategory')} {'✓' if sub_ok else '✗'} (Expected: {expected['subcategory']})")
                print(f"   - SubSubCat:    {result.get('sub_sub_category')} {'✓' if subsub_ok else '✗'} (Expected: {expected['sub_sub_category']})")
                
                if cat_ok and sub_ok and subsub_ok:
                    passed_tests += 1
                else:
                    print("   ------------------ ERROR ------------------")

            except Exception as e:
                print(f"   ----------------- API CALL FAILED -----------------")
                logger.error(f"API call failed for '{description}': {e}", exc_info=True)

            # --- Rate Limit Handling for Free Tier ---
            # The Gemini free tier allows 15 requests per minute (1 req / 4s).
            # We'll wait a bit longer to be safe.
            if i < total_tests - 1:
                time.sleep(4.1)


        print("\n" + "="*70)
        print("🎉 Test Complete!")
        accuracy = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"   - Passed: {passed_tests}/{total_tests}")
        print(f"   - Accuracy: {accuracy:.2f}%")
        print("="*70)
        
        # Make the test fail if accuracy is below a threshold, e.g., 90%
        self.assertGreaterEqual(accuracy, 90.0, "Classifier accuracy is below the 90% threshold.")

    def test_inbox_xml_files_end_to_end(self):
        """
        Performs an end-to-end test by parsing and classifying items from
        up to 5 XML files found in the configured INBOX_PATH.

        This is not an accuracy test, but a functional test to ensure the
        entire pipeline (parsing -> classifying) works with real data.
        """
        if not self.classifier:
            self.skipTest("Classifier could not be initialized. Skipping tests.")

        print("\n" + "="*70)
        print("🔄 Performing End-to-End Test from Inbox XMLs...")
        print(f"📂 Inbox Path: {settings.INBOX_PATH}")
        print("="*70)

        parser = CFDIParser()
        inbox_path = settings.INBOX_PATH
        
        if not os.path.exists(inbox_path) or not os.listdir(inbox_path):
            self.skipTest(f"Inbox directory is empty or does not exist. Skipping end-to-end test.")
            return

        xml_files = [f for f in os.listdir(inbox_path) if f.lower().endswith('.xml')][:5]

        if not xml_files:
            self.skipTest("No XML files found in the inbox. Skipping end-to-end test.")
            return
            
        print(f"Found {len(xml_files)} XML files to test. Processing...")

        for xml_file in xml_files:
            file_path = os.path.join(inbox_path, xml_file)
            print(f"\n📄 Processing File: {xml_file}")
            
            try:
                parsed_data = parser.parse_xml_file(file_path)
                items = parsed_data.get('items', [])
                self.assertGreater(len(items), 0, f"No items found in {xml_file}")

                print(f"   - Found {len(items)} items. Classifying...")

                for i, item in enumerate(items):
                    print(f"     - Item {i+1}: '{item.get('description', '')[:70]}...'")
                    
                    classification_result = self.classifier.classify_item(item)
                    
                    # Basic validation of the result structure
                    self.assertIn('category', classification_result)
                    self.assertIn('standardized_unit', classification_result)

                    print(f"       -> AI Result: {classification_result.get('category')} -> {classification_result.get('subcategory')} -> {classification_result.get('sub_sub_category')}")
                
                # Add rate-limiting delay between files
                time.sleep(4.1)

            except Exception as e:
                self.fail(f"End-to-end test failed for file {xml_file}: {e}")
        
        print("\n" + "="*70)
        print("🎉 End-to-End Test Complete!")
        print(f"   - Successfully parsed and classified items from {len(xml_files)} files.")
        print("="*70)


if __name__ == "__main__":
    unittest.main()
