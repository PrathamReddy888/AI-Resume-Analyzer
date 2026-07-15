const REPO_URL = "https://github.com/Muskankr/AI-Resume-Analyzer";

export const Footer = () => {
  return (
    <footer className="app-footer">
      <nav className="app-footer__links" aria-label="Footer">
        <a
          href={REPO_URL}
          target="_blank"
          rel="noopener noreferrer"
        >
          ⭐ GitHub
        </a>
      </nav>
      <p className="app-footer__copy">
        © 2026 AI Resume Analyzer
      </p>
    </footer>
  );
};
