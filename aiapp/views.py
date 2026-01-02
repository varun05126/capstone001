import json
import os
import requests

from django.shortcuts import render, redirect
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# ---------------------------------------------------
# ENV
# ---------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ---------------------------------------------------
# HELPERS
# ---------------------------------------------------
def extract_json(text):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    return text[start:end + 1]


def normalize_list(items):
    cleaned = []
    for it in items:
        if isinstance(it, dict):
            name = it.get("name", "").strip()
            desc = it.get("description", "").strip()
            level = it.get("level", "").strip()

            if not name and not desc:
                continue

            cleaned.append({
                "name": name,
                "description": desc,
                "level": level
            })
    return cleaned


# ---------------------------------------------------
# MAIN VIEW
# ---------------------------------------------------
def home(request):
    output = None
    error = None

    # RESET ACTION
    if request.method == "POST" and request.POST.get("action") == "reset":
        request.session.flush()
        return redirect("/")

    # REUSE LAST RESULT (GET)
    if request.method == "GET" and request.session.get("output"):
        return render(request, "index.html", {
            "output": request.session["output"],
            "error": None
        })

    # GENERATE NEW RESULT
    if request.method == "POST":
        request.session.pop("output", None)

        company = request.POST.get("company", "").strip()
        role1 = request.POST.get("jobRole", "").strip()
        role2 = request.POST.get("jobRoleCompare", "").strip()

        prompt = f"""
Return ONLY valid JSON. No markdown.

Context:
EduBridge AI bridges secondary school education and industry careers.

JSON FORMAT:
{{
  "commonSkills": [{{"name":"","description":""}}],
  "role1Only": [{{"name":"","description":""}}],
  "role2Only": [{{"name":"","description":""}}],
  "schoolGaps": [{{"name":"","description":""}}],
  "bridgeModules": [{{"name":"","description":""}}],
  "estimatedTime": "example: 4–6 months",
  "transitionAdvice": "short paragraph"
}}

Company: {company}
Primary Role: {role1}
Comparison Role: {role2 if role2 else "None"}
"""

        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                },
                timeout=15
            )

            raw = response.json()["choices"][0]["message"]["content"]
            raw = raw.replace("```json", "").replace("```", "").strip()

            json_text = extract_json(raw)
            if not json_text:
                raise ValueError("Invalid AI response")

            parsed = json.loads(json_text)

            output = {
                "company": company,
                "role1": role1,
                "role2": role2 if role2 else None,

                "commonSkills": normalize_list(parsed.get("commonSkills", [])),
                "role1Only": normalize_list(parsed.get("role1Only", [])),
                "role2Only": normalize_list(parsed.get("role2Only", [])),
                "schoolGaps": normalize_list(parsed.get("schoolGaps", [])),
                "bridgeModules": normalize_list(parsed.get("bridgeModules", [])),

                "estimatedTime": parsed.get("estimatedTime", "Not specified"),
                "transitionAdvice": parsed.get("transitionAdvice", "")
            }

            request.session["output"] = output

        except Exception as e:
            error = str(e)

    return render(request, "index.html", {
        "output": output,
        "error": error
    })


# ---------------------------------------------------
# PDF DOWNLOAD
# ---------------------------------------------------
def download_pdf(request):
    output = request.session.get("output")
    if not output:
        return HttpResponse("No data", status=400)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=edubridge_ai_report.pdf"

    pdf = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    y = height - 50

    def heading(text):
        nonlocal y
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(50, y, text)
        y -= 22
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
    pdf.drawString(50, y, "EduBridge AI – Career Comparison Report")
    y -= 30

    heading(f"Company: {output['company']}")
    heading(f"Primary Role: {output['role1']}")
    if output.get("role2"):
        heading(f"Comparison Role: {output['role2']}")
    heading(f"Estimated Time: {output['estimatedTime']}")

    heading("Common Skills")
    for s in output["commonSkills"]:
        line(f"- {s['name']}: {s['description']}")

    heading("Primary Role Skills")
    for s in output["role1Only"]:
        line(f"- {s['name']}: {s['description']}")

    if output.get("role2Only"):
        heading("Additional Skills")
        for s in output["role2Only"]:
            line(f"- {s['name']}: {s['description']}")

    heading("School Gaps")
    for g in output["schoolGaps"]:
        line(f"- {g['name']}: {g['description']}")

    heading("Bridge Modules")
    for m in output["bridgeModules"]:
        line(f"- {m['name']}: {m['description']}")

    pdf.save()
    return response
