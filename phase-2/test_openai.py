import os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path('..') / 'phase-6' / 'config' / '.env')
from openai import OpenAI

key = os.getenv('OPENAI_API_KEY', '')
print('Key present:', bool(key))
print('Key prefix:', key[:15] if key else 'NONE')

client = OpenAI(api_key=key)
try:
    r = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": "Respond with: {\"status\": \"ok\"}"}
        ],
        response_format={"type": "json_object"},
        max_tokens=50,
        timeout=20,
    )
    print('SUCCESS:', r.choices[0].message.content)
except Exception as e:
    print('FAILED:', type(e).__name__)
    print('ERROR:', str(e)[:400])
