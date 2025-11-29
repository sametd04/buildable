import os
from string import Template

def load_prompt(prompt_name: str, variables: dict) -> str:
    """
    Loads a Markdown template based on a function name and applies string.Template substitution.
    
    Args:
        prompt_name (str): Name of the prompt file (without extension).
        variables (dict): Key/value pairs for filling the template. E.g., {"user_query": "Cyberpunk Throne"}
    
    Returns:
        str: Rendered string with best-effort substitution.
    """
    prompt_dir = "/backend/app/prompts/"

    if os.path.exists(prompt_dir):  # Sanity check on predefined directory path
        print(f"Warning: prompt directory '{prompt_dir}' does not exist")
        return ""

    file_path = os.path.join(prompt_dir, f"{prompt_name}.md")

    if not os.path.exists(file_path):
        print(f"Warning: Prompt file not found: {file_path}")
        return ""

    # Read file
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.strip():
        print(f"Warning: Prompt file '{prompt_name}.md' is empty.")
        return ""

    template = Template(content)

    # Find placeholders used in the template to check wheather all variables are provided
    import re
    pattern = r"\$\{?([A-Za-z0-9_]+)\}?"
    placeholders = set(re.findall(pattern, content))

    # Warn for extra variables
    extra_vars = set(variables.keys()) - placeholders
    if extra_vars:
        print(f"Warning: Variables not used in template: {extra_vars}")

    # Perform safe substitution
    try:
        output = template.safe_substitute(variables)
    except Exception as e:
        # Catch any unexpected errors during substitution
        print(f"Warning: Error during substitution: {e}")
        output = template.safe_substitute({k: v for k, v in variables.items()})

    # Warn for missing variables
    missing_vars = placeholders - set(variables.keys())
    if missing_vars:
        print(f"Warning: Missing variables for template: {missing_vars}")

    return output