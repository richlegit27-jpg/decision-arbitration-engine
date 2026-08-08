console.log("[Nova Projects] FILE LOADED");

(function () {
    "use strict";

    function $(id) {
        return document.getElementById(id);
    }

    window.__NOVA_PROJECT_STATE =
        window.__NOVA_PROJECT_STATE || {
            activeProjectId: null,
            projects: [],
            loading: false,
        };


    async function fetchJson(url, options) {
        const response = await fetch(url, options || {});
        const text = await response.text();

        let data = {};

        try {
            data = text ? JSON.parse(text) : {};
        } catch (error) {
            throw new Error(
                "Nova received an invalid response."
            );
        }

        if (!response.ok || data.ok === false) {
            throw new Error(
                data.error ||
                data.message ||
                ("Request failed: " + response.status)
            );
        }

        return data;
    }


    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }


    function setProjectStatus(message) {
        const status = $("desktopProjectStatus");

        if (status) {
            status.textContent = message || "";
        }
    }


    function showProjectsLoading() {
        const container = $("desktopProjectList");

        if (!container) {
            return;
        }

        container.innerHTML = `
            <div class="session-placeholder">
                Loading projects...
            </div>
        `;
    }


    function showProjectsError(message) {
        const container = $("desktopProjectList");

        if (!container) {
            return;
        }

        container.innerHTML = `
            <div class="session-placeholder">
                ${escapeHtml(
                    message ||
                    "Projects could not be loaded."
                )}
            </div>
        `;
    }


    function renderProjects(projects) {
        const container = $("desktopProjectList");

        if (!container) {
            return;
        }

        const safeProjects =
            Array.isArray(projects)
                ? projects
                : [];

        window.__NOVA_PROJECT_STATE.projects =
            safeProjects;

        container.innerHTML = "";

        if (safeProjects.length === 0) {
            container.innerHTML = `
                <div class="session-placeholder">
                    No projects yet. Create a project to start organizing your work.
                </div>
            `;
            return;
        }

        safeProjects.forEach((project) => {
            const projectId = project.id;
            const isActive =
                project.active === true ||
                projectId ===
                    window.__NOVA_PROJECT_STATE.activeProjectId;

            const button =
                document.createElement("button");

            button.type = "button";
            button.className =
                "session-card nova-project-card";

            if (isActive) {
                button.classList.add("active");
            }

            button.dataset.projectId =
                projectId || "";

            const name =
                project.name ||
                project.title ||
                "Untitled Project";

            const description =
                project.description ||
                "No description";

            button.innerHTML = `
                <strong>
                    ${escapeHtml(name)}
                </strong>

                <span>
                    ${escapeHtml(description)}
                </span>

                ${
                    isActive
                        ? `
                            <small class="nova-project-active-label">
                                Active
                            </small>
                        `
                        : ""
                }
            `;

            button.addEventListener(
                "click",
                async () => {
                    if (!projectId) {
                        return;
                    }

                    openProjectWorkspace(project);

                    await activateProject(
                        projectId
                    );
                }
            );

            container.appendChild(button);
        });
    }


    function openProjectWorkspace(project) {
        if (!project) {
            return;
        }

        const title =
            $("desktopProjectTitle");

        const description =
            $("desktopProjectDescription");

        if (title) {
            title.textContent =
                project.name ||
                project.title ||
                "Untitled Project";
        }

        if (description) {
            description.textContent =
                project.description ||
                "No description provided.";
        }

        setProjectStatus(
            project.active
                ? "Active project"
                : "Opening project..."
        );
    }


    function renderProjectTasks(data) {
        const tasksContainer =
            $("desktopProjectTasks");

        if (!tasksContainer) {
            return;
        }

        const tasks =
            data.tasks ||
            data.project?.tasks ||
            [];

        tasksContainer.innerHTML = "";

        if (!Array.isArray(tasks) ||
            tasks.length === 0) {
            tasksContainer.innerHTML = `
                <div class="session-placeholder">
                    No tasks yet.
                </div>
            `;
            return;
        }

        tasks.forEach((task) => {
            const taskElement =
                document.createElement("div");

            taskElement.className =
                "nova-project-task";

            const title =
                task.title ||
                task.name ||
                "Untitled task";

            const status =
                task.status ||
                "";

            taskElement.innerHTML = `
                <strong>
                    ${escapeHtml(title)}
                </strong>

                ${
                    status
                        ? `
                            <span>
                                ${escapeHtml(status)}
                            </span>
                        `
                        : ""
                }
            `;

            tasksContainer.appendChild(
                taskElement
            );
        });
    }


    async function loadProjectWorkspace(
        projectId
    ) {
        if (!projectId) {
            return;
        }

        const tasks =
            $("desktopProjectTasks");

        if (tasks) {
            tasks.innerHTML = `
                <div class="session-placeholder">
                    Loading project...
                </div>
            `;
        }

        try {
            const data =
                await fetchJson(
                    `/api/projects/${projectId}/summary`
                );

            renderProjectTasks(data);

            setProjectStatus(
                "Active project"
            );

        } catch (error) {
            console.error(
                "[Nova Projects] workspace load failed",
                error
            );

            if (tasks) {
                tasks.innerHTML = `
                    <div class="session-placeholder">
                        ${escapeHtml(
                            error.message ||
                            "Project could not be loaded."
                        )}
                    </div>
                `;
            }

            setProjectStatus(
                "Project unavailable"
            );
        }
    }


    async function loadProjects() {
        if (
            window.__NOVA_PROJECT_STATE.loading
        ) {
            return;
        }

        window.__NOVA_PROJECT_STATE.loading =
            true;

        showProjectsLoading();

        try {
            const data =
                await fetchJson(
                    "/api/projects"
                );

            const projects =
                data.projects ||
                data.items ||
                [];

            const activeProject =
                projects.find(
                    (project) =>
                        project.active === true
                );

            if (activeProject?.id) {
                window.__NOVA_PROJECT_STATE.activeProjectId =
                    activeProject.id;
            }

            renderProjects(projects);

            if (activeProject) {
                openProjectWorkspace(
                    activeProject
                );

                await loadProjectWorkspace(
                    activeProject.id
                );
            }

        } catch (error) {
            console.error(
                "[Nova Projects] load failed",
                error
            );

            showProjectsError(
                error.message
            );
        } finally {
            window.__NOVA_PROJECT_STATE.loading =
                false;
        }
    }


    async function activateProject(
        projectId
    ) {
        if (!projectId) {
            return;
        }

        if (
            window.__NOVA_PROJECT_STATE.activeProjectId ===
            projectId
        ) {
            await loadProjectWorkspace(
                projectId
            );

            return;
        }

        setProjectStatus(
            "Activating project..."
        );

        try {
            await fetchJson(
                `/api/projects/${projectId}/activate`,
                {
                    method: "POST",
                }
            );

            window.__NOVA_PROJECT_STATE.activeProjectId =
                projectId;

            renderProjects(
                window.__NOVA_PROJECT_STATE.projects
            );

            await loadProjectWorkspace(
                projectId
            );

        } catch (error) {
            console.error(
                "[Nova Projects] activation failed",
                error
            );

            setProjectStatus(
                error.message ||
                "Project activation failed"
            );
        }
    }


    window.NovaDesktopProjects = {
        loadProjects,
        activateProject,
        loadProjectWorkspace,
        renderProjects,
    };


    document.addEventListener(
        "DOMContentLoaded",
        () => {
            loadProjects();
        }
    );

})();