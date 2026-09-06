from pathlib import Path
import json

from backend.services.data_loader import get_all_data_summary
from backend.services.ollama_service import ask_ollama


def load_current_data():

    data = get_all_data_summary()

    return data


def build_risk_prompt(data):

    return f"""
You are the AI reasoning and explanation engine
for NER-LOGIX AI.

The system is monitoring disaster risk in the
North-Eastern states of India.

Available disaster data:

{json.dumps(data, indent=2, ensure_ascii=False)}

Your task:

1. Identify important current conditions.
2. Identify rainfall-related risk.
3. Identify possible flood risk.
4. Identify possible landslide risk.
5. Identify areas requiring attention.
6. Explain uncertainty where data is missing.
7. Give practical precautionary actions.
8. Do not invent measurements.
9. Do not claim a disaster is occurring unless the
   supplied data supports that conclusion.

Return the answer in this structure:

OVERALL RISK
----------------
...

RAINFALL
----------------
...

FLOOD RISK
----------------
...

LANDSLIDE RISK
----------------
...

AREAS REQUIRING ATTENTION
----------------
...

WARNING SIGNS
----------------
...

RECOMMENDED ACTIONS
----------------
...

DATA CONFIDENCE
----------------
...
"""


def analyze_current_data():

    data = load_current_data()

    prompt = build_risk_prompt(data)

    return ask_ollama(prompt)


if __name__ == "__main__":

    print("\nNER-LOGIX AI ANALYSIS\n")

    result = analyze_current_data()

    print(result)