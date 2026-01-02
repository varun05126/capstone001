import json
import os
import requests

from django.shortcuts import render
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


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
            if name or desc:
                cleaned.append({
                    "name": name,
                    "description": desc
                })
        else:
            val = str(it).strip()
            if val:
                cleaned.append({
                    "name": val,
                    "description": ""
                })
    return cleaned


def home(request):
    output = None
    error = None

    if request.method == "GET" and request.session.get("output"):
        return render(request, "index.html", {
            "output": request.session["output"],
            "error": None
        })

    if request.method == "POST":
        company = request.POST.get("company", "")
        role1 = request.POST.get("jobRole", "")
        role2 = request.POST.get("jobRoleCompare", "")

        prompt = f"""
Return ONLY valid JSON.

Company: {company}
Primary Role: {role1}
Comparison Role: {role2}

JSON FORMAT:
{{
  "commonSkills": [{{"name":"","description":""}}],
  "role1Only": [{{"name":"","description":""}}],
  "role2Only": [{{"name":"","description":""}}],
  "schoolGaps": [{{"name":"","description":""}}],
  "bridgeModules": [{{"name":"","description":""}}],
  "estimatedTime": "4–6 months",
  "transitionAdvice": "short paragraph"
}}
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
            json_text = extract_json(raw)
            if not json_text:
                raise ValueError("Invalid AI response")

            parsed = json.loads(json_text)

            output = {
                "company": company,
                "role1": role1,
                "role2": role2,
                "commonSkills": normalize_list(parsed.get("commonSkills", [])),
                "role1Only": normalize_list(parsed.get("role1Only", [])),
                "role2Only": normalize_list(parsed.get("role2Only", [])),
                "schoolGaps": normalize_list(parsed.get("schoolGaps", [])),
                "bridgeModules": normalize_list(parsed.get("bridgeModules", [])),
                "estimatedTime": parsed.get("estimatedTime", ""),
                "transitionAdvice": parsed.get("transitionAdvice", ""),
            }

            request.session["output"] = output

        except Exception as e:
            error = str(e)

    return render(request, "index.html", {
        "output": output,
        "error": error
    })


def download_pdf(request):
    output = request.session.get("output")
    if not output:
        return HttpResponse("No data", status=400)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=report.pdf"

    pdf = canvas.Canvas(response, pagesize=letter)
    y = 750

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "EduBridge AI Report")
    y -= 30

    pdf.setFont("Helvetica", 11)
    for section in ["commonSkills", "role1Only", "role2Only"]:
        for item in output.get(section, []):
            pdf.drawString(60, y, f"- {item['name']}: {item['description']}")
            y -= 16

    pdf.save()
    return response
