import { Link } from "react-router-dom";
import "./Landing.css";

const features = [
  {
    number: "01",
    title: "Data Upload",
    text: "Bring CSV and XLSX business data into one secure analytics workspace.",
  },
  {
    number: "02",
    title: "Data Cleaning",
    text: "Detect missing values, duplicates, inconsistent types, and quality issues.",
  },
  {
    number: "03",
    title: "Analytics",
    text: "Explore trends, distributions, KPIs, correlations, and business metrics.",
  },
  {
    number: "04",
    title: "AI Insights",
    text: "Use local AI to turn analytical results into understandable business insights.",
  },
  {
    number: "05",
    title: "Predictions",
    text: "Forecast future trends and identify unusual behavior in your data.",
  },
  {
    number: "06",
    title: "Reports",
    text: "Generate professional reports from your completed analysis.",
  },
];

const workflow = [
  ["01", "Upload", "Connect your business dataset."],
  ["02", "Process", "Clean and validate the data."],
  ["03", "Analyze", "Run statistical and business analysis."],
  ["04", "Understand", "Let AI explain important patterns."],
  ["05", "Act", "Turn findings into business decisions."],
];

export default function Landing() {
  return (
    <main className="landing-page">
      <nav className="landing-nav">
        <Link to="/" className="landing-logo">
          Insight<span>OS</span>
        </Link>

        <div className="landing-nav-links">
          <a href="#features">Features</a>
          <a href="#workflow">Workflow</a>
          <a href="#ai">AI</a>
          <a href="#about">About</a>
        </div>

        <div className="landing-nav-actions">
          <Link to="/login" className="nav-login">
            Login
          </Link>

          <Link to="/signup" className="nav-start">
            Get Started
            <span>↗</span>
          </Link>
        </div>
      </nav>

      <section className="hero-section">
        <div className="hero-content">
          <div className="hero-eyebrow">
            <span className="eyebrow-dot" />
            AI-POWERED BUSINESS ANALYTICS
          </div>

          <h1>
            Turn raw data
            <br />
            into <em>business decisions.</em>
          </h1>

          <p className="hero-description">
            InsightOS gives businesses one intelligent workspace to upload,
            clean, analyze, understand, and act on their data.
          </p>

          <div className="hero-actions">
            <Link to="/login" className="primary-button">
              Start Analyzing
              <span>→</span>
            </Link>

            <a href="#workflow" className="secondary-button">
              Explore Platform
              <span>↓</span>
            </a>
          </div>

          <div className="hero-stats">
            <div>
              <strong>CSV / XLSX</strong>
              <span>Data sources</span>
            </div>

            <div>
              <strong>AI Powered</strong>
              <span>Local intelligence</span>
            </div>

            <div>
              <strong>Interactive</strong>
              <span>Business analytics</span>
            </div>
          </div>
        </div>

        <div className="hero-visual">
          <div className="hero-image-wrap">
            <img
              src="src\assets\images\hero.jpg"
              alt="Business analytics workspace"
            />

            <div className="hero-image-overlay" />
          </div>
{/* 
          <div className="floating-card revenue-card">
            <span className="floating-label">REVENUE</span>
            <strong>$2.45M</strong>
            <small>↑ 18.4%</small>
          </div> */}

          {/* <div className="floating-card insight-card">
            <span className="floating-label">AI INSIGHT</span>
            <p>Growth opportunity detected</p>
          </div>

          <div className="floating-card quality-card">
            <span className="floating-label">DATA QUALITY</span>
            <strong>97.8%</strong>
          </div> */}
        </div>
      </section>

      <section className="value-strip">
        {[
          ["01", "Upload Data"],
          ["02", "Clean & Validate"],
          ["03", "Analyze"],
          ["04", "Generate Insights"],
        ].map(([number, title]) => (
          <div className="value-item" key={number}>
            <span>{number}</span>
            <strong>{title}</strong>
          </div>
        ))}
      </section>

      <section className="section features-section" id="features">
        <div className="section-heading">
          <div>
            <span className="section-eyebrow">THE PLATFORM</span>
            <h2>
              Everything you need
              <br />
              to understand your data.
            </h2>
          </div>

          <p>
            From the first uploaded file to the final business decision,
            InsightOS brings the complete analytical workflow into one place.
          </p>
        </div>

        <div className="feature-grid">
          {features.map((feature) => (
            <article className="feature-card" key={feature.number}>
              <span className="feature-number">{feature.number}</span>

              <div className="feature-icon">
                <span />
              </div>

              <h3>{feature.title}</h3>

              <p>{feature.text}</p>

              <span className="feature-arrow">↗</span>
            </article>
          ))}
        </div>
      </section>

      <section className="workflow-section section" id="workflow">
        <div className="section-heading workflow-heading">
          <div>
            <span className="section-eyebrow">HOW IT WORKS</span>
            <h2>
              From dataset
              <br />
              to decision.
            </h2>
          </div>

          <p>
            A structured workflow designed to keep your analysis clear,
            repeatable, and useful.
          </p>
        </div>

        <div className="workflow-line">
          {workflow.map(([number, title, text]) => (
            <div className="workflow-step" key={number}>
              <div className="workflow-number">{number}</div>
              <h3>{title}</h3>
              <p>{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="ai-section section" id="ai">
        <div className="ai-copy">
          <span className="section-eyebrow">INTELLIGENT ANALYSIS</span>

          <h2>
            Don't just see
            <br />
            the numbers.
            <br />
            <em>Understand them.</em>
          </h2>

          <p>
            InsightOS combines traditional analytics with local AI to explain
            what is happening inside your data and highlight opportunities
            worth investigating.
          </p>

          <ul>
            <li>
              <span>01</span>
              Explain important patterns
            </li>
            <li>
              <span>02</span>
              Identify business opportunities
            </li>
            <li>
              <span>03</span>
              Answer questions about your data
            </li>
          </ul>
        </div>

        <div className="ai-panel">
          <div className="ai-panel-header">
            <div>
              <strong>InsightOS AI</strong>
              <span>● Online</span>
            </div>

            <span className="ai-model">LOCAL AI</span>
          </div>

          <div className="ai-panel-body">
            <span className="ai-label">AI INSIGHT</span>

            <p>
              Revenue increased <strong>18.4%</strong> during the selected
              period, with Electronics contributing the strongest growth.
            </p>

            <div className="ai-divider" />

            <span className="ai-question-label">
              Ask something about your data
            </span>

            <div className="ai-question">
              <span>Why did revenue increase?</span>
              <span>→</span>
            </div>
          </div>
        </div>
      </section>

      <section className="final-cta" id="about">
        <span className="section-eyebrow">INSIGHTOS</span>

        <h2>
          Make your data
          <br />
          <em>work harder.</em>
        </h2>

        <p>
          Build a smarter analytics workflow and make decisions with evidence,
          not assumptions.
        </p>

        <Link to="/signup" className="primary-button">
          Get Started
          <span>→</span>
        </Link>
      </section>

      <footer className="landing-footer">
        <Link to="/" className="landing-logo">
          Insight<span>OS</span>
        </Link>

        <p>AI-powered analytics for modern businesses.</p>

        <div>
          <a href="#features">Features</a>
          <a href="#workflow">Workflow</a>
          <a href="#ai">AI</a>
          <Link to="/login">Login</Link>
        </div>

        <small>© 2026 InsightOS. All rights reserved.</small>
      </footer>
    </main>
  );
}