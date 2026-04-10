import json
import os
import requests
import random

from django.http import HttpResponse
from django.shortcuts import render, redirect
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# -------------------- HELPERS --------------------
def normalize_list(items):
    normalized = []
    for it in items:
        if isinstance(it, dict):
            normalized.append({"name": it.get("name", "")})
        elif isinstance(it, str):
            normalized.append({"name": it})
        else:
            normalized.append({"name": str(it)})
    return normalized


def extract_json(text):
    if not text:
        return None
    text = text.replace("```json", "").replace("```", "").strip()
    start = text.find("{")
    end = text.rfind("}")
    return text[start:end + 1] if start != -1 and end != -1 else None


# -------------------- ACADEMIC GAPS --------------------
def generate_academic_gaps(role):
    role = role.lower()

    if "ai" in role or "ml" in role:
        return [
            {"name": "Mathematics Foundation", "description": "Need stronger understanding of statistics and linear algebra"},
            {"name": "Data Handling", "description": "Limited experience working with datasets"},
            {"name": "Programming Depth", "description": "Need deeper Python and ML libraries knowledge"}
        ]

    elif "web" in role:
        return [
            {"name": "Frontend Basics", "description": "Weak understanding of HTML, CSS"},
            {"name": "JavaScript Logic", "description": "Needs improvement in JS concepts"},
            {"name": "Project Experience", "description": "Lack of real-world web projects"}
        ]

    else:
        return [
            {"name": "Problem Solving", "description": "Needs more logical thinking practice"},
            {"name": "Data Structures", "description": "Weak understanding of DSA"},
            {"name": "Project Building", "description": "Limited hands-on coding projects"}
        ]


# -------------------- DYNAMIC ROADMAP --------------------
def generate_dynamic_roadmap(student_class, role):
    base = int(student_class)
    role = role.lower()

    roadmap = []

    for i in range(5):
        current = base + i

        if "ai" in role or "ml" in role:
            steps = [
                ["Learn Python basics", "Math fundamentals", "Simple ML concepts"],
                ["Work with datasets", "Learn regression", "Mini ML project"],
                ["Neural networks", "Use sklearn", "Kaggle practice"],
                ["Deep learning intro", "Build AI app", "Deploy model"],
                ["Specialize in AI", "Portfolio", "Internships"]
            ]

        elif "web" in role:
            steps = [
                ["HTML, CSS basics", "Build static pages"],
                ["JavaScript basics", "DOM projects"],
                ["React basics", "API integration"],
                ["Backend + Database", "Full-stack project"],
                ["Deploy apps", "Freelancing / internships"]
            ]

        else:
            steps = [
                ["Programming basics", "Logic building"],
                ["Data structures", "Solve problems"],
                ["OOP concepts", "Build projects"],
                ["Advanced DSA", "System basics"],
                ["Specialization", "Internships"]
            ]

        tasks = steps[i] if i < len(steps) else random.choice(steps)

        roadmap.append({
            "class": str(current),
            "skills": tasks
        })

    return roadmap


# -------------------- HOME --------------------
def home(request):
    output = None
    error = None

    # RESET
    if request.method == "POST" and request.POST.get("action") == "reset":
        request.session.pop("output", None)
        return redirect("/")

    # READINESS SCORE
    if request.method == "POST" and request.POST.get("action") == "calculate":
        output = request.session.get("output")

        skills = output.get("role1Skills", [])
        total, count = 0, 0

        for skill in skills:
            val = request.POST.get(skill["name"])
            if val is not None:
                total += int(val)
                count += 1

        output["readinessScore"] = int((total / (count * 3)) * 100) if count else 0
        request.session["output"] = output

        return render(request, "index.html", {"output": output})

    # LOAD SESSION
    if request.method == "GET" and request.session.get("output"):
        return render(request, "index.html", {"output": request.session.get("output")})

    # GENERATE
    if request.method == "POST":

        company = request.POST.get("company")
        role1 = request.POST.get("jobRole")
        student_class = request.POST.get("studentClass")

        roadmap = generate_dynamic_roadmap(student_class, role1)
        gaps = generate_academic_gaps(role1)

        skills = normalize_list([
            "Programming",
            "Problem Solving",
            "Data Structures",
            "Projects",
            "Technology Basics"
        ])

        youtube = [
            {"title": "freeCodeCamp", "url": "https://www.youtube.com/@freecodecamp"},
            {"title": "Traversy Media", "url": "https://www.youtube.com/@TraversyMedia"},
            {"title": "Programming with Mosh", "url": "https://www.youtube.com/@programmingwithmosh"}
        ]

        github = [
            {"title": "To-Do App", "description": "CRUD project", "url": "https://github.com/topics/todo-app"},
            {"title": "Portfolio Website", "description": "Showcase your work", "url": "https://github.com/topics/portfolio"},
            {"title": "Chatbot", "description": "AI chatbot", "url": "https://github.com/topics/chatbot"}
        ]

        internships = [
            {"company": "Internshala", "role": "Python Intern", "url": "https://internshala.com"}
        ]

        output = {
            "company": company,
            "role1": role1,
            "studentClass": student_class,
            "roadmap": roadmap,
            "role1Skills": skills,
            "academicGaps": gaps,
            "youtubePlaylists": youtube,
            "githubProjects": github,
            "internships": internships,
            "estimatedTime": "4-6 years",
            "readinessScore": 0
        }

        request.session["output"] = output

        return render(request, "index.html", {"output": output})

    return render(request, "index.html", {"output": output, "error": error})


# -------------------- PDF --------------------
def download_pdf(request):
    output = request.session.get("output")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=report.pdf"

    pdf = canvas.Canvas(response, pagesize=letter)

    pdf.drawString(100, 750, f"Company: {output['company']}")
    pdf.drawString(100, 730, f"Role: {output['role1']}")

    pdf.save()
    return response
