console.log("[Nova Projects] FILE LOADED");

(function () {    "use strict";

    function $(id) {
        return document.getElementById(id);
    }

    window.__NOVA_PROJECT_STATE = {
        activeProjectId: null,
    };


    async function fetchJson(url, options) {
        const response = await fetch(url, options || {});
        const text = await response.text();

        let data = {};

        try {
            data = JSON.parse(text);
        } catch (error) {
            throw new Error(
                "Non-JSON response from " + url
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


    function renderProjects(projects) {
        const container = $("desktopProjectList");

        if (!container) {
            return;
        }

        container.innerHTML = "";

        if (!Array.isArray(projects) || projects.length === 0) {
            container.innerHTML = `
                <div class="session-placeholder">
                    No projects yet.
                </div>
            `;
            return;
        }


        projects.forEach((project) => {
            const button = document.createElement("button");

            button.type = "button";
            button.className = "session-card";

            button.innerHTML = `
                <strong>
                    ${project.name || project.title || "Untitled Project"}
                </strong>
                <span>
                    ${project.description || "No description"}
                </span>
            `;

            button.addEventListener(
                "click",
                () => {
                    openProjectWorkspace(project);
                    activateProject(project.id);
                }
            );

            container.appendChild(button);
        });
    }


    function openProjectWorkspace(project) {
        const title = $("desktopProjectTitle");
        const description = $("desktopProjectDescription");
        const status = $("desktopProjectStatus");

        if (title) {
            title.textContent =
                project.name || "Untitled Project";
        }

        if (description) {
            description.textContent =
                project.description || "";
        }

        if (status) {
            status.textContent =
                project.active
                    ? "Active project"
                    : "Project workspace ready";
        }

        console.log(
            "[Nova Projects] opened workspace",
            project
        );
    }


    async function loadProjectWorkspace(projectId) {
        try {
            const data = await fetchJson(
                `/api/projects/${projectId}/summary`
            );

            console.log(
                "[Nova Projects] workspace summary",
                data
            );

            const tasks = $("desktopProjectTasks");

            if (tasks) {
                tasks.textContent =
                    JSON.stringify(
                        data,
                        null,
                        2
                    );
            }

        } catch (error) {
            console.error(
                "[Nova Projects] workspace load failed",
                error
            );
        }
    }


    async function loadProjects() {
        try {
            console.log(
                "[Nova Projects] loading"
            );

            const data = await fetchJson(
                "/api/projects"
            );

            console.log(
                "[Nova Projects] response",
                data
            );

            renderProjects(
                data.projects || data.items || []
            );

        } catch (error) {
            console.error(
                "[Nova Projects] load failed",
                error
            );
        }
    }


    async function activateProject(projectId) {
        try {
            await fetchJson(
                `/api/projects/${projectId}/activate`,
                {
                    method: "POST",
                }
            );

            window.__NOVA_PROJECT_STATE.activeProjectId = projectId;

            console.log(
                "[Nova Projects] active project",
                projectId
            );

            await loadProjects();
            await loadProjectWorkspace(projectId);

        } catch (error) {
            console.error(
                "[Nova Projects] activation failed",
                error
            );
        }
    }


    window.NovaDesktopProjects = {
        loadProjects,
        activateProject,
        loadProjectWorkspace,
    };


    document.addEventListener(
        "DOMContentLoaded",
        () => {
            loadProjects();
        }
    );

})();