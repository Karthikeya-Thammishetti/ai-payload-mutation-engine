app.py – Full Flask App with GPT + PDF Report

from flask import Flask, render_template, request, send_file
import requests, os, openai
from datetime import datetime
from fpdf import FPDF

app = Flask(__name__)
openai.api_key = "sk-..."  # 🔐 Replace with your OpenAI key
PHPSESSID = "replace_your_dvwa_session_id"
DVWA_ENDPOINT = "http://localhost/dvwa/vulnerabilities/xss_r/"  # Update based on test

# === GPT Payload Generator ===
def gpt_mutate_payload(base_payload, attack_type="xss"):
    prompt = f"""You're an expert in WAF bypass testing. Mutate this {attack_type.upper()} payload for testing:\n{base_payload}\nGive 5 unique versions."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200
        )
        output = response['choices'][0]['message']['content']
        return list(set([line.strip("-•* ") for line in output.strip().split('\n') if line.strip()]))
    except Exception as e:
        return [f"GPT Error: {e}"]

# === DVWA Submit ===
def submit_to_dvwa(payload):
    cookies = {"security": "low", "PHPSESSID": PHPSESSID}
    data = {"name": payload, "submit": "submit"}
    try:
        r = requests.post(DVWA_ENDPOINT, data=data, cookies=cookies, timeout=5)
        status = r.status_code
        blocked = "403" in str(status) or "mod_security" in r.text.lower()
        return {
            "payload": payload,
            "timestamp": str(datetime.now()),
            "status": status,
            "blocked": blocked,
            "snippet": r.text[:150]
        }
    except Exception as e:
        return {
            "payload": payload,
            "timestamp": str(datetime.now()),
            "status": "Error",
            "blocked": True,
            "snippet": str(e)
        }

# === PDF Generator ===
def generate_pdf(results, filename="reports/report.pdf"):
    os.makedirs("reports", exist_ok=True)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, "AI-Powered WAF Mutation Report", ln=True, align='C')
    pdf.ln(10)
    for r in results:
        pdf.cell(0, 10, f"Payload: {r['payload']}", ln=True)
        pdf.cell(0, 10, f"Time: {r['timestamp']} | Status: {r['status']} | {'Blocked' if r['blocked'] else 'Allowed'}", ln=True)
        pdf.multi_cell(0, 10, f"Snippet: {r['snippet']}")
        pdf.ln(5)
    pdf.output(filename)
    return filename

# === Web Routes ===
@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    report_file = None
    if request.method == "POST":
        attack_type = request.form.get("attack_type")
        base_payload = request.form.get("base_payload")
        gpt_payloads = gpt_mutate_payload(base_payload, attack_type)
        all_payloads = list(set(gpt_payloads + [base_payload]))

        for p in all_payloads:
            result = submit_to_dvwa(p)
            results.append(result)

        report_file = generate_pdf(results)

    return render_template("index.html", results=results, report=report_file)

@app.route("/download")
def download():
    return send_file("reports/report.pdf", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)


🖥️ 2. templates/index.html – UI Page


<!DOCTYPE html>
<html>
<head>
    <title>WAF Payload Tester</title>
    <style>
        body { font-family: Arial; background: #f2f2f2; padding: 20px; }
        input, select { padding: 8px; margin: 5px; }
        table { width: 100%; background: white; border-collapse: collapse; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        .blocked { color: red; font-weight: bold; }
        .allowed { color: green; font-weight: bold; }
    </style>
</head>
<body>
    <h2>AI-Powered Payload Mutation Engine</h2>
    <form method="POST">
        <label>Attack Type:</label>
        <select name="attack_type">
            <option value="xss">XSS</option>
            <option value="sqli">SQLi</option>
        </select><br>
        <label>Base Payload:</label>
        <input type="text" name="base_payload" value="&lt;script&gt;alert(1)&lt;/script&gt;" required><br>
        <button type="submit">Run Test</button>
    </form>

    {% if results %}
        <h3>Results:</h3>
        <table>
            <tr>
                <th>Payload</th>
                <th>Status</th>
                <th>WAF</th>
                <th>Snippet</th>
            </tr>
            {% for r in results %}
            <tr>
                <td>{{ r.payload }}</td>
                <td>{{ r.status }}</td>
                <td class="{{ 'blocked' if r.blocked else 'allowed' }}">{{ 'Blocked' if r.blocked else 'Allowed' }}</td>
                <td>{{ r.snippet }}</td>
            </tr>
            {% endfor %}
        </table>
        <br>
        <a href="/download">📄 Download PDF Report</a>
    {% endif %}
</body>
</html>


requirements.txt
Flask
openai
requests
fpdf
