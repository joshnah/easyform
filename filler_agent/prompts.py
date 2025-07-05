# Prompt templates for filler_agent

EXTRACTION_PROMPT_TEMPLATE = '''
Assume the text describes the same person who will later fill the form (the USER). Extract the following personal information from the text below and return as a JSON object with keys:
- full_name
- first_name
- middle_names
- last_name
- birth_day
- birth_month
- birth_year
- date_of_birth (MM-DD-YYYY)
- date_of_birth (DD-MM-YYYY)
- date_of_birth (MM/DD/YYYY)
- date_of_birth (DD/MM/YYYY)
- date_of_birth (YYYY/MM/DD)
- date_of_birth (YYYY-MM-DD)
- phone_number
- email
- address

Text:
"""
{content}
"""

Return ONLY a valid JSON object with these keys. Use empty strings for missing fields, ONLY add the fields that are present in the text if you are sure about the value, otherwise leave it empty. Do not include any markdown formatting, code blocks, or explanatory text - just the raw JSON object.''' 