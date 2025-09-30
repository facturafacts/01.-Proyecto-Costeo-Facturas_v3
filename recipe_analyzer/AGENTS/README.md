# Recipe Analyzer AI Agent

This project is an isolated sub-module for analyzing and processing the `RECETARIO.xlsx` file. It uses an AI-powered agent within a Jupyter Notebook to perform data cleaning, standardization, and enrichment.

## Project Structure

- **/data**: Contains the input (`RECETARIO.xlsx`) and output (cleaned data) files.
- **/notebooks**: The main `01_recipe_analysis_agent.ipynb` notebook lives here. This is the primary interface for running the agent.
- **/src**: Contains reusable Python helper modules for database connections, prompt engineering, and interacting with the Gemini API.

## Workflow

1.  Open `notebooks/01_recipe_analysis_agent.ipynb`.
2.  Run the cells sequentially.
3.  The agent will load the data, identify issues, and propose changes.
4.  Review the proposals from the AI.
5.  Run the execution cells to apply the changes and save the cleaned data.



