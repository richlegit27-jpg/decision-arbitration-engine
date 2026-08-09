(function () {
    const PROJECT_LIST_ID = "novaMobileProjectList";
    async function loadMobileProjects() {
        const container =
            document.getElementById(PROJECT_LIST_ID);
        if (!container) {
            return;
        }
        container.innerHTML = "Loading projects...";
        try {
            const response =
                await fetch("/api/projects");
            const data =
                await response.json();
const projects =
    data.projects ||
    data.items ||
    [];
            if (!projects.length) {
                container.innerHTML =
                    "No projects yet.";
                return;
            }
            container.innerHTML = "";
            projects.forEach((project) => {
const button =
    document.createElement("button");
button.type = "button";
button.className =
    "nova-mobile-project-card";
const name =
    project.name ||
    project.title ||
    "Untitled Project";
const description =
    project.description ||
    "No description";
button.innerHTML = `
    <strong>${name}</strong>
    <span>${description}</span>
    <small>Status: ${project.status || "active"}</small>
`;
button.addEventListener(
    "click",
    () => {
        const projectsPanel =
            document.getElementById(
                "nova-mobile-projects-panel"
            );
        const workspace =
            document.getElementById(
                "nova-mobile-project-workspace"
            );
        const title =
            document.getElementById(
                "nova-mobile-project-title"
            );
        const status =
            document.getElementById(
                "nova-mobile-project-status"
            );
        if (projectsPanel) {
            projectsPanel.classList.add("hidden");
        }
        if (workspace) {
            workspace.classList.remove("hidden");
            workspace.style.cssText =
                "display:flex !important; flex-direction:column !important; gap:10px !important; padding:14px !important;";
        }
        if (title) {
            title.textContent =
                project.name || "Project";
        }
        if (status) {
            status.textContent =
                `Status: ${project.status || "active"}`;
        }
    }
);
button.addEventListener(
    "click",
    () => {
        const projectsPanel =
            document.getElementById(
                "nova-mobile-projects-panel"
            );
        const workspace =
            document.getElementById(
                "nova-mobile-project-workspace"
            );
        const title =
            document.getElementById(
                "nova-mobile-project-title"
            );
        const status =
            document.getElementById(
                "nova-mobile-project-status"
            );
        if (projectsPanel) {
            projectsPanel.classList.add("hidden");
        }
        if (workspace) {
            workspace.classList.remove("hidden");
            workspace.style.cssText =
                "display:flex !important; flex-direction:column !important; gap:10px !important; padding:14px !important;";
        }
        if (title) {
            title.textContent =
                project.name || "Project";
        }
        if (status) {
            status.textContent =
                `Status: ${project.status || "active"}`;
        }
    }
);
                container.appendChild(button);
            });
        } catch (error) {
            console.error(
                "[Nova Mobile Projects] load failed",
                error
            );
            container.innerHTML =
                "Unable to load projects.";
        }
    }
window.NovaLoadMobileProjects = loadMobileProjects;
})();
document.addEventListener(
    "DOMContentLoaded",
    function () {
        const button =
            document.getElementById(
                "nova-mobile-projects-toggle"
            );
        const panel =
            document.getElementById(
                "nova-mobile-projects-panel"
            );
        if (!button || !panel) {
            return;
        }
        button.addEventListener(
            "click",
            function () {
                panel.classList.remove("hidden");
                panel.style.cssText =
                    "display:flex !important; position:fixed !important; left:10px !important; right:10px !important; top:90px !important; z-index:999999 !important; flex-direction:column !important; gap:10px !important; padding:14px !important; background:#111827 !important; border:1px solid rgba(255,255,255,.18) !important; border-radius:18px !important;";
                if (window.NovaLoadMobileProjects) {
                    window.NovaLoadMobileProjects();
                }
            }
        );
    }
);
document.addEventListener(
    "click",
    function (event) {
        const notesButton =
            event.target.closest(
                "#nova-mobile-project-notes"
            );
        if (!notesButton) {
            return;
        }
        const projectId =
            new URLSearchParams(
                window.location.search
            ).get("project_id");
        if (!projectId) {
            return;
        }
fetch(
    `/api/projects/${projectId}/notes`
)
            .then((response) =>
                response.json()
            )

.then((notes) => {
const notesPanel =
    document.getElementById(
        "nova-mobile-project-notes-content"
    );

    if (!notesPanel) {
        return;
    }

    notesPanel.innerHTML = `
        <strong>Notes</strong>
        <div class="nova-mobile-project-content">
            ${
                notes.notes && notes.notes.length
                    ? notes.notes.map(note => `
                        <div class="nova-mobile-note-card">
                            <div>
                                ${note.content || "Empty note"}
                            </div>
                        </div>
                    `).join("")
                    : `
                        <div class="nova-mobile-empty-state">
                            No notes yet.
                        </div>
                    `
            }
        </div>
    `;
});
    }
);
