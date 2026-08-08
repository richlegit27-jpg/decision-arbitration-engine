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
    <div class="nova-project-card-header">
        <strong>
            ${escapeHtml(name)}
        </strong>

        ${
            isActive
                ? `
                    <span class="nova-project-status-active">
                        ● Active
                    </span>
                `
                : ""
        }
    </div>

    <div class="nova-project-card-description">
        ${escapeHtml(description)}
    </div>

    <div class="nova-project-card-footer">
        <span>
            ${project.status || "Ready"}
        </span>

        <span>
            ${project.updated_at || "Just now"}
        </span>
    </div>
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
    const status = $("desktopProjectStatus");
    const mission = $("desktopProjectMission");
    const progress = $("desktopProjectProgress");
    const health = $("desktopProjectHealth");
    const focus = $("desktopProjectFocus");
    const nextAction = $("desktopProjectNextAction");
    const recommendation = $("desktopProjectRecommendation");
    const activity = $("desktopProjectRecentActivity");

    if (status) {
        status.textContent = "Workspace ready";
    }

    if (mission) {
        mission.innerHTML = `
            <h3>Mission</h3>
            <p>${project.description || "No mission defined."}</p>
        `;
    }

    if (progress) {
        progress.innerHTML = `
            <h3>Progress</h3>
            <p>0%</p>
        `;
    }

    if (health) {
        health.innerHTML = `
            <h3>Health</h3>
            <p>🟢 Healthy</p>
        `;
    }

    if (focus) {
        focus.innerHTML = `
            <h3>Current Focus</h3>
            <p>No active work.</p>
        `;
    }

    if (nextAction) {
        nextAction.innerHTML = `
            <h3>Next Action</h3>
            <p>Create your first task.</p>
        `;
    }

    if (recommendation) {
        recommendation.innerHTML = `
            <h3>AI Recommendation</h3>
            <p>Start organizing this project.</p>
        `;
    }

    if (activity) {
        activity.innerHTML = `
            <h3>Recent Activity</h3>
            <p>Project opened.</p>
        `;
    }
}

async function loadProjectIntelligence(projectId) {
    try {
        const data = await fetchJson(
            `/api/projects/${projectId}/intelligence`
        );

        const brain =
            data.intelligence || {};

        const todayPlan =
            $("desktopTodayPlan");

        if (todayPlan) {
            const plan =
                Array.isArray(brain.today_plan)
                    ? brain.today_plan
                    : [];

            todayPlan.innerHTML =
                plan.length
                    ? plan
                        .map(
                            (step) =>
                                `<li>${escapeHtml(step)}</li>`
                        )
                        .join("")
                    : `
                        <li>No plan available.</li>
                    `;
        }

        const mission =
            $("desktopProjectMission");

        if (mission) {
            mission.innerHTML = `
                <h3>Mission</h3>
                <p>
                    ${escapeHtml(
                        brain.mission ||
                        "No mission yet."
                    )}
                </p>
            `;
        }

        const progress =
            $("desktopProjectProgress");

        if (progress) {
            progress.innerHTML = `
                <h3>Progress</h3>
                <p>
                    ${Number(brain.progress || 0)}%
                </p>
            `;
        }

        const health =
            $("desktopProjectHealth");

        if (health) {
            health.innerHTML = `
                <h3>Health</h3>
                <p>
                    ${Number(brain.health || 0)}%
                </p>
            `;
        }

        const focus =
            $("desktopProjectFocus");

        if (focus) {
            focus.innerHTML = `
                <h3>Current Focus</h3>
                <p>
                    ${escapeHtml(
                        brain.current_focus ||
                        "No active work."
                    )}
                </p>
            `;
        }

        const nextAction =
            $("desktopProjectNextAction");

        if (nextAction) {
            nextAction.innerHTML = `
                <h3>Next Action</h3>
                <p>
                    ${escapeHtml(
                        brain.next_action ||
                        "Nothing planned."
                    )}
                </p>
            `;
        }

        const recommendation =
            $("desktopProjectRecommendation");

        if (recommendation) {
            recommendation.innerHTML = `
                <h3>AI Recommendation</h3>
                <p>
                    ${escapeHtml(
                        brain.recommendation ||
                        "No recommendation."
                    )}
                </p>
            `;
        }

        const resume =
            $("desktopProjectResume");

        if (resume) {
            resume.innerHTML = `
                <h3>📋 Resume Summary</h3>

                <p>
                    ${escapeHtml(
                        brain.resume_summary ||
                        "Ready to continue."
                    )}
                </p>

                <p>
                    <strong>Estimated time:</strong>
                    ${escapeHtml(
                        brain.estimated_time ||
                        "Unknown"
                    )}
                </p>
            `;
        }

        const activity =
            $("desktopProjectRecentActivity");

        if (activity) {
            const recentActivity =
                Array.isArray(brain.recent_activity)
                    ? brain.recent_activity
                    : [];

            activity.innerHTML = `
                <h3>Recent Activity</h3>

                ${
                    recentActivity.length
                        ? recentActivity
                            .slice(0, 5)
                            .map(
                                (item) => `
                                    <p>
                                        ${escapeHtml(
                                            item.message ||
                                            "Project activity"
                                        )}
                                    </p>
                                `
                            )
                            .join("")
                        : `
                            <p>No activity yet.</p>
                        `
                }
            `;
        }

    } catch (error) {
        console.error(
            "[Nova Projects] intelligence failed",
            error
        );

        setProjectStatus(
            error.message ||
            "Project intelligence unavailable"
        );
    }
}

    function renderProjectOverview(data) {
        const project =
            data.project ||
            data.summary?.project ||
            {};

        const summary =
            data.summary ||
            {};

        const container =
            $("desktopProjectOverview");

        if (!container) {
            return;
        }

        const tasks =
            data.tasks ||
            project.tasks ||
            [];

        const taskCount =
            summary.task_count ??
            (Array.isArray(tasks) ? tasks.length : 0);

        const artifactCount =
            summary.artifact_count ??
            0;

        const fileCount =
            summary.file_count ??
            0;

        const chatCount =
            summary.chat_count ??
            summary.session_count ??
            0;

        const name =
            project.name ||
            project.title ||
            "Untitled Project";

        const description =
            project.description ||
            "No description provided.";

        const active =
            project.active === true ||
            project.id ===
                window.__NOVA_PROJECT_STATE.activeProjectId;

        container.innerHTML = `
            <div class="nova-project-overview-card">
                <div class="nova-project-overview-header">
                    <div>
                        <strong>
                            ${escapeHtml(name)}
                        </strong>

                        <p>
                            ${escapeHtml(description)}
                        </p>
                    </div>

                    <span class="nova-project-status-badge">
                        ${active ? "Active" : "Inactive"}
                    </span>
                </div>

                <div class="nova-project-stats">
                    <div>
                        <strong>${taskCount}</strong>
                        <span>Tasks</span>
                    </div>

                    <div>
                        <strong>${artifactCount}</strong>
                        <span>Artifacts</span>
                    </div>

                    <div>
                        <strong>${fileCount}</strong>
                        <span>Files</span>
                    </div>

                    <div>
                        <strong>${chatCount}</strong>
                        <span>Chats</span>
                    </div>
                </div>
            </div>
        `;
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

            renderProjectOverview(data);
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

const continueButton =
    $("desktopContinueProject");

if (continueButton) {
    continueButton.addEventListener(
        "click",
        async () => {
            await continueProject(
                window.__NOVA_PROJECT_STATE
                    .activeProjectId
            );
        }
    );
}

    document.addEventListener(
        "DOMContentLoaded",
        () => {
            loadProjects();
        }
    );

async function continueProject(projectId) {
    if (!projectId) {
        return;
    }

    setProjectStatus(
        "Loading workspace..."
    );

    await loadProjectWorkspace(
        projectId
    );

    setProjectStatus(
        "Analyzing project..."
    );

    await loadProjectIntelligence(
        projectId
    );


    const resume =
        $("desktopProjectResume");


    const nextAction =
        $("desktopProjectNextAction");

    if (nextAction) {
        nextAction.scrollIntoView({
            behavior: "smooth",
            block: "center",
        });
    }

    setProjectStatus(
        "Ready to continue"
    );
}

})();