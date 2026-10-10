import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import "./Auth.css";

const API = "http://127.0.0.1:8000/api";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const successMessage = location.state?.message;

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (!email.trim() || !password) {
      setError("Please enter your email and password.");
      return;
    }

    try {
      setLoading(true);

      const response = await fetch(
        `${API}/auth/login?email=${encodeURIComponent(email.trim())}&password=${encodeURIComponent(password)}`,
        {
          method: "POST",
          headers: {
            Accept: "application/json",
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Invalid email or password.");
      }

      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));

      navigate("/projects", { replace: true });
    } catch (err) {
      setError(
        err.message || "Unable to connect to the InsightOS backend."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <div className="auth-background-grid" />

      <div className="auth-glow auth-glow-one" />
      <div className="auth-glow auth-glow-two" />

      <section className="auth-card">
        <Link to="/" className="auth-brand">
          Insight<span>OS</span>
        </Link>

        <div className="auth-heading">
          <span>WELCOME BACK</span>

          <h1>Sign in to InsightOS</h1>

          <p>
            Access your analytics workspace and continue turning data into
            decisions.
          </p>
        </div>

        {successMessage && (
          <div className="auth-success">
            {successMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          <label>
            Email address

            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@company.com"
              autoComplete="email"
            />
          </label>

          <label>
            Password

            <div className="password-field">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter your password"
                autoComplete="current-password"
              />

              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword((value) => !value)}
                aria-label={
                  showPassword ? "Hide password" : "Show password"
                }
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </label>

          {error && <div className="auth-error">{error}</div>}

          <button
            type="submit"
            className="auth-submit"
            disabled={loading}
          >
            {loading ? "Signing in..." : "Sign in"}

            {!loading && <span>→</span>}
          </button>
        </form>

        <div className="auth-footer">
          <span>Don't have an account?</span>

          <Link to="/signup">Create account</Link>
        </div>

        <Link to="/" className="back-home">
          ← Back to InsightOS
        </Link>
      </section>
    </main>
  );
}