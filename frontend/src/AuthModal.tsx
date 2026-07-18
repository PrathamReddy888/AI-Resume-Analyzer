import React, { useState } from "react";
import { useToast } from "./hooks/useToast";

interface AuthModalProps {
  onSignup: (username: string, password: string) => Promise<void>;
  onLogin: (username: string, password: string) => Promise<void>;
  onClose: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ onSignup, onLogin, onClose }) => {
  const { showToast } = useToast();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (mode === "signup") await onSignup(username, password);
      else await onLogin(username, password);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Authentication failed";
      showToast(msg, "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-overlay" onClick={onClose}>
      <div className="auth-modal" onClick={(e) => e.stopPropagation()}>
        <h3>{mode === "login" ? "🔐 Login" : "📝 Sign Up"}</h3>
        <form onSubmit={submit}>
          <input
            className="auth-input"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoFocus
          />
          <input
            className="auth-input"
            type="password"
            placeholder="Password (min 6 chars)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button className="auth-submit-btn" type="submit" disabled={loading}>
            {loading ? "⏳ Please wait..." : mode === "login" ? "Login" : "Create Account"}
          </button>
        </form>
        <p className="auth-switch">
          {mode === "login" ? "No account? " : "Have an account? "}
          <button className="auth-switch-btn" onClick={() => { setMode(mode === "login" ? "signup" : "login"); }}>
            {mode === "login" ? "Sign up" : "Log in"}
          </button>
        </p>
      </div>
    </div>
  );
};
