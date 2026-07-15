import re
from rest_framework.decorators import api_view, parser_classes, permission_classes, throttle_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework import status
import pdfplumber
from django.conf import settings

from .models import ResumeAnalysis
from .serializers import SignupSerializer, ResumeAnalysisSerializer


class UploadRateThrottle(SimpleRateThrottle):
    scope = "upload"

    def get_rate(self):
        return getattr(settings, "RESUME_UPLOAD_RATE", "10/hour")

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)  # client IP
        return self.cache_format % {"scope": self.scope, "ident": ident}

skills_list = [
    "python", "django", "react", "javascript", "sql",
    "html", "css", "git", "github", "flask",
    "machine learning", "data analysis",
    "excel", "microsoft office", "ms office",
    "c", "c++", "java"
]

ROLE_SKILL_MATRICES = {
    "Frontend Developer": ["html", "css", "javascript", "react", "git", "github"],
    "Backend Developer": ["python", "django", "flask", "sql", "git", "github"],
    "Data Analyst": ["python", "excel", "sql", "data analysis", "machine learning"]
}


# ---------------------------------------------------------------------------
# Core analysis helpers — shared by upload_resume and match_jd so the single
# upload flow is unchanged and the new JD-matching flow can reuse the same
# text-extraction + skill-detection logic. Issue #18 requires a NEW endpoint
# but the analysis primitives stay identical.
# ---------------------------------------------------------------------------

def _extract_pdf_text(file_obj):
    """Extract raw (un-lowercased) text from a PDF file-like object."""
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    text = ""
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def _analyze_text(text, target_role):
    """
    Run the original analysis pipeline on already-extracted resume text.

    Returns a dict with the same keys as the public upload_resume response
    so single-upload and JD-match flows produce identical per-resume shapes.
    """
    text = text.lower()

    detected_skills = [s for s in skills_list if s.lower() in text]

    matched_skills = []
    missing_skills = []

    if target_role in ROLE_SKILL_MATRICES:
        required_skills = ROLE_SKILL_MATRICES[target_role]

        for skill in required_skills:
            if skill in detected_skills:
                matched_skills.append(skill)
            else:
                missing_skills.append(skill)

        # Dynamic role-based score
        score = int((len(matched_skills) / len(required_skills)) * 100) if required_skills else 100

        # Dynamic suggestions
        suggestions = [
            f"Add experience or projects with {skill.upper() if skill in ['html', 'css', 'sql', 'git'] else skill.capitalize()}"
            for skill in missing_skills
        ]
    else:
        score = min(len(detected_skills) * 10, 100)

        suggestions = []
        if "python" not in detected_skills:
            suggestions.append("Add Python projects")
        if "django" not in detected_skills:
            suggestions.append("Mention Django experience")
        if "react" not in detected_skills:
            suggestions.append("Add frontend skills like React")

    return {
        "score": score,
        "skills_found": detected_skills,
        "suggestions": suggestions,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
    }


def _persist_analysis(user, file_name, analysis, target_role):
    """Save a single analysis record for an authenticated user."""
    if not (user and user.is_authenticated):
        return
    ResumeAnalysis.objects.create(
        user=user,
        file_name=file_name,
        score=analysis["score"],
        skills_found=analysis["skills_found"],
        suggestions=analysis["suggestions"],
        matched_skills=analysis["matched_skills"],
        missing_skills=analysis["missing_skills"],
        target_role=target_role or "",
    )


# ---------------------------------------------------------------------------
# JD keyword extraction (issue #18).
#
# The issue says: "get a match percentage plus a list of missing keywords /
# skills relative to that specific JD, not just a generic skill list."
#
# Strategy:
#   1. First, detect every known skill from our curated `skills_list` that
#      appears in the JD. These are the "must-have" technical keywords we
#      can match exactly against the resume.
#   2. Second, extract additional non-skill keywords from the JD using a
#      lightweight regex tokenizer + stopword filter. These catch domain
#      terms (e.g. "kubernetes", "swagger", "graphql") that aren't in our
#      curated list. Multi-word phrases of 2-3 words are also captured
#      (e.g. "REST APIs", "CI/CD pipelines") so the match is more semantic
#      than a pure bag-of-words.
#   3. Return the union as the JD's required keyword set. Each keyword is
#      then checked against the resume text (case-insensitive substring).
# ---------------------------------------------------------------------------

# Conservative English stopword set — kept small on purpose so we don't
# accidentally filter out real technical terms. Sourced from the standard
# NLTK English stoplist, trimmed to the highest-frequency ~130 words.
_STOPWORDS = frozenset("""
a about above after again against all am an and any are aren't as at be because been before being below between both but by can can't cannot could couldn't did didn't do does doesn't doing don't down during each few for from further had hadn't has hasn't have haven't having he he'd he'll he's her here here's hers herself him himself his how how's i i'd i'll i'm i've if in into is isn't it it's its itself let's me more most mustn't my myself no nor not of off on once only or other ought our ours ourselves out over own same shan't she she'd she'll she's should shouldn't so some such than that that's the their theirs them themselves then there there's these they they'd they'll they're they've this those through to too under until up very was wasn't we we'd we'll we're we've were weren't what what's when when's where where's which while who who's whom why why's with won't would wouldn't you you'd you'll you're you've your yours yourself yourselves
""".split())

# Tokens that are technically words but carry no JD-relevant signal. These
# get filtered alongside stopwords so the returned keyword list is clean.
# Keep this list conservative — over-filtering hides real keywords.
_JD_NOISE_TOKENS = frozenset({
    # JD structural headers / labels
    "role", "responsibilities", "requirements", "qualifications",
    "preferred", "must", "plus", "etc", "eg", "ie",
    "year", "years", "experience", "work", "working", "job", "position",
    "team", "teams", "company", "candidate", "candidates", "ideal",
    # Generic adjectives that aren't keywords
    "strong", "excellent", "good", "great", "ability",
    # Generic verbs that aren't keywords
    "including", "include", "includes", "across", "within", "per",
    "join", "build", "builds", "building", "built", "use", "uses", "using",
    "help", "helps", "helping", "helped", "ensure", "ensures",
    "design", "designs", "designing", "designed",
    "develop", "develops", "developing", "developed", "developer", "developers",
    "create", "creates", "creating", "created",
    "maintain", "maintains", "maintaining", "maintained",
    "manage", "manages", "managing", "managed", "manager",
    "support", "supports", "supporting", "supported",
    # Generic nouns that describe the JD itself, not the tech stack
    "platform", "platforms", "application", "applications", "app", "apps",
    "system", "systems", "service", "services",
    "feature", "features", "product", "products",
    "solution", "solutions", "tool", "tools",
    "environment", "environments",
    "knowledge", "understanding", "familiarity", "proficiency",
    "background", "degree", "education",
    "infrastructure", "cloud", "deployments", "development", "stores",
    "looking", "nice", "senior", "junior", "lead", "engineer", "engineers",
    # Equal-opportunity boilerplate
    "equal", "opportunity", "employer",
})


def _extract_jd_keywords(jd_text):
    """
    Extract the set of required keywords/skills from a pasted job description.

    Returns a sorted list of unique keywords (lowercased). Multi-word phrases
    of 2-3 words (e.g. "rest apis", "ci cd") are included alongside single
    tokens so the matcher can do semantic phrase matching, not just bag-of-words.
    """
    if not jd_text or not jd_text.strip():
        return []

    text = jd_text.lower()

    # Step 1: detect known skills from our curated list. These are the
    # high-confidence technical requirements — we want them in the keyword
    # set even if a generic tokenizer would have split them.
    found = set()
    for skill in skills_list:
        # Use word-boundary regex for single-word skills to avoid substring
        # false positives (e.g. "c" matching inside "css"). Multi-word
        # skills like "machine learning" can use plain substring search.
        if " " in skill or "+" in skill:
            if skill in text:
                found.add(skill)
        else:
            if re.search(r"\b" + re.escape(skill) + r"\b", text):
                found.add(skill)

    # Step 2: extract additional candidate single tokens via regex.
    # Match single words of 3+ letters that may include tech chars
    # (e.g. "api", "sql", "aws", "kubernetes", "c++", "node.js").
    token_pattern = re.compile(r"[a-z][a-z0-9+./#-]{2,}")
    for match in token_pattern.finditer(text):
        token = match.group(0).rstrip(".,;:!?")
        if not token or len(token) < 3:
            continue
        if token.isdigit():
            continue
        if token in _STOPWORDS or token in _JD_NOISE_TOKENS:
            continue
        found.add(token)

    # Step 3: extract 2-3 word phrases so we can do semantic phrase matching
    # (e.g. "rest apis", "ci cd", "machine learning pipelines"). We only
    # keep a phrase if ALL its constituent tokens are non-stopword and
    # non-noise — this avoids returning phrases like "the team" while
    # preserving real technical phrases.
    phrase_pattern = re.compile(
        r"[a-z][a-z0-9+./#-]{1,}(?:\s+[a-z][a-z0-9+./#-]{1,}){1,2}"
    )
    for match in phrase_pattern.finditer(text):
        phrase = match.group(0).strip().rstrip(".,;:!?")
        if not phrase:
            continue
        tokens = phrase.split()
        if len(tokens) < 2 or len(tokens) > 3:
            continue
        # Keep the phrase only if every token is meaningful (non-stopword,
        # non-noise). This is what filters out "the team" / "you will" while
        # preserving "rest apis" / "ci cd".
        if all(tok not in _STOPWORDS and tok not in _JD_NOISE_TOKENS for tok in tokens):
            found.add(" ".join(tokens))

    return sorted(found)


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    serializer = SignupSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"detail": "Account created."}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([AllowAny])
@throttle_classes([UploadRateThrottle])
def upload_resume(request):
    file = request.FILES.get("file")
    target_role = request.data.get("role", None)
    file_name = file.name if file else "unknown"

    if not file:
        return Response(
            {"detail": "No file uploaded. Please attach a resume."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        text = _extract_pdf_text(file)
    except Exception as exc:
        return Response(
            {"detail": f"Could not read the uploaded file: {exc}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    analysis = _analyze_text(text, target_role)
    _persist_analysis(request.user, file_name, analysis, target_role)

    return Response({
        "score": analysis["score"],
        "skills_found": analysis["skills_found"],
        "suggestions": analysis["suggestions"],
        "target_role": target_role,
        "matched_skills": analysis["matched_skills"],
        "missing_skills": analysis["missing_skills"],
    })


# ---------------------------------------------------------------------------
# JD matching endpoint — Issue #18
# Accepts a resume PDF + pasted job-description text and returns:
#   - match_percent: 0-100 (matched / total keywords)
#   - matched_keywords: keywords present in BOTH resume and JD
#   - missing_keywords: keywords in the JD but NOT in the resume
#   - resume_skills_detected: skills from the curated list found in the resume
#                             (reused from the existing analyzer so the JD
#                             match view also shows the generic skill list)
#   - jd_keyword_count: how many unique keywords were extracted from the JD
# ---------------------------------------------------------------------------

@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([AllowAny])
@throttle_classes([UploadRateThrottle])
def match_jd(request):
    """
    Compare an uploaded resume against a pasted job description.

    Accepts multipart form fields:
      - file: resume PDF
      - jd:   job-description text (plain text, any length)

    Returns:
      {
        "match_percent":        int,    # 0-100, rounded
        "matched_keywords":     [...],  # JD keywords found in the resume
        "missing_keywords":     [...],  # JD keywords NOT found in the resume
        "resume_skills_detected": [...], # curated skills present in resume
        "jd_keyword_count":     int,    # total unique keywords extracted from JD
        "file_name":            str
      }
    """
    file = request.FILES.get("file")
    jd_text = request.data.get("jd", "") or ""

    if not file:
        return Response(
            {"detail": "No file uploaded. Please attach a resume."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not jd_text.strip():
        return Response(
            {"detail": "No job description provided. Please paste the JD text."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --- Extract resume text ------------------------------------------------
    try:
        resume_text = _extract_pdf_text(file)
    except Exception as exc:
        return Response(
            {"detail": f"Could not read the uploaded file: {exc}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    resume_text_lower = resume_text.lower()

    # --- Extract JD keywords ------------------------------------------------
    jd_keywords = _extract_jd_keywords(jd_text)

    # --- Match each JD keyword against the resume text ----------------------
    # For multi-word phrase keywords, use plain substring search so "rest apis"
    # matches even if the resume writes "REST APIs" or "rest apis". For single
    # tokens, use word-boundary regex to avoid false positives like "c"
    # matching inside "css".
    matched_keywords = []
    missing_keywords = []
    for kw in jd_keywords:
        if " " in kw:
            if kw in resume_text_lower:
                matched_keywords.append(kw)
            else:
                missing_keywords.append(kw)
        else:
            if re.search(r"\b" + re.escape(kw) + r"\b", resume_text_lower):
                matched_keywords.append(kw)
            else:
                missing_keywords.append(kw)

    # --- Compute match percentage ------------------------------------------
    total = len(jd_keywords)
    if total == 0:
        match_percent = 0
    else:
        match_percent = int(round((len(matched_keywords) / total) * 100))

    # --- Also run the existing skill detector on the resume so the UI can
    #     show "Skills detected in your resume" alongside the JD-specific
    #     match view (reuses the curated skills_list). -----------------------
    resume_skills_detected = [s for s in skills_list if s.lower() in resume_text_lower]

    # Persist a regular analysis row for authenticated users so the JD match
    # also shows up in their history (we use the JD-derived match_percent as
    # the score, and the missing keywords as suggestions for traceability).
    if request.user and request.user.is_authenticated:
        ResumeAnalysis.objects.create(
            user=request.user,
            file_name=file.name,
            score=match_percent,
            skills_found=resume_skills_detected,
            suggestions=[f"Add JD keyword: {kw}" for kw in missing_keywords[:10]],
            matched_skills=matched_keywords,
            missing_skills=missing_keywords,
            target_role="JD Match",
        )

    return Response({
        "match_percent": match_percent,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "resume_skills_detected": resume_skills_detected,
        "jd_keyword_count": total,
        "file_name": file.name,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analysis_history(request):
    analyses = ResumeAnalysis.objects.filter(user=request.user)
    serializer = ResumeAnalysisSerializer(analyses, many=True)
    return Response(serializer.data)
