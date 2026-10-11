"""Turn the bank's test-customers.json into src/data.js for the Worker (exact answers, no edits)."""
import json, pathlib, sys
src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "../briefs/final/test-environment/test-customers.json")
customers = {c["customerNo"]: c["services"] for c in json.loads(src.read_text())["customers"]}
pathlib.Path("src/data.js").write_text("export default " + json.dumps(customers, ensure_ascii=False) + ";\n")
print(len(customers), "customers")
