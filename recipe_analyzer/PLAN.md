# Recipe Analyzer Development Plan (v9)

This version is the complete, detailed, and actionable plan, restoring all previously deleted details.

## Executive Summary
- **End Goal**: A trustworthy, repeatable “Should Cost” report (and Google Sheets UI) that costs every sold item using clean SKUs, sub-recipes, and complete recipes.
- **How We Get There**:
  1. **Phase 0**: Load menu and known recipes from Excel.
  2. **Phase 1**: Clean, consolidate, and standardize SKUs.
  3. **Phase 2**: Define sub-recipes with yields.
  4. **Phase 3**: Complete final recipes linking SKUs/sub-recipes.
  5. **Phase 4**: Compute Should Cost and deliver dashboards/Sheets.
- **Key Rules**:
  - Recipes for every sellable item.
  - Recipe status lifecycle: `UNDEFINED` → `IN_PROGRESS` → `DEFINED` → `ARCHIVED`.
  - Yield-first sub-recipes: explicit output quantity/unit (+ optional loss %).
  - Costing rule: use latest standardized unit price on/before sales date; for same-nature SKUs, default to the latest purchase (overrideable).
  - Tenant-aware: `client_rfc` on all recipe domain tables.

---

## Phase 0 — Detailed Breakdown: Initial Data Load via Excel
- **Objective**: To safely and accurately migrate all sellable menu items and known recipe data from user-populated Excel templates into the new database tables.
- **Agent**: `01_Initial_Data_Loader.ipynb`
- **End Goal Alignment**: This phase creates the foundational dataset. Without a complete list of all sellable items, the "Should Cost" report in Phase 4 cannot calculate its "Coverage Score".

### Executable Items for Phase 0
1.  **Generate Intelligent Excel Templates**: The agent will create three `.xlsx` files (`final_recipes_template.xlsx`, `sub_recipes_template.xlsx`, `sku_nature_mapping.xlsx`) with headers, data validation rules, and instructional tabs.
2.  **Implement Pre-Import Validator (Dry Run)**: The agent will read the user-filled templates and produce a clear validation report, checking for referential integrity, uniqueness, unit compatibility, and other errors before touching the database.
3.  **Implement Database Import Logic**: The agent will insert validated data using atomic transactions to prevent partial data and will be idempotent (re-runnable without creating duplicates).

### Milestone for Phase 0
Complete when the `01_Initial_Data_Loader.ipynb` agent can generate templates, validate a sample file, and successfully import a clean file into the database.

---

## Phase 1 — Detailed Breakdown: SKU Validation
- **Objective**: To ensure all SKUs used in costing have standardized units and prices with no duplicates, so that all cost calculations are correct and repeatable.
- **Agent**: `02_SKU_Validation_Agent.ipynb`
- **End Goal Alignment**: This phase provides the clean, reliable raw material data that is the ultimate foundation of any accurate cost calculation in Phase 4.

### Executable Items for Phase 1
1.  **Detect Duplicates and Gaps**: Scan `approved_skus` for duplicates using text similarity and for items missing `standardized_unit` or `units_per_package`.
2.  **Guided Consolidation**: For each duplicate group, prompt the user to select a primary SKU, defaulting to the one with the most recent purchase.
3.  **Update and Refresh**: Update the `approved_skus` table (marking duplicates as inactive) and create/refresh materialized views (`latest_sku_price`) for fast price lookups.

### Milestone for Phase 1
Complete when the agent can identify and guide the user through consolidating duplicate SKUs and the price look-up views are populated.

---

## Phase 2 — Detailed Breakdown: Sub-Recipe & Yield Definition
- **Objective**: To define all sub-recipes (porciones) with explicit, measurable yields, so that the cost of prepared ingredients can be accurately rolled up into final recipes.
- **Agent**: `03_Portioning_Agent.ipynb`
- **End Goal Alignment**: This phase bridges the gap between raw materials and final dishes. Correctly costing sub-recipes is critical for an accurate final "Should Cost" number.

### Executable Items for Phase 2
1.  **Identify Unknown Components**: Scan `recipe_components` to find ingredients that are neither a valid SKU nor a defined sub-recipe.
2.  **Interactive Sub-Recipe Creation**: For each "Unknown," guide the user through a wizard to define its ingredients (by selecting from clean SKUs), quantities, and, most importantly, the final `output_quantity` and `output_unit` to calculate yield.
3.  **Validate and Save**: Check for issues like circular dependencies before saving the new sub-recipe and its components to the database.

### Milestone for Phase 2
Complete when the agent can successfully guide a user to create a new sub-recipe, with its components and yield correctly saved to the database.

---

## Phase 3 — Detailed Breakdown: Recipe Completion
- **Objective**: To move all high-priority recipes to a `DEFINED` status by linking them to their constituent SKUs and sub-recipes, ensuring every sold item has a complete and trustworthy cost path.
- **Agent**: `04_Recipe_Completion_Agent.ipynb`
- **End Goal Alignment**: This phase directly builds the complete recipe trees that the Phase 4 report relies on, maximizing the "Coverage Score" of the final report.

### Executable Items for Phase 3
1.  **Prioritize Incomplete Recipes**: Query the database for recipes with a status of `UNDEFINED` or `IN_PROGRESS` and join with sales data to rank them by revenue impact.
2.  **Component Linking Interface**: For each recipe, provide an interface that allows the user to add components, with autocomplete suggestions pulling from the clean `approved_skus` and `sub_recipes` tables.
3.  **Finalize and Version**: Once all components are linked, update the recipe's status to `DEFINED`. Optionally, save a snapshot of the completed recipe to the `recipe_versions` table for auditing.

### Milestone for Phase 3
Complete when the agent can be used to take a high-revenue, `UNDEFINED` recipe and successfully transition it to `DEFINED` status.

---

## Phase 4 — Detailed Breakdown: "Should Cost" Reporting & Google Sheets
- **Objective**: To produce the final, actionable "Should Cost" report and operationalize the entire system through a user-friendly Google Sheets interface.
- **Agent**: Google Apps Script connecting to the database.
- **End Goal Alignment**: This is the final deliverable, consuming the clean data from all previous phases to provide key business insights.

### Executable Items for Phase 4
1.  **Build the Costing Engine**: Develop the logic (likely a complex SQL query or function) that traverses the recipe tree for a given sold item, calculates total standardized quantities for each base SKU, and applies the correct `latest_sku_price` as of the sale date.
2.  **Design the "Should Cost" Report**: Create a Google Sheet that takes a sales report as input. It will display a Sales Summary, a Costed Sales Analysis (for `DEFINED` recipes), an Uncosted Sales Breakdown (listing items that need recipes), and the overall "Coverage Score" KPI.
3.  **Create Google Sheets Helpers**: Build the "Costing Dashboard" for viewing costs and a "New Recipe Helper" with autocomplete to ensure new recipes are created cleanly.

### Milestone for Phase 4
Complete when the "Should Cost" report can be successfully generated from a sample sales data file, and the Google Sheets dashboard accurately reflects the calculated costs.
