# src/prompt_engineering.py

def create_unit_standardization_prompt(messy_units: list[str]) -> str:
    """
    Creates a detailed, engineered prompt for the LLM to standardize units for a recipe database.
    """
    units_as_string = ", ".join([f'"{unit}"' for unit in messy_units])

    prompt = f"""
You are an expert data cleaning assistant specializing in culinary data. Your task is to standardize a list of units of measure from a recipe database.

The standard units MUST be one of the following: 
- Gramos
- Mililitros
- Piezas
- Kilogramos
- Litros
- Cucharada
- Cucharadita
- Pizca
- A_gusto
- No_aplica (for junk values like 'RECETA' or '%')

Analyze the following list of messy units I found in the data:
[{units_as_string}]

RULES:
1.  You MUST return a valid JSON object.
2.  The keys of the JSON object must be the original messy units.
3.  The values must be the correct standard unit from the list above.
4.  Do NOT provide any explanation, comments, or introductory text. Only the raw JSON object.
5.  Pay attention to extra spaces or capitalization.
6.  If a unit is clearly not a real unit of measure (e.g., 'RECETA', 'CABEZA', '%', 'MEDIDA'), map it to 'No_aplica'.

Example output format:
{{
  "G": "Gramos",
  "g": "Gramos",
  " G": "Gramos",
  "KG": "Kilogramos",
  "pz": "Piezas",
  "PZ": "Piezas",
  "ML": "Mililitros",
  "Litro": "Litros",
  "Cucharadas": "Cucharada",
  "PIZCA": "Pizca",
  "RECETA": "No_aplica"
}}
"""
    return prompt

def create_unit_conversion_prompt(messy_units: list[str]) -> str:
    """
    Creates an advanced prompt for the LLM to standardize and provide conversion factors.
    """
    units_as_string = ", ".join([f'"{unit}"' for unit in messy_units])

    prompt = f"""
You are a world-class culinary data scientist. Your task is to analyze a list of messy units of measure from a recipe database and convert them to a strict, simplified standard.

THE ONLY VALID FINAL UNITS ARE:
- Kilogramos (for weight)
- Litros (for volume)
- Piezas (for count)

Analyze the following list of messy units:
[{units_as_string}]

RULES:
1.  You MUST return a valid JSON object where the keys are the original messy units.
2.  Each value must be another JSON object containing three fields: "proposed_standard", "conversion_factor", and "notes".
3.  `proposed_standard`: MUST be one of 'Kilogramos', 'Litros', or 'Piezas'.
4.  `conversion_factor`: A floating-point number representing how many of the FINAL standard units are in ONE of the original messy units. (e.g., for "Gramos", the factor is 0.001 because 1 gramo = 0.001 Kilogramos).
5.  `notes`: A brief explanation of your reasoning for the conversion. If no conversion is possible, explain why.
6.  For non-standard units (e.g., 'Cucharada', 'Pizca'), use your culinary knowledge to estimate a reasonable conversion to Litros or Kilogramos.
7.  For junk values ('RECETA', '%', 'MEDIDA') or units that cannot be converted (like 'CABEZA'), set `proposed_standard` to 'No_aplica', `conversion_factor` to 0, and explain why in the notes.
8.  Do NOT provide any text outside of the main JSON object.

EXAMPLE OUTPUT:
{{
  "G": {{
    "proposed_standard": "Kilogramos",
    "conversion_factor": 0.001,
    "notes": "Standard conversion from grams to kilograms."
  }},
  "pz": {{
    "proposed_standard": "Piezas",
    "conversion_factor": 1.0,
    "notes": "Assuming 'pz' is a direct mapping to 'Piezas'."
  }},
  "Cucharada": {{
    "proposed_standard": "Litros",
    "conversion_factor": 0.015,
    "notes": "Approximating a tablespoon as 15ml."
  }},
  "RECETA": {{
    "proposed_standard": "No_aplica",
    "conversion_factor": 0,
    "notes": "This is not a unit of measure."
  }}
}}
"""
    return prompt

def create_ingredient_matching_prompt(ingredients: list[str], skus: list[str]) -> str:
    """
    Creates a prompt to match recipe ingredients against a list of approved SKUs.
    """
    # TODO: Implement the full prompt template.
    prompt = f"Match these ingredients: {ingredients} to these SKUs: {skus}"
    return prompt

def create_hierarchy_labeling_prompt(product_list: list[str], df_sample_as_string: str) -> str:
    """
    Creates a prompt to classify each product into a recipe hierarchy.
    """
    product_list_as_string = ", ".join([f'"{p}"' for p in product_list])

    prompt = f"""
You are a master recipe ontologist. Your task is to analyze a list of recipe products and classify them into a three-level hierarchy: 'Recipe', 'Sub-recipe', or 'Sub-sub-recipe'.

Here is the complete list of all products that are made:
[{product_list_as_string}]

The relationship is defined as follows: A product is a sub-recipe if it is used as an ingredient for another product in the list.

Here is a sample of the data structure, showing the 'PRODUCTO' and 'INGREDIENTES' columns:
```
{df_sample_as_string}
```

RULES:
1.  Analyze the entire product list to understand the complete hierarchy.
2.  A 'Recipe' is a top-level item that is not an ingredient for any other product in the list.
3.  A 'Sub-recipe' is an ingredient for a 'Recipe'.
4.  A 'Sub-sub-recipe' is an ingredient for a 'Sub-recipe'.
5.  You MUST return a valid JSON object.
6.  The keys of the JSON object must be the product names from the list.
7.  The values must be one of the three strings: 'Recipe', 'Sub-recipe', or 'Sub-sub-recipe'.
8.  Do NOT provide any text or explanation outside of the JSON object.

EXAMPLE OUTPUT:
{{
  "PIZZA MARGHERITA": "Recipe",
  "MASA PIZZA (17pz)": "Sub-recipe",
  "MASA MADRE": "Sub-sub-recipe",
  "SALSA POMODORO": "Sub-recipe"
}}
"""
    return prompt

def create_name_standardization_prompt(name_list: list[str]) -> str:
    """
    Creates a prompt to standardize product and ingredient names.
    """
    name_list_as_string = ", ".join([f'"{name}"' for name in name_list])

    prompt = f"""
You are an expert in data cleaning and standardization for culinary databases. Your task is to homogenize a list of product and ingredient names.

The goal is to correct typos, expand abbreviations, remove extra whitespace, and create a single canonical name for items that are the same.

Analyze the following complete list of unique names:
[{name_list_as_string}]

RULES:
1.  You MUST return a valid JSON object.
2.  The keys of the JSON object must be the original, messy names from the list.
3.  The values must be the proposed, standardized name.
4.  If a name is already clean and correct, the value should be the same as the key.
5.  Do NOT provide any text, comments, or explanations outside of the single JSON object.

EXAMPLE OUTPUT:
{{
  "HARINA SIR LANCELOT": "Harina Sir Lancelot",
  "HARINA LANCELOT": "Harina Sir Lancelot",
  "   HARINA SIR LANCELOT   ": "Harina Sir Lancelot",
  "AGUA": "Agua",
  "MASA PIZZA (17pz)": "Masa Pizza"
}}
"""
    return prompt

def create_sku_matching_prompt(ingredient_name: str, sku_list_as_string: str) -> str:
    """
    Creates a prompt for the AI to find the best matching SKU for a single ingredient.
    """
    prompt = f"""
You are an expert procurement assistant for a culinary business. Your task is to find the single best-matching product from a list of approved SKUs for a given recipe ingredient.

The recipe ingredient is: "{ingredient_name}"

Here is the complete list of available SKUs you can choose from:
```
{sku_list_as_string}
```

RULES:
1.  Analyze the ingredient name and find the SKU that is the most logical and direct match.
2.  Consider brand names, product types, and descriptions. "Harina Sir Lancelot" is a better match for "HARINA LANCELOT" than a generic "HARINA DE TRIGO".
3.  You MUST return a valid JSON object.
4.  The JSON object must contain a single key, "best_match_sku", which is the `product_key` (SKU) of the item you have chosen from the list.
5.  If you are absolutely certain that no suitable match exists in the list, return a JSON object with the key "best_match_sku" and a value of "NO_MATCH_FOUND".
6.  Do NOT provide any text, comments, or explanations outside of the single JSON object.

EXAMPLE OUTPUT 1 (Successful Match):
{{
  "best_match_sku": "HARI-LAN-22.68"
}}

EXAMPLE OUTPUT 2 (No Match):
{{
  "best_match_sku": "NO_MATCH_FOUND"
}}
"""
    return prompt


