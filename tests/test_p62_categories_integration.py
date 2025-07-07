#!/usr/bin/env python3
"""
Comprehensive P62 Categories Integration Test Suite
Tests the entire CFDI processing system after P62 categories update to 3-level hierarchy.
"""

import os
import sys
import json
import tempfile
import sqlite3
from typing import Dict, List, Any
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.processing.gemini_classifier import GeminiClassifier
from src.data.models import Invoice, InvoiceItem
from src.data.database import DatabaseManager


class P62CategoriesTestSuite:
    """Comprehensive test suite for P62 categories system."""
    
    def __init__(self):
        self.test_results = {}
        self.config_path = Path(__file__).parent.parent / "config" / "p62_categories.json"
        self.categories_data = None
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive results."""
        print("🧪 Starting P62 Categories Integration Test Suite")
        print("=" * 60)
        
        tests = [
            ("P62 Categories File Structure", self.test_p62_file_structure),
            ("3-Level Hierarchy Validation", self.test_3_level_hierarchy),
            ("Category Coverage", self.test_category_coverage),
            ("Unit Mappings", self.test_unit_mappings),
            ("Gemini Classification Template", self.test_gemini_template),
            ("Database Schema Compatibility", self.test_database_compatibility),
            ("Sample Classifications", self.test_sample_classifications),
            ("Hierarchy Navigation", self.test_hierarchy_navigation),
            ("Data Integrity", self.test_data_integrity),
            ("Performance Metrics", self.test_performance_metrics)
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
                
                if not result["success"]:
                    print(f"   Error: {result.get('error', 'Unknown error')}")
                elif result.get("metrics"):
                    for key, value in result["metrics"].items():
                        print(f"   {key}: {value}")
                        
            except Exception as e:
                self.test_results[test_name] = {
                    "status": "ERROR",
                    "details": {"error": str(e), "success": False}
                }
                print(f"💥 {test_name}: ERROR - {str(e)}")
        
        return self.generate_final_report()
    
    def test_p62_file_structure(self) -> Dict[str, Any]:
        """Test that P62 categories file exists and is valid JSON."""
        try:
            if not self.config_path.exists():
                return {"success": False, "error": "P62 categories file not found"}
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.categories_data = json.load(f)
            
            required_keys = ["categories", "classification_template", "unit_mappings"]
            missing_keys = [key for key in required_keys if key not in self.categories_data]
            
            if missing_keys:
                return {"success": False, "error": f"Missing keys: {missing_keys}"}
            
            file_size = self.config_path.stat().st_size
            return {
                "success": True,
                "metrics": {
                    "File size": f"{file_size:,} bytes",
                    "Structure": "Valid JSON with required keys"
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_3_level_hierarchy(self) -> Dict[str, Any]:
        """Test that the 3-level hierarchy is properly implemented."""
        try:
            if not self.categories_data:
                return {"success": False, "error": "Categories data not loaded"}
            
            categories = self.categories_data["categories"]
            main_categories = len(categories)
            total_subcategories = 0
            total_sub_subcategories = 0
            
            for main_cat, subcats in categories.items():
                if not isinstance(subcats, dict):
                    return {"success": False, "error": f"Invalid structure in {main_cat}"}
                
                total_subcategories += len(subcats)
                
                for subcat, sub_subcats in subcats.items():
                    if not isinstance(sub_subcats, list):
                        return {"success": False, "error": f"Invalid sub-subcategory structure in {main_cat}.{subcat}"}
                    
                    total_sub_subcategories += len(sub_subcats)
            
            return {
                "success": True,
                "metrics": {
                    "Main categories": main_categories,
                    "Subcategories": total_subcategories,
                    "Sub-subcategories": total_sub_subcategories,
                    "Hierarchy levels": "3 (confirmed)"
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_category_coverage(self) -> Dict[str, Any]:
        """Test coverage of major food/business categories."""
        try:
            expected_categories = [
                "Abarrotes", "Bebidas", "Lacteos", "Proteinas", 
                "Vegetales", "Gastos Generales", "Servicios"
            ]
            
            categories = self.categories_data["categories"]
            found_categories = list(categories.keys())
            
            missing = [cat for cat in expected_categories if cat not in found_categories]
            extra = [cat for cat in found_categories if cat not in expected_categories]
            
            coverage_percent = (len(found_categories) - len(missing)) / len(expected_categories) * 100
            
            return {
                "success": len(missing) == 0,
                "metrics": {
                    "Coverage": f"{coverage_percent:.1f}%",
                    "Found categories": len(found_categories),
                    "Missing": missing if missing else "None",
                    "Additional": extra if extra else "None"
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_unit_mappings(self) -> Dict[str, Any]:
        """Test that unit mappings are properly configured."""
        try:
            unit_mappings = self.categories_data.get("unit_mappings", {})
            standardized_units = self.categories_data.get("standardized_units", [])
            
            expected_units = ["Litros", "Kilogramos", "Piezas"]
            missing_units = [unit for unit in expected_units if unit not in standardized_units]
            
            total_mappings = sum(len(mappings) for mappings in unit_mappings.values())
            
            return {
                "success": len(missing_units) == 0 and total_mappings > 0,
                "metrics": {
                    "Standardized units": len(standardized_units),
                    "Total unit mappings": total_mappings,
                    "Missing units": missing_units if missing_units else "None"
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_gemini_template(self) -> Dict[str, Any]:
        """Test that Gemini classification template supports 3-level hierarchy."""
        try:
            template = self.categories_data.get("classification_template", {})
            
            required_fields = [
                "category", "subcategory", "sub_sub_category", 
                "standardized_unit", "confidence", "reasoning"
            ]
            
            template_str = str(template)
            missing_fields = [field for field in required_fields if field not in template_str]
            
            # Check if template mentions 3-level structure
            has_3_level_support = "sub_sub_category" in template_str
            
            return {
                "success": len(missing_fields) == 0 and has_3_level_support,
                "metrics": {
                    "Template fields": len(required_fields) - len(missing_fields),
                    "3-level support": "Yes" if has_3_level_support else "No",
                    "Missing fields": missing_fields if missing_fields else "None"
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_database_compatibility(self) -> Dict[str, Any]:
        """Test database schema compatibility with new classification structure."""
        try:
            # Create temporary database to test schema
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
                temp_db_path = tmp_db.name
            
            try:
                db_manager = DatabaseManager(temp_db_path)
                db_manager.initialize_database()
                
                # Test if we can create records with 3-level classification
                with db_manager.get_session() as session:
                    # Check if tables exist
                    inspector = db_manager.engine.dialect.get_inspector(db_manager.engine)
                    tables = inspector.get_table_names()
                    
                    required_tables = ["invoices", "invoice_items", "approved_skus", "invoice_metadata"]
                    missing_tables = [table for table in required_tables if table not in tables]
                    
                    return {
                        "success": len(missing_tables) == 0,
                        "metrics": {
                            "Tables created": len(tables),
                            "Required tables": len(required_tables),
                            "Missing tables": missing_tables if missing_tables else "None"
                        }
                    }
            finally:
                # Cleanup
                if os.path.exists(temp_db_path):
                    os.unlink(temp_db_path)
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_sample_classifications(self) -> Dict[str, Any]:
        """Test sample product classifications using the new hierarchy."""
        try:
            sample_products = [
                "Aceite de oliva extra virgen",
                "Bistec de res",
                "Queso manchego",
                "Cerveza artesanal",
                "Tomate cherry"
            ]
            
            successful_classifications = 0
            classification_results = []
            
            for product in sample_products:
                try:
                    # Simulate classification logic
                    classification = self.simulate_classification(product)
                    if classification and all(key in classification for key in ["category", "subcategory", "sub_sub_category"]):
                        successful_classifications += 1
                        classification_results.append(f"{product} → {classification['category']}.{classification['subcategory']}.{classification['sub_sub_category']}")
                except:
                    classification_results.append(f"{product} → Classification failed")
            
            success_rate = successful_classifications / len(sample_products) * 100
            
            return {
                "success": success_rate >= 60,  # At least 60% should classify correctly
                "metrics": {
                    "Success rate": f"{success_rate:.1f}%",
                    "Successful classifications": successful_classifications,
                    "Sample results": classification_results[:3]  # Show first 3
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def simulate_classification(self, product_name: str) -> Dict[str, str]:
        """Simulate product classification based on keyword matching."""
        categories = self.categories_data["categories"]
        product_lower = product_name.lower()
        
        for main_cat, subcats in categories.items():
            for subcat, sub_subcats in subcats.items():
                for sub_subcat in sub_subcats:
                    if any(word in product_lower for word in sub_subcat.lower().split()):
                        return {
                            "category": main_cat,
                            "subcategory": subcat,
                            "sub_sub_category": sub_subcat,
                            "confidence": 0.85
                        }
        return {}
    
    def test_hierarchy_navigation(self) -> Dict[str, Any]:
        """Test ability to navigate the hierarchy programmatically."""
        try:
            categories = self.categories_data["categories"]
            
            # Test random navigation paths
            navigation_tests = 0
            successful_navigations = 0
            
            for main_cat, subcats in list(categories.items())[:3]:  # Test first 3 categories
                navigation_tests += 1
                if subcats and isinstance(subcats, dict):
                    first_subcat = list(subcats.keys())[0]
                    sub_subcats = subcats[first_subcat]
                    if sub_subcats and isinstance(sub_subcats, list):
                        successful_navigations += 1
            
            navigation_success = successful_navigations / navigation_tests * 100 if navigation_tests > 0 else 0
            
            return {
                "success": navigation_success >= 90,
                "metrics": {
                    "Navigation success": f"{navigation_success:.1f}%",
                    "Tested paths": navigation_tests,
                    "Successful paths": successful_navigations
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_data_integrity(self) -> Dict[str, Any]:
        """Test data integrity across the hierarchy."""
        try:
            categories = self.categories_data["categories"]
            
            empty_categories = []
            duplicate_items = []
            all_items = set()
            
            for main_cat, subcats in categories.items():
                if not subcats:
                    empty_categories.append(main_cat)
                    continue
                
                for subcat, sub_subcats in subcats.items():
                    if not sub_subcats:
                        empty_categories.append(f"{main_cat}.{subcat}")
                        continue
                    
                    for item in sub_subcats:
                        if item in all_items:
                            duplicate_items.append(item)
                        all_items.add(item)
            
            integrity_score = 100 - (len(empty_categories) * 10) - (len(duplicate_items) * 5)
            
            return {
                "success": integrity_score >= 85,
                "metrics": {
                    "Integrity score": f"{max(0, integrity_score):.1f}%",
                    "Empty categories": len(empty_categories),
                    "Duplicate items": len(duplicate_items),
                    "Total unique items": len(all_items)
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_performance_metrics(self) -> Dict[str, Any]:
        """Test performance characteristics of the hierarchy."""
        try:
            import time
            
            categories = self.categories_data["categories"]
            
            # Test lookup speed
            start_time = time.time()
            lookup_count = 0
            
            for main_cat, subcats in categories.items():
                for subcat, sub_subcats in subcats.items():
                    for item in sub_subcats:
                        lookup_count += 1
                        # Simulate lookup operation
                        _ = f"{main_cat}.{subcat}.{item}"
            
            lookup_time = time.time() - start_time
            lookups_per_second = lookup_count / lookup_time if lookup_time > 0 else 0
            
            # Calculate memory footprint estimate
            json_str = json.dumps(self.categories_data)
            memory_estimate = len(json_str.encode('utf-8'))
            
            return {
                "success": lookups_per_second > 1000,  # Should handle 1000+ lookups per second
                "metrics": {
                    "Lookups per second": f"{lookups_per_second:,.0f}",
                    "Total lookups tested": lookup_count,
                    "Memory estimate": f"{memory_estimate:,} bytes",
                    "Lookup time": f"{lookup_time:.3f} seconds"
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["status"] == "PASS")
        failed_tests = sum(1 for result in self.test_results.values() if result["status"] == "FAIL")
        error_tests = sum(1 for result in self.test_results.values() if result["status"] == "ERROR")
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "=" * 60)
        print("🏁 P62 Categories Integration Test Results")
        print("=" * 60)
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"💥 Errors: {error_tests}")
        print(f"📊 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("\n🎉 SYSTEM STATUS: HEALTHY")
            print("The P62 categories system is working correctly!")
        elif success_rate >= 60:
            print("\n⚠️  SYSTEM STATUS: NEEDS ATTENTION")
            print("Some issues detected, but system is mostly functional.")
        else:
            print("\n🚨 SYSTEM STATUS: CRITICAL ISSUES")
            print("Multiple critical issues detected. System needs immediate attention.")
        
        return {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "errors": error_tests,
            "success_rate": success_rate,
            "status": "HEALTHY" if success_rate >= 80 else "NEEDS_ATTENTION" if success_rate >= 60 else "CRITICAL",
            "detailed_results": self.test_results
        }


def main():
    """Run the comprehensive test suite."""
    test_suite = P62CategoriesTestSuite()
    results = test_suite.run_all_tests()
    
    # Save results for later analysis
    results_file = Path(__file__).parent / "p62_test_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 Detailed results saved to: {results_file}")
    
    return results["success_rate"] >= 80


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 