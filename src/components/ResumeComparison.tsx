import React, { useState } from "react";

interface AnalysisResult {
  ats_score: number;
  skills: string[];
  keywords: string[];
  word_count: number;
}

interface CompareResult {
  resume_a: AnalysisResult;
  resume_b: AnalysisResult;
  diff: {
    ats_delta: number;
    ats_delta_pct: number;
    skills_added: string[];
    skills_removed: string[];
    skills_common: string[];
    improvement_score: number;
    is_better: boolean;
  };
}

const ResumeComparison: React.FC = () => {
  const [fileA, setFileA] = useState<File | null>(null);
  const [fileB, setFileB] = useState<File | null>(null);
  const [jobDesc, setJobDesc] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState("");

  const handleCompare = async () => {
    if (!fileA || !fileB) {
      setError("Please upload both resumes.");
      return;
    }
    setError("");
    setLoading(true);

    const formData = new FormData();
    formData.append("resume_a", fileA);
    formData.append("resume_b", fileB);
    if (jobDesc) formData.append("job_description", jobDesc);

    try {
      // Adjust this endpoint to match your backend
      const res = await fetch("/api/compare", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Comparison failed");
      const data: CompareResult = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">📊 Resume Comparison Mode</h1>
      <p className="text-gray-600 mb-6">
        Upload two versions of your resume to compare ATS scores and skills side-by-side.
      </p>

      {/* Optional Job Description */}
      <details className="mb-6 bg-gray-50 p-4 rounded-lg">
        <summary className="cursor-pointer font-medium">Job Description (Optional)</summary>
        <textarea
          className="w-full mt-2 p-2 border rounded-md"
          rows={4}
          placeholder="Paste job description..."
          value={jobDesc}
          onChange={(e) => setJobDesc(e.target.value)}
        />
      </details>

      {/* Dual Upload Slots */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
          <h3 className="font-semibold mb-2">📄 Version A (Older / Baseline)</h3>
          <input
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={(e) => setFileA(e.target.files?.[0] || null)}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
          {fileA && <p className="mt-2 text-sm text-green-600">✅ {fileA.name}</p>}
        </div>

        <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
          <h3 className="font-semibold mb-2">📄 Version B (Newer / Updated)</h3>
          <input
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={(e) => setFileB(e.target.files?.[0] || null)}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
          {fileB && <p className="mt-2 text-sm text-green-600">✅ {fileB.name}</p>}
        </div>
      </div>

      <button
        onClick={handleCompare}
        disabled={loading || !fileA || !fileB}
        className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? "Analyzing..." : "🔍 Compare Resumes"}
      </button>

      {error && <p className="mt-4 text-red-600 text-center">{error}</p>}

      {/* Results */}
      {result && (
        <div className="mt-8">
          {/* Summary Banner */}
          <div
            className={`p-4 rounded-lg mb-6 text-center font-semibold ${
              result.diff.is_better
                ? "bg-green-100 text-green-800"
                : "bg-yellow-100 text-yellow-800"
            }`}
          >
            {result.diff.is_better
              ? `🎉 Version B looks better! Improvement: +${result.diff.improvement_score} pts`
              : `⚠️ Version B scores lower. Change: ${result.diff.improvement_score} pts`}
          </div>

          {/* Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white p-4 rounded-lg shadow text-center">
              <p className="text-sm text-gray-500">ATS Δ</p>
              <p
                className={`text-xl font-bold ${
                  result.diff.ats_delta >= 0 ? "text-green-600" : "text-red-600"
                }`}
              >
                {result.diff.ats_delta > 0 ? "+" : ""}
                {result.diff.ats_delta} ({result.diff.ats_delta_pct}%)
              </p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow text-center">
              <p className="text-sm text-gray-500">Skills Added</p>
              <p className="text-xl font-bold text-green-600">
                {result.diff.skills_added.length}
              </p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow text-center">
              <p className="text-sm text-gray-500">Skills Removed</p>
              <p className="text-xl font-bold text-red-600">
                {result.diff.skills_removed.length}
              </p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow text-center">
              <p className="text-sm text-gray-500">Common Skills</p>
              <p className="text-xl font-bold text-blue-600">
                {result.diff.skills_common.length}
              </p>
            </div>
          </div>

          {/* Side-by-Side Detail */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Resume A */}
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-bold mb-3">Resume A</h3>
              <div className="w-full bg-gray-200 rounded-full h-4 mb-2">
                <div
                  className="bg-blue-600 h-4 rounded-full"
                  style={{ width: `${Math.min(result.resume_a.ats_score, 100)}%` }}
                />
              </div>
              <p className="text-sm text-gray-600 mb-4">
                ATS: {result.resume_a.ats_score}/100 | Words: {result.resume_a.word_count}
              </p>
              <div className="flex flex-wrap gap-2">
                {result.resume_a.skills.map((skill) => (
                  <span
                    key={skill}
                    className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>

            {/* Resume B */}
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-bold mb-3">Resume B</h3>
              <div className="w-full bg-gray-200 rounded-full h-4 mb-2">
                <div
                  className={`h-4 rounded-full ${
                    result.diff.ats_delta >= 0 ? "bg-green-600" : "bg-red-500"
                  }`}
                  style={{ width: `${Math.min(result.resume_b.ats_score, 100)}%` }}
                />
              </div>
              <p
                className={`text-sm font-semibold mb-4 ${
                  result.diff.ats_delta >= 0 ? "text-green-600" : "text-red-600"
                }`}
              >
                ATS: {result.resume_b.ats_score}/100 (Δ {result.diff.ats_delta > 0 ? "+" : ""}
                {result.diff.ats_delta})
              </p>
              <div className="flex flex-wrap gap-2">
                {result.resume_b.skills.map((skill) => {
                  const isAdded = result.diff.skills_added.includes(skill);
                  const isCommon = result.diff.skills_common.includes(skill);
                  return (
                    <span
                      key={skill}
                      className={`px-3 py-1 rounded-full text-sm ${
                        isAdded
                          ? "bg-green-100 text-green-800 border border-green-300"
                          : isCommon
                          ? "bg-gray-100 text-gray-700"
                          : "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {skill}
                      {isAdded && " ✨"}
                    </span>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Diff Breakdown */}
          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-green-50 p-4 rounded-lg">
              <h4 className="font-semibold text-green-800 mb-2">▲ Added in Version B</h4>
              {result.diff.skills_added.length > 0 ? (
                <ul className="list-disc list-inside">
                  {result.diff.skills_added.map((s) => (
                    <li key={s} className="text-green-700">
                      <strong>{s}</strong>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-gray-500">No new skills added.</p>
              )}
            </div>

            <div className="bg-red-50 p-4 rounded-lg">
              <h4 className="font-semibold text-red-800 mb-2">▼ Removed from Version B</h4>
              {result.diff.skills_removed.length > 0 ? (
                <ul className="list-disc list-inside">
                  {result.diff.skills_removed.map((s) => (
                    <li key={s} className="text-red-700 line-through">
                      {s}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-gray-500">No skills removed.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ResumeComparison;
