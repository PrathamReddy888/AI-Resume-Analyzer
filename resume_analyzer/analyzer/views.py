from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
import pdfplumber


skills_list = [
    "python","django","react","javascript","sql",
    "html","css","git","github","flask",
    "machine learning","data analysis",
    "excel","microsoft office","ms office",
    "c","c++","java"
]


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def upload_resume(request):

    file = request.FILES.get("file")

    text = ""

    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text

    text = text.lower()

    print(text)   # debug

    detected_skills = []

    for skill in skills_list:
        if skill.lower() in text:
            detected_skills.append(skill)

    score = len(detected_skills) * 10

    if score > 100:
        score = 100

    suggestions = []

    if "python" not in detected_skills:
        suggestions.append("Add Python projects")

    if "django" not in detected_skills:
        suggestions.append("Mention Django experience")

    if "react" not in detected_skills:
        suggestions.append("Add frontend skills like React")

    return Response({
        "score": score,
        "skills_found": detected_skills,
        "suggestions": suggestions
    })