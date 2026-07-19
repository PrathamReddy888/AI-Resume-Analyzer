"""
Resume Comparison Engine
Issue #22 — Adds side-by-side resume comparison with diff highlighting.
"""

import io
import re
from typing import Dict, List, Optional, Set

# ═══════════════════════════════════════════════════════════════
# NOTE: Update this import to your actual analyzer module
# If your analyzer is in app.py or another file, adjust accordingly.
# ═══════════════════════════════════════════════════════════════
try:
    from resume_analyzer import analyze_resume as _single_analyze
except ImportError:
    # Fallback: replace this with your real analyze_resume() function
    _single_analyze = None


def _mock_analyze(text: str, job_desc: Optional[str] = None) -> Dict:
    """
    REMOVE THIS once you wire up your real analyzer.
    This is only a fallback so the file is syntactically valid.
    """
    words = re.findall(r'\b\w+\b', text.lower())
    skills_pool = {
        "python", "java", "javascript", "react", "node.js", "sql", "aws",
        "docker", "kubernetes", "machine learning", "deep learning", "nlp",
        "html", "css", "typescript", "git", "linux", "agile", "scrum",
        "data analysis", "pandas", "numpy", "tensorflow", "pytorch",
        "communication", "leadership", "project management", "excel",
        "tableau", "powerbi", "spark", "hadoop", "mongodb", "postgresql",
        "c++", "go", "rust", "flutter", "django", "flask", "fastapi"
    }
    found_skills = [s for s in skills_pool if s in text.lower()]
    ats = min(100, max(0, 40 + len(found_skills) * 5 + (len(words) // 100)))
    return {
        "ats_score": round(ats, 1),
        "skills": sorted(found_skills),
        "keywords": sorted(set(words))[:20],
        "word_count": len(words),
    }


def _get_analyzer():
    return _single_analyze if _single_analyze is not None else _mock_analyze


def extract_text(uploaded_file) -> str:
    """
    Extract text from an uploaded file (PDF, DOCX, or TXT).
    Re-uses the file object safely.
    """
    if uploaded_file is None:
        return ""

    uploaded_file.seek(0)
    raw_bytes = uploaded_file.read()
    uploaded_file.seek(0)

    name = getattr(uploaded_file, "name", "").lower()

    if name.endswith(".pdf"):
        # Try pdfplumber first, then PyPDF2
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception:
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(io.BytesIO(raw_bytes))
                return "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception as e:
                return f"[PDF extraction failed: {e}]"

    if name.endswith(".docx"):
        try:
            import docx2txt
            return docx2txt.process(io.BytesIO(raw_bytes))
        except Exception as e:
            return f"[DOCX extraction failed: {e}]"

    # Plain text fallback
    return raw_bytes.decode("utf-8", errors="ignore")


def analyze_single(resume_text: str, job_description: Optional[str] = None) -> Dict:
    """Normalize the output from your existing analyzer."""
    analyzer = _get_analyzer()
    result = analyzer(resume_text, job_description)

    # Normalize keys so the comparison UI always gets consistent data
    return {
        "ats_score": float(result.get("ats_score", 0) or 0),
        "skills": list(result.get("skills", [])),
        "keywords": list(result.get("keywords", [])),
        "word_count": int(result.get("word_count", 0)),
        "raw_text": resume_text,
    }


def compare_two_resumes(
    text_a: str,
    text_b: str,
    job_description: Optional[str] = None,
) -> Dict:
    """
    Compare two resume versions side-by-side.

    Returns
    -------
    dict
        {
            "resume_a": {ats_score, skills, ...},
            "resume_b": {ats_score, skills, ...},
            "diff": {
                "ats_delta": float,
                "ats_delta_pct": float,
                "skills_added": List[str],
                "skills_removed": List[str],
                "skills_common": List[str],
                "skill_change_net": int,
                "improvement_score": float,
                "is_better": bool,
            },
        }
    """
    a = analyze_single(text_a, job_description)
    b = analyze_single(text_b, job_description)

    skills_a: Set[str] = set(a["skills"])
    skills_b: Set[str] = set(b["skills"])

    added: List[str] = sorted(skills_b - skills_a)
    removed: List[str] = sorted(skills_a - skills_b)
    common: List[str] = sorted(skills_a & skills_b)

    ats_delta = b["ats_score"] - a["ats_score"]
    ats_delta_pct = (ats_delta / max(a["ats_score"], 1.0)) * 100

    # Simple composite improvement metric
    improvement = ats_delta
    improvement += len(added) * 2.5
    improvement -= len(removed) * 1.5

    return {
        "resume_a": a,
        "resume_b": b,
        "diff": {
            "ats_delta": round(ats_delta, 1),
            "ats_delta_pct": round(ats_delta_pct, 1),
            "skills_added": added,
            "skills_removed": removed,
            "skills_common": common,
            "skill_change_net": len(added) - len(removed),
            "improvement_score": round(improvement, 1),
            "is_better": improvement > 0,
        },
    }
