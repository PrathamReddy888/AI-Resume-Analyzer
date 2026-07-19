import { NextRequest, NextResponse } from "next/server";

// Replace this with your actual analyzer call
async function analyzeResume(text: string, jobDesc?: string) {
  // TODO: Wire this to your real analyzer
  // Mock return for now:
  const words = text.match(/\b\w+\b/g) || [];
  const skillsPool = new Set([
    "python", "javascript", "typescript", "react", "node.js", "sql", "aws",
    "docker", "kubernetes", "machine learning", "git", "linux", "agile",
    "html", "css", "pandas", "numpy", "tensorflow", "communication"
  ]);
  const found = Array.from(skillsPool).filter((s) => text.toLowerCase().includes(s));
  const ats = Math.min(100, Math.max(0, 40 + found.length * 5 + Math.floor(words.length / 100)));
  return {
    ats_score: Math.round(ats * 10) / 10,
    skills: found.sort(),
    keywords: Array.from(new Set(words)).slice(0, 20),
    word_count: words.length,
  };
}

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const fileA = formData.get("resume_a") as File;
    const fileB = formData.get("resume_b") as File;
    const jobDesc = formData.get("job_description") as string | undefined;

    if (!fileA || !fileB) {
      return NextResponse.json({ error: "Both resumes required" }, { status: 400 });
    }

    const textA = await fileA.text();
    const textB = await fileB.text();

    const [a, b] = await Promise.all([
      analyzeResume(textA, jobDesc),
      analyzeResume(textB, jobDesc),
    ]);

    const setA = new Set(a.skills);
    const setB = new Set(b.skills);

    const added = Array.from(setB).filter((s) => !setA.has(s)).sort();
    const removed = Array.from(setA).filter((s) => !setB.has(s)).sort();
    const common = Array.from(setA).filter((s) => setB.has(s)).sort();

    const atsDelta = b.ats_score - a.ats_score;
    const atsDeltaPct = (atsDelta / Math.max(a.ats_score, 1)) * 100;
    const improvement = atsDelta + added.length * 2.5 - removed.length * 1.5;

    return NextResponse.json({
      resume_a: a,
      resume_b: b,
      diff: {
        ats_delta: Math.round(atsDelta * 10) / 10,
        ats_delta_pct: Math.round(atsDeltaPct * 10) / 10,
        skills_added: added,
        skills_removed: removed,
        skills_common: common,
        improvement_score: Math.round(improvement * 10) / 10,
        is_better: improvement > 0,
      },
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Internal error" }, { status: 500 });
  }
}
