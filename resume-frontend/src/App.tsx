import { useState } from "react";
import axios from "axios";
import "./index.css";

function App() {
  const [loading, setLoading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [score, setScore] = useState<number | null>(null);
  const [skills, setSkills] = useState<string[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  
  // New states for clean inline and banner error handling
  const [inlineError, setInlineError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInlineError(null); // Clear previous errors
    setApiError(null);

    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];

      // Acceptance Criteria: Non-PDF files show a clear inline error before upload
      if (selectedFile.type !== "application/pdf") {
        setInlineError("⚠️ Only PDF files are supported. Please select a valid PDF.");
        setFile(null); // Clear invalid file from state
        return;
      }

      setFile(selectedFile);
    }
  };

  const uploadResume = async () => {
    if (!file) {
      setInlineError("⚠️ Please upload a resume first.");
      return;
    }

    // Reset API errors before initiating a new call
    setApiError(null);

    try {
      setLoading(true);   

      const formData = new FormData();
      formData.append("file", file);

      const res = await axios.post(
        "http://127.0.0.1:8000/api/upload/",
        formData
      );

      setScore(res.data.score);
      setSkills(res.data.skills_found);
      setSuggestions(res.data.suggestions);

    } catch (error: any) {
      console.error(error);
      
      // Acceptance Criteria: Failed API calls show a banner with a readable message
      if (!window.navigator.onLine) {
        setApiError("🔌 Network Error: Please check your internet connection.");
      } else if (error.response) {
        setApiError(`❌ Server Error (${error.response.status}): Failed to analyze resume.`);
      } else {
        setApiError("⚠️ Could not reach the server. Make sure your backend service is running.");
      }
    } finally {
      // Acceptance Criteria: Errors don't crash the app or leave it stuck loading
      setLoading(false);   
    }
  };

  return (
    <div className="container mt-5">
      <div className="main-card text-center">
        <h1 className="mb-4">🚀 AI Resume Analyzer</h1>
        
        {/* API Error Banner Notification */}
        {apiError && (
          <div className="error-banner mb-3" style={{
            backgroundColor: "#fee2e2",
            color: "#dc2626",
            padding: "12px",
            borderRadius: "8px",
            border: "1px solid #fca5a5",
            fontSize: "14px",
            fontWeight: "500",
            textAlign: "left"
          }}>
            {apiError}
          </div>
        )}

        <div className="upload-box mb-3">
          <input
            type="file"
            id="fileUpload"
            accept=".pdf" // Restricts native picker view to PDFs
            hidden
            onChange={handleFileChange}
          />

          <label htmlFor="fileUpload" className="upload-label">
            📄 {file ? file.name : "Drag & Drop Resume or Click to Upload"}
          </label>
        </div>

        {/* Inline Error Message for File Type Validation */}
        {inlineError && (
          <p className="error-text mb-3" style={{ color: "#dc2626", fontSize: "14px", fontWeight: "500" }}>
            {inlineError}
          </p>
        )}

        <button
          className="analyze-btn"
          onClick={uploadResume}
          disabled={loading} // Prevent multiple clicks while uploading
        >
          {loading ? "⏳ Analyzing..." : "🚀 Analyze Resume"}
        </button>

        {score !== null && (
          <>
            {/* SCORE METER */}
            <div className="score-section">
              <div
                className="score-circle mb-3"
                style={{ "--score": `${score * 3.6}deg` } as React.CSSProperties}
              >
                {score}%
              </div>
              <h3>ATS Resume Score</h3>
              <h5 className="analysis-done">
                ✅ Resume Analysis Complete
              </h5>
            </div>

            {/* SKILLS */}
            <div className="mt-4">
              <h4>Skills Found</h4>
              {skills.length === 0 && <p>No skills detected</p>}
              {skills.map((skill: string, i: number) => (
                <span key={i} className="skill-badge">
                  {skill}
                </span>
              ))}
            </div>

            {/* SUGGESTIONS */}
            <div className="suggestion-box">
              <h4>💡 Suggestions</h4>
              {suggestions.map((s, i) => (
                <div key={i} className="suggestion-item">
                  📌 {s}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default App;
