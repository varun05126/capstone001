import json
import requests
from django.http import HttpResponse
from django.shortcuts import render
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# -----------------------------
# YOUR GROQ API KEY
# -----------------------------
GROQ_API_KEY = "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"


# ---------------------------------------------------
# Helper: Normalize lists into {name, description}
# ---------------------------------------------------
def normalize_list(items):
    normalized = []
    for it in items:
        if isinstance(it, dict):
            name = it.get("name") or str(it)
            desc = it.get("description") or it.get("desc") or ""
            normalized.append({"name": name, "description": desc})
        else:
            normalized.append({"name": str(it), "description": ""})
    return normalized


# ---------------------------------------------------
# Helper: Extract JSON safely (NO regex, NO errors)
# ---------------------------------------------------
def extract_json(text):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    return text[start:end + 1]


# ---------------------------------------------------
# Main Page + AI Processing
# ---------------------------------------------------
def home(request):
    output = None
    error = None

    if request.method == "POST":
        company = request.POST.get("company")
        jobRole = request.POST.get("jobRole")

        # -------- Prompt to Groq --------
        prompt = f"""
Return only JSON. No extra text. Follow this structure exactly:

{{
  "industrySkills": ["skill1", "skill2"],
  "schoolGaps": ["gap1", "gap2"],
  "bridgeModules": ["module1", "module2"],
  "expectedStudentOutcomes": ["outcome1", "outcome2"],
  "flow": ["step1", "step2"],
  "explanation": "text"
}}

Company: {company}
Job Role: {jobRole}
"""

        try:
            # ---- Call Groq API ----
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                },
            )

            data = response.json()
            ai_raw = data["choices"][0]["message"]["content"]

            # ---- Clean JSON ----
            ai_raw = ai_raw.replace("```json", "").replace("```", "").strip()
            json_text = extract_json(ai_raw)
            if not json_text:
                raise ValueError("AI did not return valid JSON.")

            parsed = json.loads(json_text)

            # ---- Final formatted output ----
            output = {
                "industrySkills": normalize_list(parsed.get("industrySkills", [])),
                "schoolGaps": normalize_list(parsed.get("schoolGaps", [])),
                "bridgeModules": normalize_list(parsed.get("bridgeModules", [])),
                "expectedStudentOutcomes": normalize_list(parsed.get("expectedStudentOutcomes", [])),
                "flow": normalize_list(parsed.get("flow", [])),
                "explanation": parsed.get("explanation", ""),
                "company": company,
                "jobRole": jobRole,
            }

        except Exception as e:
            error = str(e)

    return render(request, "index.html", {"output": output, "error": error})


# ---------------------------------------------------
# PDF Generator
# ---------------------------------------------------
def download_pdf(request):
    content = request.GET.get("content", "")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=skill_report.pdf"

    pdf = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    y = height - 50
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "AI Skill Mapper Report")
    y -= 40
    pdf.setFont("Helvetica", 12)

    # Write content line by line
    for line in content.split("\n"):
        pdf.drawString(50, y, line)
        y -= 20
        if y < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 12)
            y = height - 50

    pdf.save()
    return response