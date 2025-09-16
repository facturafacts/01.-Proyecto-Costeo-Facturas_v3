#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P62 Categories Utility Module for CFDI Processing System v4

Utility functions for managing P62 category taxonomy.
Handles conversion between flat sheet format and hierarchical JSON format.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class P62CategoriesManager:
    """Manages P62 category taxonomy operations."""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.categories_file = self.config_dir / "p62_categories.json"

    def load_categories_from_sheet_data(self, sheet_data: List[List[str]]) -> Dict:
        """
        Convert flat sheet data to hierarchical category structure.

        Args:
            sheet_data: List of [category, subcategory, sub_subcategory] rows

        Returns:
            Hierarchical categories dictionary
        """
        categories = {}

        for row in sheet_data:
            if len(row) >= 3 and all(cell.strip() for cell in row[:3]):
                category, subcategory, sub_subcategory = [cell.strip() for cell in row[:3]]

                # Build hierarchical structure
                if category not in categories:
                    categories[category] = {}

                if subcategory not in categories[category]:
                    categories[category][subcategory] = []

                if sub_subcategory not in categories[category][subcategory]:
                    categories[category][subcategory].append(sub_subcategory)

        return categories

    def generate_full_json(self, categories: Dict) -> Dict:
        """
        Generate complete P62 categories JSON structure.

        Args:
            categories: Hierarchical categories dictionary

        Returns:
            Complete JSON structure with standardized_units and unit_mappings
        """
        return {
            "categories": categories,
            "standardized_units": ["Litros", "Kilogramos", "Piezas"],
            "unit_mappings": {
                "liquids": ["LTR", "MLT", "LT", "L"],
                "weight": ["KGM", "GRM", "KG", "G", "TNE"],
                "pieces": ["H87", "PZA", "PZ", "UNI", "BOX", "BX", "E48"]
            },
            "prompts": {
                "classification_template": "You are a Mexican invoice item classifier. Classify this item into the EXACT 3-tier P62 category system.\n\nITEM TO CLASSIFY:\nDescription: \"{description}\"\nProduct Code: \"{product_code}\"\nUnit: \"{unit_code}\"\nQuantity: {quantity}\n\nSelect the EXACT category, subcategory, and sub_sub_category from the P62 system.\nAlso standardize the unit to: Litros (liquids), Kilogramos (weight), or Piezas (countable items).\n\nReturn ONLY this JSON format:\n{{\n  \"category\": \"EXACT_TIER_1_NAME\",\n  \"subcategory\": \"EXACT_TIER_2_NAME\", \n  \"sub_sub_category\": \"EXACT_TIER_3_NAME\",\n  \"standardized_unit\": \"Litros|Kilogramos|Piezas\",\n  \"confidence\": 0.95,\n  \"reasoning\": \"Brief explanation\"\n}}"
            }
        }

    def save_categories_json(self, categories: Dict, backup: bool = True) -> bool:
        """
        Save categories to JSON file.

        Args:
            categories: Hierarchical categories dictionary
            backup: Whether to create backup of existing file

        Returns:
            Success status
        """
        try:
            # Create backup if requested and file exists
            if backup and self.categories_file.exists():
                backup_file = self.config_dir / f"p62_categories.json.backup.{int(__import__('time').time())}"
                backup_file.write_text(self.categories_file.read_text())
                logger.info(f"Created backup: {backup_file}")

            # Ensure config directory exists
            self.config_dir.mkdir(exist_ok=True)

            # Generate and save full JSON structure
            full_json = self.generate_full_json(categories)
            self.categories_file.write_text(json.dumps(full_json, indent=2, ensure_ascii=False))

            logger.info(f"Successfully saved {len(categories)} categories to {self.categories_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save categories JSON: {e}")
            return False

    def load_current_categories(self) -> Dict:
        """
        Load current categories from JSON file.

        Returns:
            Categories dictionary or empty dict if file doesn't exist
        """
        try:
            if self.categories_file.exists():
                data = json.loads(self.categories_file.read_text())
                return data.get("categories", {})
            return {}
        except Exception as e:
            logger.error(f"Failed to load categories from JSON: {e}")
            return {}

    def validate_category_structure(self, categories: Dict) -> List[str]:
        """
        Validate category structure.

        Args:
            categories: Categories dictionary to validate

        Returns:
            List of validation errors
        """
        errors = []

        if not isinstance(categories, dict):
            errors.append("Categories must be a dictionary")
            return errors

        for category, subcategories in categories.items():
            if not isinstance(subcategories, dict):
                errors.append(f"Category '{category}' must have subcategories as dictionary")
                continue

            for subcategory, sub_subcategories in subcategories.items():
                if not isinstance(sub_subcategories, list):
                    errors.append(f"Subcategory '{subcategory}' in '{category}' must have sub-subcategories as list")
                    continue

                if not sub_subcategories:
                    errors.append(f"Subcategory '{subcategory}' in '{category}' has no sub-subcategories")

        return errors


def export_categories_to_json(sheet_data: List[List[str]]) -> str:
    """
    Export categories from sheet data to JSON format.

    Args:
        sheet_data: List of [category, subcategory, sub_subcategory] rows

    Returns:
        JSON string of the category structure
    """
    manager = P62CategoriesManager()
    categories = manager.load_categories_from_sheet_data(sheet_data)

    # Validate structure
    errors = manager.validate_category_structure(categories)
    if errors:
        raise ValueError(f"Invalid category structure: {errors}")

    full_json = manager.generate_full_json(categories)
    return json.dumps(full_json, indent=2, ensure_ascii=False)

