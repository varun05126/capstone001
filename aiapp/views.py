import json
import os
import requests


from django.contrib.auth import logout
from django.http import HttpResponse
from django.shortcuts import render, redirect
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from .models import StudentProfile
from django.contrib.auth.decorators import login_required

# ---------------------------------------------------
# GROQ API KEY
# ---------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# ---------------------------------------------------
# HELPERS
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
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    return text[start:end + 1]


# ---------------------------------------------------
# HOME PAGE (AI CAREER PLANNER)
# ---------------------------------------------------
@login_required
def home(request):

    output = None
    error = None

    # -----------------------------------
    # RESET
    # -----------------------------------
    if request.method == "POST" and request.POST.get("action") == "reset":
        if "output" in request.session:
            del request.session["output"]
        return redirect("/")
    
    # -----------------------------------
    # SKILL READINESS CALCULATION
    # -----------------------------------
    if request.method == "POST" and request.POST.get("action") == "calculate":

        output = request.session.get("output")

        if not output:
            return redirect("/")

        skills = output.get("role1Skills", [])

        total_score = 0
        max_score = len(skills) * 3

        for skill in skills:
            value = request.POST.get(skill["name"])
            if value:
                total_score += int(value)

        readiness_score = int((total_score / max_score) * 100) if max_score else 0

        output["readinessScore"] = readiness_score
        request.session["output"] = output

        return render(request, "index.html", {"output": output})

    # -----------------------------------
    # RELOAD SESSION DATA
    # -----------------------------------
    if request.method == "GET" and request.session.get("output"):
        return render(request, "index.html", {
            "output": request.session.get("output"),
            "error": None
        })

    # -----------------------------------
    # GENERATE AI CAREER PLAN
    # -----------------------------------
    if request.method == "POST":

        if not GROQ_API_KEY:
            return render(request, "index.html", {
                "output": None,
                "error": "Server configuration error: API key missing."
            })

        company = request.POST.get("company", "").strip()
        role1 = request.POST.get("jobRole", "").strip()
        role2 = request.POST.get("jobRoleCompare", "").strip()

        if not company or not role1:
            return render(request, "index.html", {
                "output": None,
                "error": "Company name and primary role are required."
            })

        prompt = f"""
You are a professional career architect.

STRICT RULES:
- Output ONLY valid JSON.
- No markdown.
- No explanations outside JSON.
- Provide realistic career guidance.
- Include detailed skill descriptions.
- Include YouTube playlists.
- Include GitHub project ideas.
- Include internship suggestions.
- Include salary progression.
- readinessScore must be 0 (system calculates later).

JSON FORMAT:
{{
  "role1Skills": [
    {{"name": "", "description": "", "level": "Beginner|Intermediate|Advanced"}}
  ],
  "schoolGaps": [
    {{"name": "", "description": ""}}
  ],
  "bridgeModules": [
    {{"name": "", "description": ""}}
  ],
  "youtubePlaylists": [
    {{"title": "", "url": ""}}
  ],
  "githubProjects": [
    {{"title": "", "description": "", "url": ""}}
  ],
  "internships": [
    {{"company": "", "role": "", "url": ""}}
  ],
  "salaryProgression": {{
    "entry": "",
    "mid": "",
    "senior": ""
  }},
  "estimatedTime": "",
  "transitionAdvice": ""
}}

Company: {company}
Primary Role: {role1}
Comparison Role: {role2 if role2 else "None"}
"""

        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": "You are a strict JSON-only generator."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0,
                },
                timeout=40
            )

            if response.status_code != 200:
                raise ValueError(f"AI error: {response.status_code}")

            data = response.json()

            if "choices" not in data or not data["choices"]:
                raise ValueError("Invalid AI response structure.")

            ai_raw = data["choices"][0]["message"]["content"]
            ai_raw = ai_raw.replace("```json", "").replace("```", "").strip()

            json_text = extract_json(ai_raw)

            if not json_text:
                raise ValueError("AI response format invalid.")

            parsed = json.loads(json_text)

            # ---------------------------------------------------
            # FALLBACK RESOURCES (YouTube + GitHub + Internships)
            # ---------------------------------------------------

            youtube_playlists = parsed.get("youtubePlaylists") or []
            github_projects = parsed.get("githubProjects") or []
            internships = parsed.get("internships") or []

            role_keyword = role1.replace(" ", "+")

            # -----------------------------------
            # Fallback YouTube playlists
            # -----------------------------------
            if len(youtube_playlists) == 0:
                youtube_playlists = [
                    {
                        "title": f"{role1} Full Course",
                        "url": f"https://www.youtube.com/results?search_query={role_keyword}+full+course"
                    },
                    {
                        "title": f"{role1} Roadmap",
                        "url": f"https://www.youtube.com/results?search_query={role_keyword}+roadmap"
                    },
                    {
                        "title": f"{role1} Projects",
                        "url": f"https://www.youtube.com/results?search_query={role_keyword}+projects"
                    }
                ]

            # -----------------------------------
            # Fallback GitHub projects
            # -----------------------------------
            if len(github_projects) == 0:
                github_projects = [
                    {
                        "title": f"{role1} Portfolio Project",
                        "description": f"A complete beginner to advanced {role1} project.",
                        "url": f"https://github.com/search?q={role_keyword}+project"
                    },
                    {
                        "title": f"{role1} Practice Repository",
                        "description": f"Practice problems and exercises related to {role1}.",
                        "url": f"https://github.com/search?q={role_keyword}+practice"
                    },
                    {
                        "title": f"{role1} Real World Application",
                        "description": f"Build a real-world application related to {role1}.",
                        "url": f"https://github.com/search?q={role_keyword}+app"
                    }
                ]

            # -----------------------------------
            # Fallback internships
            # -----------------------------------
            if len(internships) == 0:
                internships = [
                    {
                        "company": "Google",
                        "role": "Student Intern",
                        "url": "https://careers.google.com"
                    },
                    {
                        "company": "Microsoft",
                        "role": "Student Intern",
                        "url": "https://careers.microsoft.com"
                    },
                    {
                        "company": "Amazon",
                        "role": "SDE Intern",
                        "url": "https://amazon.jobs"
                    }
                ]

            output = {
                "company": company,
                "role1": role1,
                "role2": role2 if role2 else None,

                "role1Skills": normalize_list(parsed.get("role1Skills", [])),
                "schoolGaps": normalize_list(parsed.get("schoolGaps", [])),
                "bridgeModules": normalize_list(parsed.get("bridgeModules", [])),

                "youtubePlaylists": youtube_playlists,
                "githubProjects": github_projects,
                "internships": internships,

                "salaryProgression": parsed.get("salaryProgression", {}),
                "estimatedTime": parsed.get("estimatedTime", ""),
                "transitionAdvice": parsed.get("transitionAdvice", ""),

                # IMPORTANT: No default 60%
                "readinessScore": 0
            }

            request.session["output"] = output

        except requests.exceptions.Timeout:
            error = "AI service timeout. Please try again."
        except Exception as e:
            error = str(e)

    return render(request, "index.html", {
        "output": output,
        "error": error
    })


# ---------------------------------------------------
# PDF GENERATOR
# ---------------------------------------------------
def download_pdf(request):

    output = request.session.get("output")

    if not output:
        return HttpResponse("No data available", status=400)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=career_report.pdf"

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
    pdf.drawString(50, y, "AI Career Readiness Report")
    y -= 30

    title(f"Company: {output['company']}")
    title(f"Primary Role: {output['role1']}")
    title(f"Estimated Time: {output['estimatedTime']}")

    title("Core Skills")
    for s in output["role1Skills"]:
        line(f"- {s['name']} ({s['level']}): {s['description']}")

    title("Transition Advice")
    advice = output.get("transitionAdvice", "")
    for part in advice.split(". "):
        line(part.strip())

    pdf.save()
    return response

@login_required
def profile(request):

    profile = StudentProfile.objects.filter(user=request.user).first()

    if request.method == "POST":

        # Save Career Path
        if "career_company" in request.POST:

            company = request.POST.get("career_company")
            role = request.POST.get("career_role")

            if profile:
                profile.target_company = company
                profile.target_role = role
                profile.save()

            return redirect("/profile/")


        # Save Profile Details
        grade = request.POST.get("grade")
        school = request.POST.get("school")

        github = request.POST.get("github")
        leetcode = request.POST.get("leetcode")
        codechef = request.POST.get("codechef")
        hackerrank = request.POST.get("hackerrank")

        profile, created = StudentProfile.objects.update_or_create(
            user=request.user,
            defaults={
                "grade": grade,
                "school": school,
                "github": github,
                "leetcode": leetcode,
                "codechef": codechef,
                "hackerrank": hackerrank
            }
        )

        # 🔹 Redirect to home page after saving
        return redirect("/")

    return render(request, "profile.html", {
        "profile": profile
    })


from django.contrib.auth import logout
from django.shortcuts import redirect

def logout_user(request):
    logout(request)
    return redirect("/login/")

from django.contrib.auth.models import User
from django.contrib import messages

def signup(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        if User.objects.filter(username=username).exists():
            return render(request, "signup.html", {
                "error": "Username already exists"
            })

        User.objects.create_user(
            username=username,
            password=password
        )

        return redirect("/login/")

    return render(request, "signup.html")