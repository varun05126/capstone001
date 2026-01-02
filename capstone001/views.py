import json
import os
import requests

from django.http import HttpResponse
from django.shortcuts import render
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# ---------------------------------------------------
# GROQ API KEY (ENV VARIABLE)
# ---------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# ---------------------------------------------------
# Helpers
# ---------------------------------------------------
def normalize_list(items):
    normalized = []
    for it in items:
        if isinstance(it, dict):
            normalized.append({
                "name": it.get("name", ""),
                "description": it.get("description", ""),
                "level": it.get("level", "")
            })
        else:
            normalized.append({
                "name": str(it),
                "description": "",
                "level": ""
            })
    return normalized


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

    # Reuse last generated report (session cache)
    if request.method == "GET" and request.session.get("output"):
        return render(request, "index.html", {
            "output": request.session.get("output"),
            "error": None
        })

    if request.method == "POST":
        company = request.POST.get("company")
        role1 = request.POST.get("jobRole")
        role2 = request.POST.get("jobRoleCompare")  # optional comparison role

        # ---------------------------------------------------
        # AI PROMPT
        # ---------------------------------------------------
        prompt = f"""
Return ONLY valid JSON. No markdown. No extra text.

Context:
This system bridges secondary school education and industry expectations.
Focus on practical, curriculum-aware skills (Indian education context).

JSON FORMAT:
{{
  "role1Skills": [
    {{"name": "skill", "description": "short explanation", "level": "Beginner|Intermediate|Advanced"}}
  ],
  "role2Skills": [
    {{"name": "skill", "description": "short explanation", "level": "Beginner|Intermediate|Advanced"}}
  ],
  "commonSkills": [
    {{"name": "skill", "description": "why common to both"}}
  ],
  "role1Only": [
    {{"name": "skill", "description": "specific to role 1"}}
  ],
  "role2Only": [
    {{"name": "skill", "description": "additional skill needed for role 2"}}
  ],
  "schoolGaps": [
    {{"name": "gap", "description": "why school education misses this"}}
  ],
  "bridgeModules": [
    {{"name": "module", "description": "how this bridges school to industry"}}
  ],
  "estimatedTime": "example: 5–6 months",
  "transitionAdvice": "short guidance paragraph"
}}

Company: {company}
Primary Role: {role1}
Comparison Role: {role2}
"""

        try:
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
                timeout=15
            )

            data = response.json()
            ai_raw = data["choices"][0]["message"]["content"]
            ai_raw = ai_raw.replace("```json", "").replace("```", "").strip()

            json_text = extract_json(ai_raw)
            if not json_text:
                raise ValueError("Invalid AI response format")

            parsed = json.loads(json_text)

            output = {
                "company": company,
                "role1": role1,
                "role2": role2,

                "role1Skills": normalize_list(parsed.get("role1Skills", [])),
                "role2Skills": normalize_list(parsed.get("role2Skills", [])),
                "commonSkills": normalize_list(parsed.get("commonSkills", [])),
                "role1Only": normalize_list(parsed.get("role1Only", [])),
                "role2Only": normalize_list(parsed.get("role2Only", [])),

                "schoolGaps": normalize_list(parsed.get("schoolGaps", [])),
                "bridgeModules": normalize_list(parsed.get("bridgeModules", [])),

                "estimatedTime": parsed.get("estimatedTime", "Not specified"),
                "transitionAdvice": parsed.get("transitionAdvice", ""),
            }

            # Save to session for PDF & refresh
            request.session["output"] = output

        except Exception as e:
            error = str(e)

    return render(request, "index.html", {
        "output": output,
        "error": error
    })


# ---------------------------------------------------
# Structured PDF Generator (Comparison Report)
# ---------------------------------------------------
def download_pdf(request):
    output = request.session.get("output")

    if not output:
        return HttpResponse("No data available", status=400)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=skill_comparison_report.pdf"

    pdf = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    y = height - 50

    def title(text):
        nonlocal y
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(50, y, text)
        y -= 25
        pdf.setFont("Helvetica", 11)

    def line(text):
        nonlocal y
        if y < 60:
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = height - 50
        pdf.drawString(60, y, text)
        y -= 16

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "AI Skill Mapper – Role Comparison Report")
    y -= 30

    title(f"Company: {output['company']}")
    title(f"Primary Role: {output['role1']}")
    title(f"Comparison Role: {output['role2']}")
    title(f"Estimated Preparation Time: {output['estimatedTime']}")

    title("Common Skills (Both Roles)")
    for s in output["commonSkills"]:
        line(f"- {s['name']}: {s['description']}")

    title(f"{output['role1']} – Core Skills")
    for s in output["role1Only"]:
        line(f"- {s['name']} ({s['level']}): {s['description']}")

    title(f"{output['role2']} – Additional Skills Needed")
    for s in output["role2Only"]:
        line(f"- {s['name']} ({s['level']}): {s['description']}")

    title("School Gaps")
    for g in output["schoolGaps"]:
        line(f"- {g['name']}: {g['description']}")

    title("Bridge Training Modules")
    for m in output["bridgeModules"]:
        line(f"- {m['name']}: {m['description']}")

    title("Transition Advice")
    for part in output["transitionAdvice"].split(". "):
        line(part.strip())

    pdf.save()
    return response