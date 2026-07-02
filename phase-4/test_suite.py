import json
import os
import urllib.request
import urllib.error
import time

WEBHOOK_URL = "http://localhost:5678/webhook/analyze"
TEST_CASES_DIR = "phase-4/test-cases"
RESULTS_DIR = "phase-4/results"

def load_test_cases():
    test_cases = {}
    for filename in os.listdir(TEST_CASES_DIR):
        if filename.endswith(".txt"):
            filepath = os.path.join(TEST_CASES_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                test_cases[filename] = f.read()
    return test_cases

def run_test(name, text):
    print(f"Running test for: {name} (length: {len(text)})")
    
    start_time = time.time()
    
    try:
        req = urllib.request.Request(
            WEBHOOK_URL,
            data=json.dumps({"reviews": text}).encode('utf-8'),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=180) as response:
            duration = time.time() - start_time
            print(f"[SUCCESS] ({duration:.2f}s)")
            data = json.loads(response.read().decode('utf-8'))
            
            # Save the result
            out_filename = name.replace(".txt", ".json")
            out_path = os.path.join(RESULTS_DIR, out_filename)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                
            validate_schema(data)
            
    except urllib.error.HTTPError as e:
        print(f"[FAIL] Status Code: {e.code}")
        print(e.read().decode('utf-8'))
    except Exception as e:
        print(f"[ERROR] occurred: {e}")

def validate_schema(data):
    expected_keys = [
        "executive_summary",
        "sentiment_analysis",
        "key_pain_points",
        "root_causes",
        "recommendation_frustrations",
        "desired_listening_behaviors",
        "repeat_listening_causes",
        "user_segments",
        "unmet_needs",
        "feature_requests",
        "strategic_product_insights",
        "ai_product_opportunities",
        "confidence_assessment",
        "meta"
    ]
    
    missing = [k for k in expected_keys if k not in data]
    if missing:
        print(f"   [WARN] Missing keys: {missing}")
    else:
        print("   [PASS] Schema validated perfectly.")

if __name__ == "__main__":
    os.makedirs(RESULTS_DIR, exist_ok=True)
    tests = load_test_cases()
    for name, text in tests.items():
        run_test(name, text)
        print("-" * 40)
