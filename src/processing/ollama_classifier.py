#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama Classifier for CFDI Processing System v4

Direct Python integration with Ollama for local AI classification.
Optimized for DeepSeek R1 1.5B model with no HTTP overhead.
"""

import json
import time
import re
import hashlib
import unicodedata
from typing import Dict, Any, Optional
from datetime import datetime
from difflib import get_close_matches

import ollama  # Direct Ollama Python client

from src.data.database import get_session
from src.data.models import ApprovedSku
from config.settings import settings
from src.utils.logging_config import get_logger


logger = get_logger(__name__)


class OllamaClassifier:
    """Direct Ollama classifier with DeepSeek R1 optimization.

    Features:
    - Direct Python integration (no HTTP overhead)
    - P62 3-tier taxonomy classification
    - Unit standardization (Litros, Kilogramos, Piezas)
    - Units per package determination
    - Confidence in [0, 1]
    - Approved SKU caching
    - Optimized for DeepSeek R1 1.5B model
    """

    def __init__(self) -> None:
        self.settings = settings
        self.get_session = get_session
        self.p62_categories = self._load_p62_categories()
        self._classification_cache: Dict[str, Dict[str, Any]] = {}

        # Direct Ollama client (no HTTP)
        self.client = ollama.Client()
        self.model = self.settings.OLLAMA_MODEL

        # Model-specific optimizations
        self._setup_model_optimizations()

        logger.info(f"OllamaClassifier initialized with model: {self.model}")

    def _setup_model_optimizations(self) -> None:
        """Set up model-specific optimizations."""
        model_name = (self.model or "").lower()
        if "qwen3" in model_name:
            # Qwen3 small models on CPU
            self.model_config = {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 180,
                "num_ctx": 2048,
                "num_thread": 4,
            }
            logger.info("Applied Qwen3 optimizations")
        elif "qwen2.5" in model_name:
            # Qwen2.5 3B instruct quantized: very fast + decent JSON
            self.model_config = {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 160,
                "num_ctx": 1536,
                "num_thread": 4,
            }
            logger.info("Applied Qwen2.5 optimizations")
        elif "llama3.1" in model_name or "llama3" in model_name:
            # Llama 3.1 8B instruct (q4_0) runs well on CPU and is a good instruction follower
            self.model_config = {
                "temperature": 0.0,
                "top_p": 0.9,
                "num_predict": 250,
                "num_ctx": 3072,
                "num_thread": 4,
            }
            logger.info("Applied Llama 3.1 optimizations")
        elif "llama3.2" in model_name:
            # Llama 3.2 3B instruct (q4_0) runs well on CPU
            self.model_config = {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 160,
                "num_ctx": 2048,
                "num_thread": 4,
            }
            logger.info("Applied Llama 3.2 optimizations")
        elif "gemma3:4b" in model_name or "gemma3" in model_name:
            # Gemma 3 4B tends to produce clean JSON; keep context modest
            self.model_config = {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 220,
                "num_ctx": 3072,
                "num_thread": 4,
            }
            logger.info("Applied Gemma 3 4B optimizations")
        elif "deepseek-r1" in model_name:
            # DeepSeek R1 1.5B optimizations
            self.model_config = {
                "temperature": 0.1,
                "top_p": 0.8,
                "num_predict": 200,
                "num_ctx": 2048,
                "num_thread": 4,
            }
            logger.info("Applied DeepSeek R1 optimizations")
        else:
            # Default optimizations for other models
            self.model_config = {
                "temperature": 0.1,
                "top_p": 0.8,
                "num_predict": 300,
                "num_ctx": 4096,
                "num_thread": 4,
            }
            logger.info("Using default model optimizations")

    def _load_p62_categories(self) -> Dict[str, Any]:
        """Load P62 categories from configuration file."""
        try:
            with open(self.settings.P62_CATEGORIES_PATH, 'r', encoding='utf-8') as f:
                categories = json.load(f)
            logger.info(f"Loaded P62 categories: {len(categories.get('categories', {}))} main categories")
            return categories
        except Exception as e:
            logger.error(f"Failed to load P62 categories: {e}")
            return {"categories": {}, "standardized_units": ["Litros", "Kilogramos", "Piezas"], "unit_mappings": {}}

    def generate_sku_key(self, description: str, product_code: Optional[str] = None) -> str:
        """Generate deterministic SKU key for caching and DB lookup."""
        normalized_desc = re.sub(r'[^\w\s]', '', (description or '').lower())
        normalized_desc = re.sub(r'\s+', '_', normalized_desc.strip())
        key_base = f"{product_code}_{normalized_desc}" if product_code else normalized_desc
        if len(key_base) > 200:
            key_base = key_base[:200]
        sku_hash = hashlib.md5(key_base.encode('utf-8')).hexdigest()[:8]
        return f"sku_{sku_hash}_{key_base[:50]}"

    def _find_best_match(self, value: str, valid_options: list[str], cutoff: float = 0.7) -> Optional[str]:
        """Find the best match for a value in a list of valid options using fuzzy matching."""
        if not value or not valid_options:
            return None
        
        # Normalize for better matching
        value_norm = value.lower().strip()
        options_norm = [opt.lower().strip() for opt in valid_options]
        
        # First, try a direct case-insensitive check
        for i, option_norm in enumerate(options_norm):
            if value_norm == option_norm:
                return valid_options[i]
                
        # Then, use get_close_matches
        matches = get_close_matches(value_norm, options_norm, n=1, cutoff=cutoff)
        
        if matches:
            original_index = options_norm.index(matches[0])
            return valid_options[original_index]
                
        return None

    def _build_hierarchy_display(self) -> str:
        """Build a human-readable P62 hierarchy section for the prompt."""
        lines = []
        for category, subcats in self.p62_categories.get("categories", {}).items():
            lines.append(f"📁 {category}:")
            if isinstance(subcats, dict):
                for subcat, subsubs in subcats.items():
                    lines.append(f"  📂 {subcat}:")
                    if isinstance(subsubs, list):
                        for s in subsubs:
                            lines.append(f"    📄 {s}")
                    else:
                        lines.append(f"    📄 {subsubs}")
            else:
                for subcat in subcats:
                    lines.append(f"  📂 {subcat}")
            lines.append("")
        return "\n".join(lines)

    def _build_step1_category_prompt(self, item_data: Dict[str, Any]) -> str:
        """Pass 1: Determine the top-level category."""
        categories = list(self.p62_categories.get("categories", {}).keys())
        prompt = f"""
You are an expert invoice item classifier for a Mexican grocery supplier.
Your task is to determine the single best top-level category for the given item.

ITEM DESCRIPTION: "{item_data.get('description', '')}"

VALID CATEGORIES:
{json.dumps(categories, indent=2)}

INSTRUCTIONS:
- Choose EXACTLY ONE category from the list above.
- Return ONLY the JSON object with your choice.

EXAMPLE:
Input: "Cerveza Tecate 12 piezas"
{{
  "category": "Bebidas"
}}

REQUIRED JSON RESPONSE:
{{
  "category": "EXACT_CATEGORY_NAME"
}}
"""
        return prompt

    def _build_step2_subcategory_prompt(self, item_data: Dict[str, Any], category: str) -> str:
        """Pass 2: Determine the sub-category within the chosen top-level category."""
        subcategories = list(self.p62_categories.get("categories", {}).get(category, {}).keys())
        prompt = f"""
You are an expert invoice item classifier.
The item's top-level category is "{category}". Now, determine the single best sub-category.

ITEM DESCRIPTION: "{item_data.get('description', '')}"

VALID SUB-CATEGORIES for "{category}":
{json.dumps(subcategories, indent=2)}

INSTRUCTIONS:
- YOU MUST choose exactly one sub-category from the list above.
- DO NOT invent a new sub-category or deviate from the provided list.
- Return ONLY the JSON object with your choice.

EXAMPLE:
Input: "Cerveza Tecate 12 piezas", Category: "Bebidas"
{{
  "subcategory": "Cerveza"
}}

REQUIRED JSON RESPONSE:
{{
  "subcategory": "EXACT_SUB_CATEGORY_NAME"
}}
"""
        return prompt

    def _build_step3_final_prompt(self, item_data: Dict[str, Any], category: str, subcategory: str) -> str:
        """Pass 3: Determine the final sub-sub-category and unit information."""
        sub_sub_categories = self.p62_categories.get("categories", {}).get(category, {}).get(subcategory, [])
        prompt = f"""
You are an expert invoice item classifier with deep knowledge of Mexican grocery items.
The item's category is "{category} -> {subcategory}". Now, complete the final classification with high precision.

ITEM:
Description: "{item_data.get('description', '')}"
Unit Code: "{item_data.get('unit_code', '')}"

VALID SUB-SUB-CATEGORIES for "{subcategory}":
{json.dumps(sub_sub_categories, indent=2)}

INSTRUCTIONS:
1.  Sub-Sub-Category: YOU MUST choose exactly one sub-sub-category from the list above. DO NOT invent a new one.
2.  Standardized Unit: Choose from ["Litros", "Kilogramos", "Piezas"].
    -   Use 'Piezas' for items sold as individual units, even if they have a weight or volume (e.g., a bottle of soda, a can of beer, a bag of flour, a tub of cream). Look for keywords like 'botella', 'lata', 'bolsa', 'paquete', 'pza'.
    -   Use 'Kilogramos' for bulk items sold by weight (e.g., fresh vegetables, meat, cheese from the deli).
    -   Use 'Litros' only for liquids not in standard consumer packages (e.g., bulk oil).
3.  Units per Package: Infer the number of units from the description (e.g., "12 piezas" -> 12.0). Default to 1.0 if not specified. **IMPORTANT: DO NOT use the weight or volume (e.g., '400' from '400GR') as the units per package. It must be a piece count.**
4.  Response: Return ONLY the JSON object with your final choices.

---
EXAMPLES:
1. Input: "Cerveza Tecate 12 piezas", Category: "Bebidas -> Cerveza"
   {{
     "sub_sub_category": "Nacional",
     "standardized_unit": "Piezas",
     "units_per_package": 12.0
   }}
2. Input: "Refresco Coca-Cola 600 ml", Category: "Bebidas -> Refrescos"
   {{
     "sub_sub_category": "Cola",
     "standardized_unit": "Piezas",
     "units_per_package": 1.0
   }}
3. Input: "SOPA BARILLA ESPAGUETTI 500GR", Category: "Abarrotes -> Otros-a"
   {{
     "sub_sub_category": "Pasta",
     "standardized_unit": "Piezas",
     "units_per_package": 1.0
   }}
4. Input: "PEPINO", Category: "Vegetales -> Verduras"
    {{
      "sub_sub_category": "Pepino Verde",
      "standardized_unit": "Kilogramos",
      "units_per_package": 1.0
    }}
5. Input: "CREMA ACIDA LALA", Category: "Lacteos -> Cremas"
    {{
      "sub_sub_category": "Crema agria",
      "standardized_unit": "Piezas",
      "units_per_package": 1.0
    }}
---

REQUIRED JSON RESPONSE:
{{
  "sub_sub_category": "EXACT_SUB_SUB_CATEGORY_NAME",
  "standardized_unit": "Litros|Kilogramos|Piezas",
  "units_per_package": 1.0
}}
"""
        return prompt

    def _extract_json_block(self, text: str) -> Optional[Dict[str, Any]]:
        """Attempt to extract the first valid JSON object from arbitrary text."""
        try:
            return json.loads(text)
        except Exception:
            pass
        # Remove code fences
        cleaned = text
        if cleaned.startswith('```json'):
            cleaned = cleaned.replace('```json', '').replace('```', '').strip()
        elif cleaned.startswith('```'):
            cleaned = cleaned.replace('```', '').strip()
        try:
            return json.loads(cleaned)
        except Exception:
            pass
        # Regex-based brace matching (simple heuristic)
        import re as _re
        candidates = _re.findall(r"\{[\s\S]*\}", cleaned)
        for c in candidates:
            try:
                return json.loads(c)
            except Exception:
                continue
        return None

    def _normalize_classification_keys(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize common key variants produced by small models to our schema."""
        if not isinstance(data, dict):
            return data
        # Unwrap common wrappers
        for wrap_key in ("result", "data", "output", "answer"):
            if isinstance(data.get(wrap_key), dict):
                data = data.get(wrap_key)
                break
        key_map = {
            # Category level 1
            "category_name": "category",
            "Category": "category",
            "tier1": "category",
            "level1": "category",
            "main_category": "category",
            # Subcategory level 2
            "subCategory": "subcategory",
            "subcategory_name": "subcategory",
            "tier2": "subcategory",
            "level2": "subcategory",
            # Sub-subcategory level 3
            "sub_subcategory": "sub_sub_category",
            "subSubCategory": "sub_sub_category",
            "tier3": "sub_sub_category",
            "level3": "sub_sub_category",
            # Units
            "unit": "standardized_unit",
            "standard_unit": "standardized_unit",
            "std_unit": "standardized_unit",
            "unit_of_measure": "standardized_unit",
            # Units per package
            "units": "units_per_package",
            "units_per_pack": "units_per_package",
            "units_pkg": "units_per_package",
            # Confidence
            "conf": "confidence",
            "confidence_score": "confidence",
        }
        normalized: Dict[str, Any] = {}
        for k, v in data.items():
            nk = key_map.get(k, k)
            normalized[nk] = v
        return normalized

    def _correct_and_validate_classification(
        self,
        description: str,
        category: str,
        subcategory: str,
        result3: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Takes the results of the 3-step AI classification and applies code-based
        validation, correction, and business logic rules.
        """
        
        # --- 1. Keyword-based Guards (Overrides everything) ---
        desc_norm = description.lower()
        if any(keyword in desc_norm for keyword in ["jabon", "zote", "foca", "roma"]):
            logger.warning(f"Applying keyword guard for 'Jabones' on '{description}'")
            return {
                'category': 'Limpieza', 'subcategory': 'Jabones', 'sub_sub_category': 'Lavanderia',
                'standardized_unit': 'Piezas', 'units_per_package': 1.0
            }
        if any(keyword in desc_norm for keyword in ["aceite"]):
            logger.warning(f"Applying keyword guard for 'Aceites' on '{description}'")
            return {
                'category': 'Abarrotes', 'subcategory': 'Aceites', 'sub_sub_category': 'Aceite vegetal',
                'standardized_unit': 'Piezas', 'units_per_package': 1.0
            }

        # --- 2. Path Correction & Validation ---
        sub_sub_category_guess = result3.get('sub_sub_category')
        
        # Find the correct path for the AI's guess
        found_path = self._find_correct_path(sub_sub_category_guess)
        if found_path:
            category, subcategory, sub_sub_category = found_path
            logger.info(f"Path corrected for '{sub_sub_category_guess}' to '{category} -> {subcategory} -> {sub_sub_category}'")
        else:
            # Fallback to original path and fuzzy match
            sub_sub_category = sub_sub_category_guess
            valid_sub_subs = self.p62_categories.get("categories", {}).get(category, {}).get(subcategory, [])
            if sub_sub_category not in valid_sub_subs:
                matched_sub_sub = self._find_best_match(sub_sub_category, valid_sub_subs)
                if matched_sub_sub:
                    logger.warning(f"Fuzzy match correction: '{sub_sub_category}' to '{matched_sub_sub}'.")
                    sub_sub_category = matched_sub_sub
                else:
                    logger.warning(f"Invalid sub_sub_category '{sub_sub_category}'. Defaulting.")
                    sub_sub_category = valid_sub_subs[0] if valid_sub_subs else 'Otros'

        # --- 3. Unit & Package Validation ---
        standardized_unit = result3.get('standardized_unit')
        if standardized_unit not in ["Litros", "Kilogramos", "Piezas"]:
             logger.warning(f"Invalid standardized_unit '{standardized_unit}'. Defaulting to 'Piezas'.")
             standardized_unit = 'Piezas'

        # Prevent weights from becoming units_per_package
        units_per_package = float(result3.get('units_per_package', 1.0))
        if units_per_package > 100: # Heuristic for weights like 400GR
            if any(unit in desc_norm for unit in ['gr', 'kg', 'ml', 'lt']):
                 logger.warning(f"Correcting high units_per_package '{units_per_package}' to 1.0 for item '{description}'.")
                 units_per_package = 1.0
             
        final_classification = {
            'category': category,
            'subcategory': subcategory,
            'sub_sub_category': sub_sub_category,
            'standardized_unit': standardized_unit,
            'units_per_package': units_per_package,
        }
        
        return final_classification

    def _find_correct_path(self, sub_sub_category_guess: str) -> Optional[tuple[str, str, str]]:
        """Search the entire P62 hierarchy for the best path for a given sub_sub_category guess."""
        if not sub_sub_category_guess:
            return None
            
        # First, find all possible paths for a fuzzy match of the guess
        possible_matches = []
        for cat, sub_cats in self.p62_categories.get("categories", {}).items():
            for sub_cat, sub_sub_cats in sub_cats.items():
                for sub_sub_cat in sub_sub_cats:
                    if sub_sub_category_guess.lower() in sub_sub_cat.lower() or \
                       get_close_matches(sub_sub_category_guess.lower(), [sub_sub_cat.lower()], n=1, cutoff=0.8):
                        possible_matches.append((cat, sub_cat, sub_sub_cat))
        
        if not possible_matches:
            return None
        
        # If there's an exact (case-insensitive) match, prioritize it
        for path in possible_matches:
            if sub_sub_category_guess.lower() == path[2].lower():
                return path

        # Otherwise, return the first fuzzy match
        return possible_matches[0]

    def call_ollama_direct(self, prompt: str, step: int) -> Dict[str, Any]:
        """Direct Ollama call with model-specific optimizations."""
        last_error = None
        for attempt in range(self.settings.OLLAMA_MAX_RETRIES):
            try:
                start = time.time()

                # Direct Ollama call (no HTTP overhead)
                response = self.client.generate(
                    model=self.model,
                    prompt=prompt,
                    format="json",
                    options=self.model_config,
                    stream=False
                )

                # Extract and clean response
                text = response.get('response', '').strip()

                # Parse JSON response (robust)
                result = self._extract_json_block(text)
                if result is None:
                    raise ValueError("Model did not return parseable JSON")

                # Normalize keys before validation
                result = self._normalize_classification_keys(result)
                result['processing_time'] = time.time() - start
                result['api_attempt'] = attempt + 1

                logger.info(f"Ollama step {step} success on attempt {attempt + 1}: {result}")
                return result

            except Exception as e:
                last_error = e
                logger.warning(f"Ollama step {step} attempt {attempt + 1} failed: {e}")
                if attempt < self.settings.OLLAMA_MAX_RETRIES - 1:
                    time.sleep((2 ** attempt) * 1)

        raise Exception(f"Ollama step {step} failed after {self.settings.OLLAMA_MAX_RETRIES} attempts: {last_error}")

    def get_approved_sku_classification(self, sku_key: str) -> Optional[Dict[str, Any]]:
        """Return approved classification if available, updating usage counters."""
        try:
            with self.get_session() as session:
                approved_sku = session.query(ApprovedSku).filter_by(sku_key=sku_key).first()
                if approved_sku:
                    approved_sku.usage_count += 1
                    approved_sku.last_used = datetime.utcnow()
                    return {
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
                return None
        except Exception as e:
            logger.error(f"Error checking approved SKU {sku_key}: {e}")
            return None

    def classify_item(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main classification method using a multi-step, sequential approach."""
        sku_key = self.generate_sku_key(
            item_data.get('description', ''),
            item_data.get('product_code')
        )

        if sku_key in self._classification_cache:
            logger.info(f"Using cached classification for {sku_key}")
            return self._classification_cache[sku_key]

        approved = self.get_approved_sku_classification(sku_key)
        if approved:
            self._classification_cache[sku_key] = approved
            return approved

        full_classification = {}
        total_time = 0.0

        try:
            # Step 1: Get Category
            logger.info(f"Step 1: Classifying category for '{item_data['description']}'")
            prompt1 = self._build_step1_category_prompt(item_data)
            result1 = self.call_ollama_direct(prompt1, step=1)
            category = result1.get('category')
            total_time += result1.get('processing_time', 0.0)
            if not category or category not in self.p62_categories.get("categories", {}):
                raise ValueError(f"Step 1 failed: Invalid or missing category '{category}'")
            full_classification['category'] = category

            # Step 2: Get Subcategory
            logger.info(f"Step 2: Classifying sub-category for '{item_data['description']}' (Category: {category})")
            prompt2 = self._build_step2_subcategory_prompt(item_data, category)
            result2 = self.call_ollama_direct(prompt2, step=2)
            subcategory = result2.get('subcategory')
            total_time += result2.get('processing_time', 0.0)
            if not subcategory or subcategory not in self.p62_categories.get("categories", {}).get(category, {}):
                raise ValueError(f"Step 2 failed: Invalid or missing subcategory '{subcategory}' for category '{category}'")
            full_classification['subcategory'] = subcategory
            
            # Step 3: Get Final Classification
            logger.info(f"Step 3: Finalizing classification for '{item_data['description']}' (Path: {category} -> {subcategory})")
            prompt3 = self._build_step3_final_prompt(item_data, category, subcategory)
            result3 = self.call_ollama_direct(prompt3, step=3)
            total_time += result3.get('processing_time', 0.0)
            
            # Final Correction & Validation Step (Code-based)
            final_data = self._correct_and_validate_classification(
                item_data['description'],
                category,
                subcategory,
                result3
            )
            
            full_classification.update({
                'sub_sub_category': final_data['sub_sub_category'],
                'standardized_unit': final_data['standardized_unit'],
                'units_per_package': final_data['units_per_package'],
                'confidence': 0.95,  # Higher confidence due to code validation
                'source': 'ollama_hybrid',
                'approval_status': 'pending',
                'sku_key': sku_key,
                'processing_time': total_time
            })
            
            self._classification_cache[sku_key] = full_classification
            logger.info(f"Hybrid classification successful for {sku_key}")
            return full_classification

        except Exception as e:
            logger.error(f"Multi-step classification failed for {sku_key}: {e}")
            return {
                'category': 'Abarrotes', 'subcategory': 'Otros-a', 'sub_sub_category': 'Otros',
                'standardized_unit': 'Piezas', 'units_per_package': 1.0,
                'confidence': 0.0, 'source': 'ollama_fallback', 'approval_status': 'pending',
                'sku_key': sku_key, 'processing_time': total_time, 'error': str(e)
            }

    def calculate_standardized_quantity(self, original_quantity: float, units_per_package: float) -> float:
        """Match helper signature used by pipeline."""
        return original_quantity * units_per_package

    def get_classification_statistics(self) -> Dict[str, Any]:
        """Expose statistics for diagnostics."""
        return {
            'cache_size': len(self._classification_cache),
            'model_name': self.model,
            'connection_type': 'direct_python_client',
            'model_config': self.model_config,
            'max_retries': self.settings.OLLAMA_MAX_RETRIES,
            'categories_loaded': len(self.p62_categories.get('categories', {})),
            'model_optimized': any(k in self.model.lower() for k in ['qwen', 'llama', 'gemma', 'deepseek'])
        }


