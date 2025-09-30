#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pluggable AI Classifier System for CFDI Processing v4

This module provides a flexible, multi-provider AI classification engine.
It uses a factory pattern to select and instantiate a classifier (e.g., Gemini,
OpenAI) based on the application's configuration settings.

This centralizes all AI provider logic, making it easy to add, remove, or
switch between models without changing the core application code.

Features:
- Abstract Base Class (`AIClassifier`) to enforce a standard interface.
- Concrete implementations for Google Gemini and OpenAI.
- `get_classifier()` factory for easy, configuration-driven instantiation.
- Simplified, robust prompts optimized for modern, instruction-following models.
"""

import json
import time
import abc
import os
import re
import hashlib
from typing import Dict, Any, Optional

import google.generativeai as genai
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


# --- 1. Abstract Base Class (The Standard Interface) ---

class AIClassifier(abc.ABC):
    """
    Abstract Base Class for all AI classifiers.

    Defines a standard contract that all concrete classifier implementations
    (Gemini, OpenAI, etc.) must follow. This ensures that the main application
    can interact with any classifier in a consistent way.
    """

    @abc.abstractmethod
    def classify_item(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classifies a single invoice item.

        This is the primary method that the application will call.

        Args:
            item_data: A dictionary containing item details from the invoice
                       (e.g., 'description', 'product_code', 'unit_code').

        Returns:
            A dictionary containing the structured classification result.
        """
        pass

    @abc.abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """
        Returns diagnostic information about the classifier's configuration.
        """
        pass

    def generate_sku_key(self, description: str, product_code: Optional[str] = None) -> str:
        """
        Generates a consistent, normalized key for an item.
        This is a shared utility method inherited by all classifiers.
        
        Correction: Ensures components are sorted for deterministic output.
        """
        # 1. Normalize and clean the description
        normalized_desc = re.sub(r'\W+', '_', description.lower()).strip('_')
        
        # 2. Create a list of key components
        components = [normalized_desc]
        if product_code:
            components.append(str(product_code))
            
        # 3. Sort components to ensure order is always the same
        components.sort()
        
        # 4. Join sorted components to create the base key
        key_base = "_".join(components)
        
        # 5. Truncate and hash for a manageable and unique key
        truncated_key = key_base[:100]
        key_hash = hashlib.md5(key_base.encode('utf-8')).hexdigest()[:8]
        
        return f"sku_{key_hash}_{truncated_key}"


# --- 2. Concrete Implementations (The "Plug-ins") ---

class GeminiClassifier(AIClassifier):
    """
    AI Classifier implementation using Google's Gemini API.
    """

    def __init__(self):
        self._initialize_api()
        self.p62_categories_text = self._load_p62_text()
        logger.info("✅ GeminiClassifier initialized.")

    def _initialize_api(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            generation_config={'temperature': 0.1, 'top_p': 0.9}
        )
        logger.info(f"Gemini API configured with model: {settings.GEMINI_MODEL}")

    def _load_p62_text(self) -> str:
        try:
            with open(settings.P62_CATEGORIES_PATH, 'r', encoding='utf-8') as f:
                return json.dumps(json.load(f), ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to load P62 categories: {e}")
            return "{}"

    def build_prompt(self, item_data: Dict[str, Any]) -> str:
        return f"""
        Analyze the invoice item below and classify it according to the provided P62 JSON taxonomy.

        ITEM:
        - Description: "{item_data.get('description', '')}"
        - Unit: "{item_data.get('unit_code', '')}"

        P62 TAXONOMY:
        {self.p62_categories_text}

        INSTRUCTIONS:
        1.  Determine the 3-tier classification (category, subcategory, sub_sub_category) by selecting the most appropriate terms from the P62 TAXONOMY.
        2.  Determine the standardized_unit: Choose ONLY from ["Litros", "Kilogramos", "Piezas"]. Use 'Piezas' for packaged goods (e.g., a bottle of soda, a bag of flour).
        3.  Determine the units_per_package: The number of items in a pack (e.g., "12 pack" -> 12.0). Default to 1.0. Do NOT confuse weight/volume with this value.
        4.  Provide a confidence score from 0.0 to 1.0.

        CRITICAL BUSINESS RULES (Follow these examples exactly):
        - "JABON ZOTE" is a laundry soap, it MUST be classified as {{"category": "Limpieza", "subcategory": "Jabones", "sub_sub_category": "Lavanderia"}}. Do NOT use 'Suministros'.
        - "BOLSA DE PLASTICO" is a disposable item, it MUST be classified as {{"category": "Desechables", "subcategory": "Bolsas", "sub_sub_category": "Plastico"}}. Do NOT use 'Suministros'.
        - "PANCO" is a breading, it MUST be classified as {{"category": "Panaderia", "subcategory": "Otros-p", "sub_sub_category": "Empanizador"}}.
        - "CHILE POBLANO" is a vegetable, it MUST be classified as {{"category": "Vegetales", "subcategory": "Verduras", "sub_sub_category": "Chile Poblano"}}.

        Your response MUST be a single, valid JSON object and nothing else.

        JSON RESPONSE FORMAT:
        {{
            "category": "...",
            "subcategory": "...",
            "sub_sub_category": "...",
            "standardized_unit": "...",
            "units_per_package": 1.0,
            "confidence": 0.9
        }}
        """

    @retry(stop=stop_after_attempt(settings.GEMINI_MAX_RETRIES), wait=wait_exponential(multiplier=1, min=2, max=10))
    def classify_item(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self.build_prompt(item_data)
        response = self.model.generate_content(prompt)
        
        # Clean the response to extract only the JSON object
        response_text = response.text.strip()
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            raise ValueError("No valid JSON object found in Gemini response.")
        
        classification = json.loads(json_match.group(0))
        
        # --- BUG FIX: Generate and add the sku_key ---
        sku_key = self.generate_sku_key(
            item_data.get('description', ''),
            item_data.get('product_code')
        )
        classification['sku_key'] = sku_key
        # --- End Bug Fix ---
        
        return classification

    def get_statistics(self) -> Dict[str, Any]:
        return {"provider": "gemini", "model": settings.GEMINI_MODEL}


class OpenAIClassifier(AIClassifier):
    """
    AI Classifier implementation using OpenAI's API.
    """

    def __init__(self):
        self._initialize_api()
        self.p62_categories_text = self._load_p62_text()
        logger.info("✅ OpenAIClassifier initialized.")

    def _initialize_api(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set.")
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=settings.OPENAI_TIMEOUT)
        logger.info(f"OpenAI API configured with model: {settings.OPENAI_MODEL}")

    def _load_p62_text(self) -> str:
        try:
            with open(settings.P62_CATEGORIES_PATH, 'r', encoding='utf-8') as f:
                return json.dumps(json.load(f), ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to load P62 categories: {e}")
            return "{}"

    def build_messages(self, item_data: Dict[str, Any]) -> list:
        system_prompt = f"""
        You are an expert at classifying Mexican invoice items.
        Your task is to analyze an item and return a structured JSON response based on the provided P62 taxonomy.
        You must adhere strictly to the JSON format and the categories provided.

        P62 TAXONOMY:
        {self.p62_categories_text}

        CRITICAL BUSINESS RULES (Follow these examples exactly):
        - "JABON ZOTE" is a laundry soap, it MUST be classified as {{"category": "Limpieza", "subcategory": "Jabones", "sub_sub_category": "Lavanderia"}}. Do NOT use 'Suministros'.
        - "BOLSA DE PLASTICO" is a disposable item, it MUST be classified as {{"category": "Desechables", "subcategory": "Bolsas", "sub_sub_category": "Plastico"}}. Do NOT use 'Suministros'.
        - "PANCO" is a breading, it MUST be classified as {{"category": "Panaderia", "subcategory": "Otros-p", "sub_sub_category": "Empanizador"}}.
        - "CHILE POBLANO" is a vegetable, it MUST be classified as {{"category": "Vegetales", "subcategory": "Verduras", "sub_sub_category": "Chile Poblano"}}.
        """
        user_prompt = f"""
        Classify the following item.

        ITEM:
        - Description: "{item_data.get('description', '')}"
        - Unit: "{item_data.get('unit_code', '')}"

        INSTRUCTIONS:
        1.  Determine the 3-tier classification from the P62 TAXONOMY.
        2.  Determine standardized_unit: ["Litros", "Kilogramos", "Piezas"]. Use 'Piezas' for packaged goods.
        3.  Determine units_per_package. Default to 1.0. Do not confuse with weight/volume.
        4.  Provide a confidence score (0.0 to 1.0).

        JSON RESPONSE FORMAT:
        {{
            "category": "...",
            "subcategory": "...",
            "sub_sub_category": "...",
            "standardized_unit": "...",
            "units_per_package": 1.0,
            "confidence": 0.9
        }}
        """
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    @retry(stop=stop_after_attempt(settings.OPENAI_MAX_RETRIES), wait=wait_exponential(multiplier=1, min=2, max=10))
    def classify_item(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        messages = self.build_messages(item_data)
        response = self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        classification = json.loads(response.choices[0].message.content)

        # --- BUG FIX: Generate and add the sku_key ---
        sku_key = self.generate_sku_key(
            item_data.get('description', ''),
            item_data.get('product_code')
        )
        classification['sku_key'] = sku_key
        # --- End Bug Fix ---

        return classification

    def get_statistics(self) -> Dict[str, Any]:
        return {"provider": "openai", "model": settings.OPENAI_MODEL}


# --- 3. The Factory Function ---

def get_classifier() -> AIClassifier:
    """
    Factory function to get the configured AI classifier.

    Reads the `AI_PROVIDER` setting and returns an instance of the
    corresponding classifier.

    Returns:
        An instance of a class that inherits from AIClassifier.

    Raises:
        ValueError: If the configured AI_PROVIDER is unknown.
    """
    provider = settings.AI_PROVIDER.lower()
    logger.info(f"Attempting to initialize AI provider: '{provider}'")

    if provider == "gemini":
        return GeminiClassifier()
    elif provider == "openai":
        return OpenAIClassifier()
    else:
        raise ValueError(f"Unknown AI_PROVIDER configured: '{provider}'. Please use 'gemini' or 'openai'.")
