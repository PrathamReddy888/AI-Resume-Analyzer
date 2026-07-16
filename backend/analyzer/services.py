import re
import os
import pdfplumber
from django.contrib.auth import get_user_model
from .models import ResumeAnalysis

User = get_user_model()


SKILLS = [
    # Languages — only include ones unlikely to false-match as common words
    "python", "java", "c++", "javascript", "typescript",
    "kotlin", "swift", "ruby", "php", "rust",

    # C and single-letter langs need explicit listing but matched carefully
    "c",

    # Web Frontend
    "html", "css", "react", "react.js", "angular", "vue", "vue.js",
    "next.js", "tailwind", "bootstrap", "sass", "webpack",

    # Web Backend
    "node.js", "express", "express.js", "django", "flask", "fastapi",
    "spring boot", "laravel",

    # Databases
    "sql", "mysql", "postgresql", "mongodb", "firebase", "redis",
    "sqlite", "cassandra", "dynamodb",

    # ML / AI
    "machine learning", "deep learning", "data analysis",
    "tensorflow", "keras", "pytorch", "scikit-learn", "opencv",
    "mediapipe", "lstm", "cnn", "llm", "nlp", "pandas", "numpy",
    "matplotlib", "seaborn", "huggingface",

    # Cloud & DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "linux",

    # Tools
    "git", "github", "postman", "jupyter", "vs code", "excel",
]


ROLE_SKILLS = {
    "Frontend Developer": [
        "html", "css", "javascript", "typescript", "react",
        "next.js", "tailwind", "git", "github", "webpack",
    ],

    "Backend Developer": [
        "python", "django", "flask", "fastapi", "node.js", "express.js",
        "sql", "mysql", "postgresql", "mongodb", "docker", "git", "github",
    ],

    "Data Analyst": [
        "python", "sql", "excel", "machine learning", "deep learning",
        "data analysis", "pandas", "numpy", "matplotlib", "tensorflow",
        "scikit-learn", "jupyter",
    ],
}


def analyze_resume(file_path, target_role, file_name="resume.pdf", user_id=None):

    text = ""

    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    raw_text = text
    text = text.lower()

    def skill_in_text(skill, text):
        escaped = re.escape(skill)
        return bool(re.search(rf'(?<![\w]){escaped}(?![\w])', text, re.IGNORECASE))

    detected = [skill for skill in SKILLS if skill_in_text(skill, text)]

    matched = []
    missing = []

    required = ROLE_SKILLS.get(target_role, [])

    for skill in required:
        if skill in detected:
            matched.append(skill)
        else:
            missing.append(skill)

    score = (
        int(len(matched) / len(required) * 100)
        if required
        else min(len(detected) * 10, 100)
    )

    suggestions = [
        f"Add projects or experience with {skill.title()}"
        for skill in missing
    ]

    if user_id:
        try:
            user = User.objects.get(id=user_id)

            analysis_record, created = ResumeAnalysis.objects.update_or_create(
                user=user,
                file_name=file_name,          
                target_role=target_role,
                defaults={
                    'score': score,
                    'skills_found': detected,
                    'suggestions': suggestions,
                    'matched_skills': matched,
                    'missing_skills': missing,
                }
            )

        except User.DoesNotExist:
            pass

    return {
        "score": score,
        "skills_found": detected,
        "suggestions": suggestions,
        "matched_skills": matched,
        "missing_skills": missing,
        "target_role": target_role,
        "resume_text": raw_text,
    }