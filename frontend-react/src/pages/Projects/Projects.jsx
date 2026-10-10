import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import "./Projects.css";

const API = "http://127.0.0.1:8000/api";

export default function Projects() {
  const navigate = useNavigate();

  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [openMenu, setOpenMenu] = useState(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");

  const token = localStorage.getItem("access_token");
  const user = JSON.parse(localStorage.getItem("user") || "null");

  useEffect(() => {
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }

    loadProjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function loadProjects() {
    try {
      setLoading(true);
      setError("");

      const response = await fetch(`${API}/projects`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.status === 401) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
        navigate("/login", { replace: true });
        return;
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to load projects.");
      }

      setProjects(data);
    } catch (err) {
      setError(err.message || "Unable to load projects.");
    } finally {
      setLoading(false);
    }
  }

  async function createProject(event) {
    event.preventDefault();

    if (!name.trim()) {
      setError("Project name is required.");
      return;
    }

    try {
      setError("");

      const params = new URLSearchParams({
        name: name.trim(),
      });

      if (description.trim()) {
        params.append("description", description.trim());
      }

      const response = await fetch(
        `${API}/projects?${params.toString()}`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Unable to create project."
        );
      }

      setProjects((current) => [data.project, ...current]);
      setName("");
      setDescription("");
      setShowCreate(false);
    } catch (err) {
      setError(err.message || "Unable to create project.");
    }
  }

  async function renameProject(project) {
    setOpenMenu(null);

    const nextName = window.prompt(
      "Enter a new project name:",
      project.name
    );

    if (nextName === null) return;

    const trimmedName = nextName.trim();

    if (!trimmedName) {
      setError("Project name is required.");
      return;
    }

    if (trimmedName === project.name) return;

    try {
      setError("");

      const params = new URLSearchParams({
        name: trimmedName,
      });

      const response = await fetch(
        `${API}/projects/${project.id}?${params.toString()}`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.status === 401) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
        navigate("/login", { replace: true });
        return;
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Unable to rename project."
        );
      }

      setProjects((current) =>
        current.map((item) =>
          item.id === project.id
            ? { ...item, ...data.project }
            : item
        )
      );
    } catch (err) {
      setError(err.message || "Unable to rename project.");
    }
  }

  async function deleteProject(project) {
    setOpenMenu(null);

    const confirmed = window.confirm(
      `Delete "${project.name}"?\n\nThe project will be permanently removed. Connected datasets will not be deleted.`
    );

    if (!confirmed) return;

    try {
      setError("");

      const response = await fetch(
        `${API}/projects/${project.id}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.status === 401) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
        navigate("/login", { replace: true });
        return;
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Unable to delete project."
        );
      }

      setProjects((current) =>
        current.filter((item) => item.id !== project.id)
      );
    } catch (err) {
      setError(err.message || "Unable to delete project.");
    }
  }

  function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    navigate("/login", { replace: true });
  }

  return (
    <main className="projects-page">
      <header className="projects-header">
        <Link to="/" className="projects-brand">
          Insight<span>OS</span>
        </Link>

        <div className="projects-user">
          <div>
            <strong>{user?.name || "User"}</strong>
            <span>{user?.email || ""}</span>
          </div>

          <button onClick={logout}>Logout</button>
        </div>
      </header>

      <section className="projects-content">
        <div className="projects-intro">
          <div>
            <span className="projects-eyebrow">WORKSPACE</span>
            <h1>Your projects</h1>
            <p>
              Create a project to organize datasets, analytics,
              AI insights, forecasts, anomalies and reports.
            </p>
          </div>

          <button
            className="create-project-button"
            onClick={() => {
              setError("");
              setShowCreate(true);
            }}
          >
            + New project
          </button>
        </div>

        {error && <div className="projects-error">{error}</div>}

        {loading ? (
          <div className="projects-state">
            <span>Loading projects...</span>
          </div>
        ) : projects.length === 0 ? (
          <div className="empty-projects">
            <div className="empty-icon">+</div>
            <h2>Create your first project</h2>
            <p>
              Start by creating a workspace for your business
              analytics.
            </p>

            <button
              className="create-project-button"
              onClick={() => {
                setError("");
                setShowCreate(true);
              }}
            >
              Create project
            </button>
          </div>
        ) : (
          <div className="projects-grid">
            {projects.map((project) => (
              <article className="project-card" key={project.id}>
                <div className="project-card-top">
                  <span className="project-status">
                    {project.status}
                  </span>

                  <div className="project-card-actions">
                    <span className="project-id">
                      #{project.id}
                    </span>

                    <button
                      type="button"
                      className="project-menu-button"
                      aria-label={`Project actions for ${project.name}`}
                      onClick={(event) => {
                        event.stopPropagation();
                        setOpenMenu((current) =>
                          current === project.id
                            ? null
                            : project.id
                        );
                      }}
                    >
                      ⋮
                    </button>

                    {openMenu === project.id && (
                      <div className="project-actions-menu">
                        <button
                          type="button"
                          onClick={() => renameProject(project)}
                        >
                          Rename
                        </button>
                        <button
                          type="button"
                          className="danger"
                          onClick={() => deleteProject(project)}
                        >
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                <h2>{project.name}</h2>

                <p>
                  {project.description ||
                    "No project description provided."}
                </p>

                <div className="project-card-bottom">
                  <span>
                    Created{" "}
                    {project.created_at
                      ? new Date(
                          project.created_at
                        ).toLocaleDateString()
                      : "—"}
                  </span>

                  <button
                    onClick={() =>
                      navigate(`/projects/${project.id}`)
                    }
                  >
                    Open →
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {showCreate && (
        <div
          className="project-modal-overlay"
          onClick={() => setShowCreate(false)}
        >
          <div
            className="project-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              className="modal-close"
              onClick={() => setShowCreate(false)}
            >
              ×
            </button>

            <span className="projects-eyebrow">
              NEW WORKSPACE
            </span>

            <h2>Create project</h2>

            <p>
              Give your analytics workspace a name and optional
              description.
            </p>

            <form onSubmit={createProject}>
              <label>
                Project name
                <input
                  value={name}
                  onChange={(event) =>
                    setName(event.target.value)
                  }
                  placeholder="e.g. Sales Analytics"
                  autoFocus
                />
              </label>

              <label>
                Description
                <textarea
                  value={description}
                  onChange={(event) =>
                    setDescription(event.target.value)
                  }
                  placeholder="What will this project analyze?"
                  rows="4"
                />
              </label>

              <button
                type="submit"
                className="create-project-submit"
              >
                Create project →
              </button>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}
