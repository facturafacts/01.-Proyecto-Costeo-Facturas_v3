#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemini Classifier for CFDI Processing System v4

Enhanced AI-powered classification system that performs:
1. 3-Tier P62 Classification (Category → Subcategory → Sub-subcategory)
2. Unit Standardization (Litros, Kilogramos, Piezas)
3. Units Per Package Determination (NEW)
4. Confidence Assessment

Follows v4 Enhanced Cursor Rules:
- Use existing Gemini API patterns
- Validate responses against expected schema
- Cache approved SKUs for performance
- Store conversion_factor and standardized_quantity
- Retry logic with 3 attempts and 30s timeout
"""

import json
import time
import logging
import hashlib
import re
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

import google.generativeai as genai
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential

from src.data.database import get_session
from src.data.models import ApprovedSku
from config.settings import settings
from src.utils.logging_config import get_logger

# --- Configuration ---
# Configure the generative AI model with the API key from settings
try:
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set. Please check your .env file.")
    genai.configure(api_key=settings.GEMINI_API_KEY)
    logging.info("Gemini AI configured successfully.")
except Exception as e:
    logging.error(f"Gemini AI configuration failed: {e}", exc_info=True)
    # The application might not function correctly without the classifier.
    # Depending on requirements, you might want to exit or run in a degraded mode.

# Configure logger
logger = get_logger(__name__)


class GeminiClassifier:
    """
    Enhanced Gemini classifier with units per package determination
    
    Features:
    - Full P62 3-tier taxonomy classification
    - Mexican unit standardization
    - Package size calculation
    - Confidence scoring
    - Approved SKU caching
    - Retry logic with exponential backoff
    """
    
    def __init__(self):
        """Initialize Gemini classifier with configuration and P62 categories."""
        self.settings = settings
        self.db_manager = get_session()
        
        # Initialize Gemini API
        self._initialize_gemini_api()
        
        # Load P62 categories
        self.p62_categories = self._load_p62_categories()
        
        # Classification cache
        self._classification_cache: Dict[str, Dict[str, Any]] = {}
        
        logger.info("GeminiClassifier initialized successfully")
    
    def _initialize_gemini_api(self) -> None:
        """Initialize Gemini API with configuration."""
        try:
            if not self.settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY not found in environment variables")
            
            # Configure Gemini
            genai.configure(api_key=self.settings.GEMINI_API_KEY)
            
            # Create model instance
            self.model = genai.GenerativeModel(
                model_name=self.settings.GEMINI_MODEL,
                generation_config={
                    'temperature': 0.1,  # Low temperature for consistent classification
                    'top_p': 0.8,
                    'top_k': 40,
                    'max_output_tokens': 1024,
                }
            )
            
            logger.info(f"Gemini API initialized with model: {self.settings.GEMINI_MODEL}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini API: {e}")
            raise
    
    def _load_p62_categories(self) -> Dict[str, Any]:
        """Load P62 categories from configuration."""
        try:
            with open(self.settings.P62_CATEGORIES_PATH, 'r', encoding='utf-8') as f:
                categories = json.load(f)
            
            logger.info(f"Loaded P62 categories: {len(categories.get('categories', {}))} main categories")
            return categories
            
        except Exception as e:
            logger.error(f"Failed to load P62 categories: {e}")
            return {"categories": {}, "standardized_units": [], "unit_mappings": {}}
    
    def generate_sku_key(self, description: str, product_code: Optional[str] = None) -> str:
        """
        Generate consistent SKU key for caching and lookup.
        
        Args:
            description: Item description
            product_code: SAT product code
            
        Returns:
            Normalized SKU key
        """
        # Normalize description
        normalized_desc = re.sub(r'[^\w\s]', '', description.lower())
        normalized_desc = re.sub(r'\s+', '_', normalized_desc.strip())
        
        # Include product code if available
        if product_code:
            key_base = f"{product_code}_{normalized_desc}"
        else:
            key_base = normalized_desc
        
        # Truncate if too long and add hash for uniqueness
        if len(key_base) > 200:
            key_base = key_base[:200]
        
        sku_hash = hashlib.md5(key_base.encode('utf-8')).hexdigest()[:8]
        return f"sku_{sku_hash}_{key_base[:50]}"
    
    def build_enhanced_gemini_prompt(self, item_data: Dict[str, Any]) -> str:
        """
        Build comprehensive Gemini prompt with complete 3-tier hierarchy display.
        
        Args:
            item_data: Item information from invoice
            
        Returns:
            Complete prompt for Gemini API with full hierarchy visibility
        """
        # Build complete 3-tier hierarchy for prompt
        hierarchy_text = self._build_hierarchy_display()
        
        prompt = f"""
You are a Mexican invoice item classifier. Classify this item into the EXACT 3-tier P62 category system below.

ITEM TO CLASSIFY:
Description: "{item_data.get('description', '')}"
Product Code: "{item_data.get('product_code', '')}"
Unit: "{item_data.get('unit_code', '')}"
Quantity: {item_data.get('quantity', 0)}

COMPLETE P62 TAXONOMY (3-TIER HIERARCHY):

{hierarchy_text}

MANDATORY 5-STEP CLASSIFICATION:

STEP 1 - CATEGORY (choose EXACTLY ONE from the 11 categories listed above):
You MUST select one of the main categories shown in the hierarchy above.

STEP 2 - SUBCATEGORY (choose EXACTLY ONE from your selected category):
You MUST select one of the subcategories listed under your chosen main category above.

STEP 3 - SUB_SUB_CATEGORY (choose EXACTLY ONE from the 428 pre-defined options):
You MUST select the most specific sub-subcategory from the list shown under your selected subcategory above.
CRITICAL: Do NOT create new sub-subcategory names. Choose ONLY from the exact sub-subcategories listed in the hierarchy (📄 items).
If no perfect match exists, choose the closest available option from the displayed list.

STEP 4 - STANDARDIZED UNIT (choose EXACTLY ONE):
- Litros (for all liquids, beverages, oils, etc.)
- Kilogramos (for all weight-based items, meat, vegetables, dry goods, etc.)
- Piezas (for countable items, services, individual units, packages, etc.)

STEP 5 - UNITS PER PACKAGE DETERMINATION:
Analyze the description to determine how many units are contained per package/container.

Examples:
- "Cebolla" with unit "KG" → units_per_package: 1 (sold by individual kg)
- "Caja cerveza tecate 24 piezas" with unit "Caja" → units_per_package: 24 (24 beers per box)
- "Aceite vegetal 1 litro" with unit "PZA" → units_per_package: 1 (1 liter per piece)
- "Huevos blancos paquete 12 piezas" → units_per_package: 12 (12 eggs per package)

Consider:
- Look for numbers in the description (24, 12, 6, etc.)
- Package keywords (caja, paquete, docena, etc.)
- If no package info is obvious, default to 1

CRITICAL INSTRUCTIONS FOR RESPONSE:
1. Use EXACT names from the hierarchy above (copy exactly, including accents and special characters)
2. For sub_sub_category: Choose ONLY from the 📄 items shown in the hierarchy
3. Return ONLY valid JSON format (no additional text, no markdown)

REQUIRED JSON RESPONSE FORMAT:
{{
  "category": "EXACT_TIER_1_NAME_FROM_HIERARCHY",
  "subcategory": "EXACT_TIER_2_NAME_FROM_HIERARCHY", 
  "sub_sub_category": "EXACT_TIER_3_NAME_FROM_HIERARCHY",
  "standardized_unit": "Litros|Kilogramos|Piezas",
  "units_per_package": numeric_value,
  "package_type": "description_of_package_type_or_null",
  "conversion_factor": numeric_value,
  "confidence": 0.95,
  "reasoning": "Brief explanation of classification and package determination"
}}

Where:
- units_per_package: Number of individual units in each package/container
- package_type: Type of packaging (Caja, Paquete, Botella, etc.) or null if individual
- conversion_factor: Same as units_per_package (for calculating total standardized quantity)
"""
        return prompt
    
    def _build_hierarchy_display(self) -> str:
        """
        Build a formatted display of the complete 3-tier P62 hierarchy.
        
        Returns:
            Formatted string showing Category → Subcategory → Sub-subcategories
        """
        hierarchy_lines = []
        
        for category, subcategories in self.p62_categories.get("categories", {}).items():
            hierarchy_lines.append(f"📁 {category}:")
            
            # Handle both old format (list) and new format (dict)
            if isinstance(subcategories, dict):
                # New 3-tier format
                for subcategory, sub_subcategories in subcategories.items():
                    hierarchy_lines.append(f"  📂 {subcategory}:")
                    if isinstance(sub_subcategories, list):
                        for sub_sub in sub_subcategories:
                            hierarchy_lines.append(f"    📄 {sub_sub}")
                    else:
                        hierarchy_lines.append(f"    📄 {sub_subcategories}")
            else:
                # Legacy 2-tier format (fallback)
                for subcategory in subcategories:
                    hierarchy_lines.append(f"  📂 {subcategory}")
            
            hierarchy_lines.append("")  # Empty line between categories
        
        return "\n".join(hierarchy_lines)
    
    def call_gemini_api(self, prompt: str) -> Dict[str, Any]:
        """
        Call Gemini API with retry logic and timeout handling.
        
        Args:
            prompt: Classification prompt
            
        Returns:
            Parsed classification response
            
        Raises:
            Exception: If all retries fail
        """
        last_exception = None
        
        for attempt in range(self.settings.GEMINI_MAX_RETRIES):
            try:
                start_time = time.time()
                
                # Generate content
                response = self.model.generate_content(prompt)
                
                processing_time = time.time() - start_time
                
                # Extract and clean response text
                response_text = response.text.strip()
                
                # Remove markdown code blocks if present
                if response_text.startswith('```json'):
                    response_text = response_text.replace('```json', '').replace('```', '').strip()
                elif response_text.startswith('```'):
                    response_text = response_text.replace('```', '').strip()
                
                # Parse JSON response
                classification = json.loads(response_text)
                
                # Validate required fields
                required_fields = [
                    'category', 'subcategory', 'sub_sub_category', 
                    'standardized_unit', 'units_per_package', 'confidence'
                ]
                
                for field in required_fields:
                    if field not in classification:
                        raise ValueError(f"Missing required field: {field}")
                
                # Validate and clean data
                classification = self._validate_and_clean_response(classification)
                classification['processing_time'] = processing_time
                classification['api_attempt'] = attempt + 1
                
                logger.info(f"Gemini API success on attempt {attempt + 1}: {classification['category']} -> {classification['subcategory']}")
                return classification
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Gemini API attempt {attempt + 1} failed: {e}")
                
                # Exponential backoff for retries
                if attempt < self.settings.GEMINI_MAX_RETRIES - 1:
                    wait_time = (2 ** attempt) * 1  # 1, 2, 4 seconds
                    time.sleep(wait_time)
        
        # All retries failed
        logger.error(f"Gemini API failed after {self.settings.GEMINI_MAX_RETRIES} attempts: {last_exception}")
        raise Exception(f"Gemini API failed after {self.settings.GEMINI_MAX_RETRIES} attempts: {last_exception}")
    
    def _validate_and_clean_response(self, classification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean Gemini response data.
        
        Args:
            classification: Raw classification response
            
        Returns:
            Validated and cleaned classification
        """
        # Validate standardized unit
        valid_units = self.p62_categories.get("standardized_units", ["Litros", "Kilogramos", "Piezas"])
        if classification.get('standardized_unit') not in valid_units:
            logger.warning(f"Invalid unit '{classification.get('standardized_unit')}', defaulting to 'Piezas'")
            classification['standardized_unit'] = 'Piezas'
        
        # Validate and clean units_per_package
        try:
            units_per_package = float(classification.get('units_per_package', 1))
            if units_per_package <= 0:
                units_per_package = 1.0
        except (ValueError, TypeError):
            units_per_package = 1.0
        
        classification['units_per_package'] = units_per_package
        
        # Set conversion_factor (same as units_per_package for most cases)
        classification['conversion_factor'] = classification.get('conversion_factor', units_per_package)
        
        # Validate confidence score
        try:
            confidence = float(classification.get('confidence', 0.5))
            confidence = max(0.0, min(1.0, confidence))  # Clamp between 0-1
        except (ValueError, TypeError):
            confidence = 0.5
        
        classification['confidence'] = confidence
        
        # Validate category exists in P62
        valid_categories = list(self.p62_categories.get("categories", {}).keys())
        if classification.get('category') not in valid_categories:
            logger.warning(f"Invalid category '{classification.get('category')}', defaulting to 'Abarrotes'")
            classification['category'] = 'Abarrotes'
            classification['subcategory'] = 'Otros-a'
            classification['sub_sub_category'] = 'Otros'
        else:
            # Validate subcategory and sub-subcategory exist in the hierarchy
            category = classification.get('category')
            subcategory = classification.get('subcategory')
            sub_sub_category = classification.get('sub_sub_category')
            
            category_data = self.p62_categories.get("categories", {}).get(category, {})
            
            # Validate subcategory
            if isinstance(category_data, dict):
                if subcategory not in category_data:
                    logger.warning(f"Invalid subcategory '{subcategory}' for category '{category}'")
                    # Use first available subcategory
                    subcategory = list(category_data.keys())[0] if category_data else 'Otros-a'
                    classification['subcategory'] = subcategory
                
                # Validate sub-subcategory
                subcategory_data = category_data.get(subcategory, [])
                if isinstance(subcategory_data, list):
                    if sub_sub_category not in subcategory_data:
                        logger.warning(f"Invalid sub-subcategory '{sub_sub_category}' for '{category} -> {subcategory}'")
                        # Use first available sub-subcategory
                        sub_sub_category = subcategory_data[0] if subcategory_data else 'Otros'
                        classification['sub_sub_category'] = sub_sub_category
        
        return classification
    
    def get_approved_sku_classification(self, sku_key: str) -> Optional[Dict[str, Any]]:
        """
        Check for approved SKU classification in database.
        
        Args:
            sku_key: Generated SKU key
            
        Returns:
            Approved classification if found, None otherwise
        """
        try:
            with self.db_manager as session:
                # Query approved SKU
                approved_sku = session.query(ApprovedSku).filter_by(sku_key=sku_key).first()
                
                if approved_sku:
                    # Update usage tracking
                    approved_sku.usage_count += 1
                    approved_sku.last_used = datetime.utcnow()
                    
                    classification = {
                        'category': approved_sku.category,
                        'subcategory': approved_sku.subcategory,
                        'sub_sub_category': approved_sku.sub_sub_category,
                        'standardized_unit': approved_sku.standardized_unit,
                        'units_per_package': float(approved_sku.units_per_package or 1.0),
                        'package_type': approved_sku.package_type,
                        'conversion_factor': float(approved_sku.units_per_package or 1.0),
                        'confidence': float(approved_sku.confidence_score or 1.0),
                        'source': 'approved_sku',
                        'approval_status': 'approved',
                        'sku_key': sku_key,
                        'processing_time': 0.0
                    }
                    
                    logger.info(f"Using approved SKU: {sku_key} -> {classification['category']}")
                    return classification
                
                return None
                
        except Exception as e:
            logger.error(f"Error checking approved SKU {sku_key}: {e}")
            return None
    
    def classify_item(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main classification method with SKU caching and Gemini API.
        
        Args:
            item_data: Item information from invoice
            
        Returns:
            Complete classification result
        """
        # Generate SKU key
        sku_key = self.generate_sku_key(
            item_data.get('description', ''),
            item_data.get('product_code')
        )
        
        # Check cache first
        if sku_key in self._classification_cache:
            logger.info(f"Using cached classification: {sku_key}")
            return self._classification_cache[sku_key]
        
        # Check approved SKUs in database
        approved_classification = self.get_approved_sku_classification(sku_key)
        if approved_classification:
            self._classification_cache[sku_key] = approved_classification
            return approved_classification
        
        # Call Gemini API for new classification
        try:
            logger.info(f"Calling Gemini API for new item: {sku_key}")
            
            prompt = self.build_enhanced_gemini_prompt(item_data)
            classification = self.call_gemini_api(prompt)
            
            # Add metadata
            classification.update({
                'source': 'gemini_api',
                'approval_status': 'pending',
                'sku_key': sku_key
            })
            
            # Cache result
            self._classification_cache[sku_key] = classification
            
            logger.info(f"Gemini classification complete: {classification['category']} -> {classification['subcategory']} (units_per_package: {classification['units_per_package']})")
            return classification
            
        except Exception as e:
            logger.error(f"Classification failed for {sku_key}: {e}")
            
            # Return fallback classification
            fallback = {
                'category': 'Abarrotes',
                'subcategory': 'Otros-a',
                'sub_sub_category': 'Otros',
                'standardized_unit': 'Piezas',
                'units_per_package': 1.0,
                'package_type': None,
                'conversion_factor': 1.0,
                'confidence': 0.0,
                'source': 'fallback',
                'approval_status': 'pending',
                'sku_key': sku_key,
                'processing_time': 0.0,
                'error': str(e)
            }
            
            return fallback
    
    def calculate_standardized_quantity(self, original_quantity: float, units_per_package: float) -> float:
        """
        Calculate standardized quantity based on package information.
        
        Args:
            original_quantity: Quantity from invoice
            units_per_package: Units per package from classification
            
        Returns:
            Standardized quantity
        """
        return original_quantity * units_per_package
    
    def validate_classification_response(self, classification: Dict[str, Any]) -> bool:
        """
        Validate classification response against schema.
        
        Args:
            classification: Classification result
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            'category', 'subcategory', 'sub_sub_category',
            'standardized_unit', 'units_per_package', 'confidence'
        ]
        
        # Check required fields
        for field in required_fields:
            if field not in classification:
                logger.error(f"Missing required field: {field}")
                return False
        
        # Validate data types and ranges
        try:
            confidence = float(classification['confidence'])
            if not 0.0 <= confidence <= 1.0:
                logger.error(f"Invalid confidence score: {confidence}")
                return False
            
            units_per_package = float(classification['units_per_package'])
            if units_per_package <= 0:
                logger.error(f"Invalid units_per_package: {units_per_package}")
                return False
            
            return True
            
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid data types in classification: {e}")
            return False
    
    def get_classification_statistics(self) -> Dict[str, Any]:
        """
        Get classification statistics for monitoring.
        
        Returns:
            Statistics dictionary
        """
        return {
            'cache_size': len(self._classification_cache),
            'model_name': self.settings.GEMINI_MODEL,
            'max_retries': self.settings.GEMINI_MAX_RETRIES,
            'timeout': self.settings.GEMINI_TIMEOUT,
            'categories_loaded': len(self.p62_categories.get('categories', {}))
        } 