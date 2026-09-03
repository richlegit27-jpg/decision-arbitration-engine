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
            const projectId =
                project.id;

const isActive =
    projectId ===
    window.__NOVA_PROJECT_STATE.activeProjectId;

            const name =
                project.name ||
                project.title ||
                "Untitled Project";

            const description =
                project.description ||
                "No description";

            const card =
                document.createElement("div");

            card.className =
                "nova-project-card";

            if (isActive) {
                card.classList.add("active");
            }

            card.dataset.projectId =
                projectId || "";

            card.innerHTML = `
                <div class="nova-project-card-main">
                    <button
                        type="button"
                        class="nova-project-card-open"
                    >
                        <div class="nova-project-card-header">
                            <strong>
                                ${escapeHtml(name)}
                            </strong>

                            ${
                                isActive
                                    ? `<span class="nova-project-active-badge">Active</span>`
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
                    </button>

                    <button
                        type="button"
                        class="nova-project-delete-button"
                        title="Delete project"
                    >
                        Delete
                    </button>
                </div>
            `;

            const openButton =
                card.querySelector(
                    ".nova-project-card-open"
                );

            const deleteButton =
                card.querySelector(
                    ".nova-project-delete-button"
                );

            if (openButton) {
                openButton.addEventListener(
                    "click",
                    async () => {
                        if (!projectId) {
                            return;
                        }

                        openProjectWorkspace(
                            project
                        );

                        await activateProject(
                            projectId
                        );

                        await loadProjectWorkspace(
                            projectId
                        );
                    }
                );
            }

            if (deleteButton) {
                deleteButton.addEventListener(
                    "click",
                    async (event) => {
                        event.stopPropagation();

                        if (!projectId) {
                            return;
                        }

                        const confirmed =
                            window.confirm(
                                `Delete project "${name}"?\n\nThis cannot be undone.`
                            );

                        if (!confirmed) {
                            return;
                        }

                        deleteButton.disabled = true;

                        try {
                            const response =
                                await fetch(
                                    `/api/projects/${encodeURIComponent(projectId)}`,
                                    {
                                        method: "DELETE",
                                    }
                                );

                            const text =
                                await response.text();

                            let data = {};

                            try {
                                data = text
                                    ? JSON.parse(text)
                                    : {};
                            } catch (parseError) {
                                throw new Error(
                                    "Nova received an invalid delete response."
                                );
                            }

                            if (
                                !response.ok ||
                                data.ok === false
                            ) {
                                throw new Error(
                                    data.error ||
                                    data.message ||
                                    "Project deletion failed"
                                );
                            }

                            const wasActive =
                                window.__NOVA_PROJECT_STATE
                                    .activeProjectId ===
                                projectId;

                            window.__NOVA_PROJECT_STATE.projects =
                                window.__NOVA_PROJECT_STATE.projects.filter(
                                    (item) =>
                                        item.id !== projectId
                                );

                            if (wasActive) {
                                window.__NOVA_PROJECT_STATE
                                    .activeProjectId = null;

                                const workspace =
                                    $("desktopProjectWorkspace");

                                if (workspace) {
                                    workspace.style.display = "";

                                    const title =
                                        $("desktopProjectTitle");

                                    const description =
                                        $("desktopProjectDescription");

                                    if (title) {
                                        title.textContent =
                                            "No project selected";
                                    }

                                    if (description) {
                                        description.textContent =
                                            "Select a project to open workspace.";
                                    }
                                }
                            }

                            renderProjects(
                                window.__NOVA_PROJECT_STATE.projects
                            );

                            setProjectStatus(
                                "Project deleted"
                            );

                            console.log(
                                "[NOVA PROJECTS] deleted",
                                projectId
                            );

                            try {
                                await loadProjects();
                            } catch (reloadError) {
                                console.error(
                                    "[NOVA PROJECTS] reload after delete failed",
                                    reloadError
                                );
                            }

                        } catch (error) {
                            console.error(
                                "[NOVA PROJECTS] delete failed",
                                error
                            );

                            window.alert(
                                error.message ||
                                "Project deletion failed"
                            );

                            deleteButton.disabled = false;
                        }
                    }
                );
            }

            container.appendChild(
                card
            );
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
            <p>ðŸŸ¢ Healthy</p>
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

}

async function loadProjectIntelligence(projectId) {
    try {
        const data = await fetchJson(
            `/api/projects/${projectId}/brain`
        );

        const brain =
            data.brain || {};

        const todayPlan =
            $("desktopTodayPlan");

        if (todayPlan) {
            const plan =
                Array.isArray(brain.next_actions)
                    ? brain.next_actions
                    : [];

            todayPlan.innerHTML =
                plan.length
                    ? plan
                        .map(
                            (item) => `
                                <li>
                                    ${escapeHtml(
                                        item.action ||
                                        item.title ||
                                        "Project action"
                                    )}
                                </li>
                            `
                        )
                        .join("")
                    : `
                        <li>No actions planned.</li>
                    `;
        }

        const mission =
            $("desktopProjectMission");

        if (mission) {
            mission.innerHTML = `
                <h3>Mission</h3>
                <p>
                    ${escapeHtml(
                        brain.goal ||
                        brain.name ||
                        "No mission defined yet."
                    )}
                </p>
            `;
        }

        const progress =
            $("desktopProjectProgress");

        if (progress) {
            const tasksOpen =
                Number(brain.tasks_open || 0);

            progress.innerHTML = `
                <h3>Open Tasks</h3>
                <p>
                    ${tasksOpen}
                </p>
            `;
        }

        const health =
            $("desktopProjectHealth");

        if (health) {
            const blockers =
                Array.isArray(brain.blockers)
                    ? brain.blockers
                    : [];

            health.innerHTML = `
                <h3>Project Health</h3>
                <p>
                    ${
                        blockers.length
                            ? `${blockers.length} blocker(s)`
                            : "Healthy"
                    }
                </p>
            `;
        }

        const focus =
            $("desktopProjectFocus");

        if (focus) {
            const actions =
                Array.isArray(brain.next_actions)
                    ? brain.next_actions
                    : [];

            const firstAction =
                actions.length
                    ? actions[0]
                    : null;

            focus.innerHTML = `
                <h3>Current Focus</h3>
                <p>
                    ${escapeHtml(
                        firstAction?.action ||
                        brain.goal ||
                        "No active work."
                    )}
                </p>
            `;
        }

        const nextAction =
            $("desktopProjectNextAction");

        if (nextAction) {
            const actions =
                Array.isArray(brain.next_actions)
                    ? brain.next_actions
                    : [];

            const firstAction =
                actions.length
                    ? actions[0]
                    : null;

            nextAction.innerHTML = `
                <h3>Next Action</h3>
                <p>
                    ${escapeHtml(
                        firstAction?.action ||
                        "Nothing planned."
                    )}
                </p>
            `;
        }

        const recommendation =
            $("desktopProjectRecommendation");

        if (recommendation) {
            const blockers =
                Array.isArray(brain.blockers)
                    ? brain.blockers
                    : [];

            const actions =
                Array.isArray(brain.next_actions)
                    ? brain.next_actions
                    : [];

            let recommendationText =
                "No recommendation available.";

            if (blockers.length) {
                recommendationText =
                    "Resolve the current project blockers before continuing.";
            } else if (actions.length) {
                recommendationText =
                    `Continue with: ${
                        actions[0].action ||
                        "the next planned action"
                    }`;
            } else if (Number(brain.tasks_open || 0) > 0) {
                recommendationText =
                    "Review the open project tasks and choose the next task.";
            }

            recommendation.innerHTML = `
                <h3>AI Recommendation</h3>
                <p>
                    ${escapeHtml(
                        recommendationText
                    )}
                </p>
            `;
        }

        const resume =
            $("desktopProjectResume");

        if (resume) {
            const decisions =
                Array.isArray(brain.decisions)
                    ? brain.decisions
                    : [];

            resume.innerHTML = `
                <h3>Resume Summary</h3>

                <p>
                    ${escapeHtml(
                        brain.goal ||
                        brain.name ||
                        "Ready to continue."
                    )}
                </p>

                <p>
                    <strong>Open tasks:</strong>
                    ${Number(brain.tasks_open || 0)}
                </p>

                <p>
                    <strong>Decisions:</strong>
                    ${decisions.length}
                </p>
            `;
        }

        const activity =
            $("desktopProjectRecentActivity");

        if (activity) {
            const decisions =
                Array.isArray(brain.decisions)
                    ? brain.decisions
                    : [];

            const actions =
                Array.isArray(brain.next_actions)
                    ? brain.next_actions
                    : [];

            const recentActivity = [
                ...actions.map(
                    (item) => ({
                        type: "Next action",
                        text:
                            item.action ||
                            "Project action"
                    })
                ),
                ...decisions.map(
                    (item) => ({
                        type: "Decision",
                        text:
                            item.decision ||
                            "Project decision"
                    })
                )
            ];

            activity.innerHTML = `
                <h3>Recent Activity</h3>

                ${
                    recentActivity.length
                        ? recentActivity
                            .slice(0, 5)
                            .map(
                                (item) => `
                                    <p>
                                        <strong>
                                            ${escapeHtml(
                                                item.type
                                            )}
                                        </strong>
                                        — ${escapeHtml(
                                            item.text
                                        )}
                                    </p>
                                `
                            )
                            .join("")
                        : `
                            <p>No recent activity.</p>
                        `
                }
            `;
        }

        return brain;

    } catch (error) {
        console.error(
            "[Nova Projects] brain load failed",
            error
        );

        setProjectStatus(
            error.message ||
            "Project Brain unavailable"
        );

        return null;
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

const titleElement =
    $("desktopProjectTitle");

if (titleElement) {
    titleElement.textContent = name;
}

const descriptionElement =
    $("desktopProjectDescription");

if (descriptionElement) {
    descriptionElement.textContent = description;
}

const active =
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
        $("desktopProjectTaskList");

    if (!tasksContainer) {
        return;
    }

    const projectId =
        window.__NOVA_PROJECT_STATE?.activeProjectId;

    const tasks =
        Array.isArray(data?.tasks)
            ? data.tasks
            : Array.isArray(data?.project?.tasks)
                ? data.project.tasks
                : [];

tasksContainer.innerHTML = `
    <section
        id="desktopProjectExecutionPanel"
        class="nova-project-execution-panel"
    >
        <div class="nova-project-execution-header">
            <div>
                <h3>Project Execution</h3>

                <p>
                    Run the complete project workflow or
                    continue from the current execution state.
                </p>
            </div>

            <div
                id="desktopProjectExecutionStatus"
                class="nova-project-execution-status"
            >
                Ready
            </div>
        </div>

        <div class="nova-project-execution-actions">
            <button
                id="desktopProjectRunAllButton"
                type="button"
            >
                Run All
            </button>

            <button
                id="desktopProjectContinueButton"
                type="button"
            >
                Continue
            </button>
        </div>
    </section>

    <section
        class="nova-project-task-panel"
    >
        <div class="nova-project-task-panel-header">
            <h3>Project Tasks</h3>
        </div>

        <div id="novaProjectTaskItems"></div>
    </section>
`;

    const items =
        $("novaProjectTaskItems");

    if (!items) {
        return;
    }

const runAllButton =
    $("desktopProjectRunAllButton");

if (runAllButton) {
    runAllButton.addEventListener(
        "click",
        async () => {
            const currentProjectId =
                window.__NOVA_PROJECT_STATE
                    ?.activeProjectId;

            if (!currentProjectId) {
                setProjectStatus(
                    "No active project"
                );
                return;
            }

            runAllButton.disabled = true;

            try {
                await runAllProject(
                    currentProjectId
                );
            } finally {
                runAllButton.disabled = false;
            }
        }
    );
}


const continueButton =
    $("desktopProjectContinueButton");

if (continueButton) {
    continueButton.addEventListener(
        "click",
        async () => {
            const currentProjectId =
                window.__NOVA_PROJECT_STATE
                    ?.activeProjectId;

            if (!currentProjectId) {
                setProjectStatus(
                    "No active project"
                );
                return;
            }

            continueButton.disabled = true;

            try {
                await continueProject(
                    currentProjectId
                );
            } finally {
                continueButton.disabled = false;
            }
        }
    );
}

    if (!tasks.length) {
        items.innerHTML = `
            <div class="session-placeholder">
                No tasks yet. Add the first task for this project.
            </div>
        `;
    } else {
        tasks.forEach((task) => {
            const row =
                document.createElement("div");

            row.className =
                "nova-project-task";

            row.dataset.taskId =
                task.id || "";

            const title =
                task.title ||
                task.name ||
                "Untitled task";

            const status =
                String(
                    task.status || "open"
                ).toLowerCase();

            const priority =
                String(
                    task.priority || "medium"
                ).toLowerCase();

            row.innerHTML = `
                <div class="nova-project-task-main">
                    <strong>
                        ${escapeHtml(title)}
                    </strong>

                    <div class="nova-project-task-meta">
                        <span>
                            ${escapeHtml(status)}
                        </span>

                        <span>
                            ${escapeHtml(priority)}
                        </span>
                    </div>
                </div>

                <div class="nova-project-task-actions">
                    <select
                        class="nova-project-task-status"
                        data-task-status
                    >
                        <option value="open">Open</option>
                        <option value="running">Running</option>
                        <option value="completed">Completed</option>
                        <option value="blocked">Blocked</option>
                    </select>

                    <button
                        type="button"
                        data-task-delete
                    >
                        Delete
                    </button>
                </div>
            `;

            const statusSelect =
                row.querySelector(
                    "[data-task-status]"
                );

            if (statusSelect) {
                statusSelect.value =
                    [
                        "open",
                        "running",
                        "completed",
                        "blocked",
                    ].includes(status)
                        ? status
                        : "open";

                statusSelect.addEventListener(
                    "change",
                    async () => {
                        if (!projectId || !task.id) {
                            return;
                        }

                        try {
                            statusSelect.disabled =
                                true;

                            setProjectStatus(
                                "Updating task..."
                            );

                            await fetchJson(
                                `/api/projects/${projectId}/tasks/${task.id}`,
                                {
                                    method: "PATCH",
                                    headers: {
                                        "Content-Type":
                                            "application/json",
                                    },
                                    body:
                                        JSON.stringify({
                                            status:
                                                statusSelect.value,
                                        }),
                                }
                            );

                            await loadProjectWorkspace(
                                projectId
                            );

                            await loadProjectIntelligence(
                                projectId
                            );

                            setProjectStatus(
                                "Task updated"
                            );

                        } catch (error) {
                            console.error(
                                "[Nova Projects] task update failed",
                                error
                            );

                            statusSelect.disabled =
                                false;

                            setProjectStatus(
                                error.message ||
                                "Task update failed"
                            );
                        }
                    }
                );
            }

            const deleteButton =
                row.querySelector(
                    "[data-task-delete]"
                );




            if (deleteButton) {
                deleteButton.addEventListener(
                    "click",
                    async () => {
                        if (!projectId || !task.id) {
                            return;
                        }

                        if (
                            !confirm(
                                "Delete this task?"
                            )
                        ) {
                            return;
                        }

                        try {
                            deleteButton.disabled =
                                true;

                            setProjectStatus(
                                "Deleting task..."
                            );

                            await fetchJson(
                                `/api/projects/${projectId}/tasks/${task.id}`,
                                {
                                    method: "DELETE",
                                }
                            );

                            await loadProjectWorkspace(
                                projectId
                            );

                            await loadProjectIntelligence(
                                projectId
                            );

                            setProjectStatus(
                                "Task deleted"
                            );

                        } catch (error) {
                            console.error(
                                "[Nova Projects] task delete failed",
                                error
                            );

                            deleteButton.disabled =
                                false;

                            setProjectStatus(
                                error.message ||
                                "Task delete failed"
                            );
                        }
                    }
                );
            }

            items.appendChild(row);
        });
    }

    const addButton =
        $("desktopProjectAddTaskButton");

    if (
        addButton &&
        !addButton.dataset.bound
    ) {
        addButton.dataset.bound =
            "true";

        addButton.addEventListener(
            "click",
            async () => {
                const currentProjectId =
                    window.__NOVA_PROJECT_STATE
                        ?.activeProjectId;

                if (!currentProjectId) {
                    setProjectStatus(
                        "No active project"
                    );
                    return;
                }

                const title =
                    prompt(
                        "Task name:"
                    );

                if (
                    !title ||
                    !title.trim()
                ) {
                    return;
                }

                try {
                    addButton.disabled =
                        true;

                    setProjectStatus(
                        "Creating task..."
                    );

                    await fetchJson(
                        `/api/projects/${currentProjectId}/tasks`,
                        {
                            method: "POST",
                            headers: {
                                "Content-Type":
                                    "application/json",
                            },
                            body:
                                JSON.stringify({
                                    title:
                                        title.trim(),
                                    priority:
                                        "medium",
                                }),
                        }
                    );

                    await loadProjectWorkspace(
                        currentProjectId
                    );

                    await loadProjectIntelligence(
                        currentProjectId
                    );

                    setProjectStatus(
                        "Task created"
                    );

                } catch (error) {
                    console.error(
                        "[Nova Projects] task creation failed",
                        error
                    );

                    setProjectStatus(
                        error.message ||
                        "Task creation failed"
                    );

                } finally {
                    addButton.disabled =
                        false;
                }
            }
        );
    }
}

function setProjectExecutionStatus(
    message,
    state = "ready"
) {
    const status =
        document.getElementById(
            "desktopProjectExecutionStatus"
        );

    if (!status) {
        return;
    }

    status.textContent =
        message || "Ready";

    status.dataset.state =
        state;
}

async function loadProjectWorkspace(
    projectId
) {
    if (!projectId) {
        return;
    }

    const tasksContainer =
        $("desktopProjectTaskList");

    if (tasksContainer) {
        tasksContainer.innerHTML = `
            <div class="session-placeholder">
                Loading project...
            </div>
        `;
    }

    try {
        const summary =
            await fetchJson(
                `/api/projects/${projectId}/summary`
            );

        let projectData = null;

        try {
            projectData =
                await fetchJson(
                    `/api/projects/${projectId}`
                );
        } catch (projectError) {
            console.warn(
                "[Nova Projects] direct project endpoint unavailable",
                projectError
            );
        }

        const project =
            projectData?.project ||
            summary?.project ||
            summary?.summary?.project ||
            {};

        const data = {
            ...summary,
            project: project,
            tasks:
                project.tasks ||
                summary?.tasks ||
                []
        };

        if (!project.id) {
            throw new Error(
                "Project not found"
            );
        }

        renderProjectTasks(
            data
        );

        const title =
            $("desktopProjectTitle");

        if (title) {
            title.textContent =
                project.name ||
                project.title ||
                "Untitled Project";
        }

        const description =
            $("desktopProjectDescription");

        if (description) {
            description.textContent =
                project.description ||
                "";
        }

        window.__NOVA_PROJECT_STATE =
            window.__NOVA_PROJECT_STATE || {};

        window.__NOVA_PROJECT_STATE.activeProjectId =
            projectId;

const executionPanel =
    document.getElementById(
        "desktopProjectExecutionPanel"
    );

if (!executionPanel) {
    const tasksContainer =
        $("desktopProjectTaskList");

    const newExecutionPanel =
        document.createElement("div");

    newExecutionPanel.id =
        "desktopProjectExecutionPanel";

    newExecutionPanel.className =
        "nova-project-execution-panel";

    newExecutionPanel.innerHTML = `
        <div class="nova-project-execution-header">
            <div>
                <h3>Execution Center</h3>

                <p>
                    Run and monitor project work.
                </p>
            </div>

            <div
                id="desktopProjectExecutionState"
                class="nova-project-execution-state"
            >
                Ready
            </div>
        </div>

        <div
            id="desktopProjectExecutionMessage"
            class="nova-project-execution-message"
        >
            Select an execution action to begin.
        </div>

        <div class="nova-project-execution-actions">
            <button
                id="desktopProjectRunAllButton"
                type="button"
            >
                Run All
            </button>

            <button
                id="desktopProjectContinueButton"
                type="button"
            >
                Continue
            </button>
        </div>
    `;

    if (
        tasksContainer &&
        tasksContainer.parentNode
    ) {
        tasksContainer.parentNode.insertBefore(
            newExecutionPanel,
            tasksContainer
        );
    }
}

        const workspace =
            document.querySelector(
                ".project-workspace-card"
            );

        if (
            workspace &&
            !document.getElementById(
                "desktopProjectFiles"
            )
        ) {
            const filesPanel =
                document.createElement(
                    "div"
                );

            filesPanel.id =
                "desktopProjectFiles";

            filesPanel.className =
                "project-panel-card";

            filesPanel.innerHTML = `
                <div class="nova-project-files-header">
                    <h3>Project Files</h3>

                    <button
                        id="desktopProjectUploadButton"
                        type="button"
                    >
                        Upload File
                    </button>
                </div>

                <input
                    id="desktopProjectFileInput"
                    type="file"
                    hidden
                />

                <div id="desktopProjectFileList">
                    <p>No files yet.</p>
                </div>
            `;

            const notes =
                document.getElementById(
                    "desktopProjectNotes"
                );

            if (notes) {
                notes.before(
                    filesPanel
                );
            } else {
                workspace.appendChild(
                    filesPanel
                );
            }
        }

        const projectUploadButton =
            document.getElementById(
                "desktopProjectUploadButton"
            );

        const projectFileInput =
            document.getElementById(
                "desktopProjectFileInput"
            );

        if (
            projectUploadButton &&
            projectFileInput &&
            !projectUploadButton.dataset.bound
        ) {
            projectUploadButton.dataset.bound =
                "true";

            projectUploadButton.addEventListener(
                "click",
                () => {
                    projectFileInput.click();
                }
            );

            projectFileInput.addEventListener(
                "change",
                async () => {
                    const file =
                        projectFileInput.files?.[0];

                    const currentProjectId =
                        window.__NOVA_PROJECT_STATE
                            ?.activeProjectId;

                    if (
                        !file ||
                        !currentProjectId
                    ) {
                        return;
                    }

                    const formData =
                        new FormData();

                    formData.append(
                        "file",
                        file
                    );

                    formData.append(
                        "project_id",
                        currentProjectId
                    );

                    try {
                        setProjectStatus(
                            "Uploading file..."
                        );

                        const response =
                            await fetch(
                                "/api/upload",
                                {
                                    method: "POST",
                                    body: formData
                                }
                            );

                        const uploadData =
                            await response.json();

                        if (
                            !response.ok ||
                            !uploadData.ok
                        ) {
                            throw new Error(
                                uploadData.error ||
                                "Upload failed"
                            );
                        }

                        await loadProjectFiles(
                            currentProjectId
                        );

                        await loadProjectIntelligence(
                            currentProjectId
                        );

                        setProjectStatus(
                            "File uploaded"
                        );

                    } catch (error) {
                        console.error(
                            "[Nova Projects] file upload failed",
                            error
                        );

                        setProjectStatus(
                            error.message ||
                            "File upload failed"
                        );

                    } finally {
                        projectFileInput.value =
                            "";
                    }
                }
            );
        }

        await loadProjectFiles(
            projectId
        );

        await loadProjectIntelligence(
            projectId
        );

        setProjectStatus(
            "Active project"
        );

        return data;

    } catch (error) {
        console.error(
            "[Nova Projects] workspace load failed",
            error
        );

        if (tasksContainer) {


            tasksContainer.innerHTML = `
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

        return null;
    }
}

async function deleteProjectFile(
    projectId,
    fileId
) {
    if (
        !projectId ||
        !fileId
    ) {
        return;
    }

    try {
        setProjectStatus(
            "Deleting file..."
        );

        const response =
            await fetch(
                `/api/projects/${projectId}/files/${fileId}`,
                {
                    method: "DELETE",
                }
            );

        const data =
            await response.json();

        if (
            !response.ok ||
            !data.ok
        ) {
            throw new Error(
                data.error ||
                "Delete failed"
            );
        }

        await loadProjectFiles(
            projectId
        );

        setProjectStatus(
            "File deleted"
        );

    } catch (error) {
        console.error(
            "[Nova Projects] file delete failed",
            error
        );

        setProjectStatus(
            error.message ||
            "File delete failed"
        );
    }
}

async function loadProjectFiles(projectId) {
    if (!projectId) {
        return;
    }

    const container =
        $("desktopProjectFileList");

    if (!container) {
        return;
    }

    container.innerHTML = `
        <p>Loading files...</p>
    `;

    try {
        const data = await fetchJson(
            `/api/projects/${projectId}/files`
        );

        const files =
            Array.isArray(data.files)
                ? data.files
                : [];

        if (!files.length) {
            container.innerHTML = `
                <p>No files yet.</p>
            `;
            return;
        }


    container.innerHTML = files
        .map(
            (file) => {
                const name =
                    file.filename ||
                    file.name ||
                    "Untitled file";

                    const size =
                        Number(file.size || 0);

                    return `
                        <div
                            class="nova-project-file"
                            data-project-file-id="${escapeHtml(
                                file.id || ""
                            )}"
                        >
                            <div class="nova-project-file-info">

<a
    href="/api/projects/${projectId}/files/${file.id}/download"
    target="_blank"
    rel="noopener"
>
    ${escapeHtml(name)}
</a>

                                <span>
                                    ${size} bytes
                                </span>
                            </div>

                            <button
                                type="button"
                                class="nova-project-file-delete"
                                data-project-file-delete="${escapeHtml(
                                    file.id || ""
                                )}"
                            >
                                Delete
                            </button>
                        </div>
                    `;
                }
            )
            .join("");

container
    .querySelectorAll(
        "[data-project-file-delete]"
    )
    .forEach(
        (button) => {
            button.addEventListener(
                "click",
                async () => {
                    const fileId =
                        button.dataset
                            .projectFileDelete;

                    await deleteProjectFile(
                        projectId,
                        fileId
                    );
                }
            );
        }
    );

    } catch (error) {
        console.error(
            "[Nova Projects] file load failed",
            error
        );

        container.innerHTML = `
            <p>
                ${escapeHtml(
                    error.message ||
                    "Could not load files."
                )}
            </p>
        `;
    }
}

async function loadProjectNotes(projectId) {
    if (!projectId) {
        return;
    }

    const container =
        $("desktopProjectNoteList");

    if (!container) {
        return;
    }

    container.innerHTML = `
        <p>Loading notes...</p>
    `;

    try {
        const data = await fetchJson(
            `/api/projects/${projectId}/notes`
        );

        const notes =
            Array.isArray(data.notes)
                ? data.notes
                : [];

        if (!notes.length) {
            container.innerHTML = `
                <p>No notes yet.</p>
            `;
            return;
        }

        container.innerHTML = notes
            .map(
                (note) => `
                    <div
                        class="nova-project-note"
                        data-project-note-id="${escapeHtml(
                            note.id || ""
                        )}"
                    >
                        <strong>
                            ${escapeHtml(
                                note.title ||
                                "Untitled Note"
                            )}
                        </strong>

                        <p>
                            ${escapeHtml(
                                note.content || ""
                            )}
                        </p>

                        <button
                            type="button"
                            data-project-note-delete="${escapeHtml(
                                note.id || ""
                            )}"
                        >
                            Delete
                        </button>
                    </div>
                `
            )
            .join("");

container
    .querySelectorAll("[data-project-note-delete]")
    .forEach((button) => {
        button.addEventListener(
            "click",
            async () => {
                const noteId =
                    button.dataset.projectNoteDelete;

                const projectId =
                    window.__NOVA_PROJECT_STATE
                        .activeProjectId;

                if (!projectId || !noteId) {
                    return;
                }

                await fetch(
                    `/api/projects/${projectId}/notes/${noteId}`,
                    {
                        method: "DELETE",
                    }
                );

                await loadProjectNotes(
                    projectId
                );
            }
        );
    });

    } catch (error) {
        console.error(
            "[Nova Projects] notes load failed",
            error
        );

        container.innerHTML = `
            <p>Could not load notes.</p>
        `;
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

    await loadProjectNotes(
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

const newProjectButton =
    $("newProjectBtn");

const newProjectModal =
    $("newProjectModal");

const newProjectName =
    $("newProjectName");

const newProjectDescription =
    $("newProjectDescription");

const createNewProjectButton =
    $("createNewProject");

const cancelNewProjectButton =
    $("cancelNewProject");


if (newProjectButton) {
    newProjectButton.addEventListener(
        "click",
        () => {
            console.log(
                "[NOVA PROJECTS] New Project clicked"
            );

            if (!newProjectModal) {
                console.error(
                    "[NOVA PROJECTS] newProjectModal not found"
                );
                return;
            }

            newProjectModal.hidden = false;

            if (newProjectName) {
                newProjectName.value = "";
                newProjectName.focus();
            }

            if (newProjectDescription) {
                newProjectDescription.value = "";
            }
        }
    );
}


if (cancelNewProjectButton) {
    cancelNewProjectButton.addEventListener(
        "click",
        () => {
            if (newProjectModal) {
                newProjectModal.hidden = true;
            }
        }
    );
}


if (createNewProjectButton) {
    createNewProjectButton.addEventListener(
        "click",
        async () => {
            const name =
                newProjectName?.value.trim();

            if (!name) {
                if (newProjectName) {
                    newProjectName.focus();
                }
                return;
            }

            const description =
                newProjectDescription?.value.trim() ||
                "";

            createNewProjectButton.disabled = true;

            try {
                const response =
                    await fetch(
                        "/api/projects/new",
                        {
                            method: "POST",
                            headers: {
                                "Content-Type":
                                    "application/json",
                            },
                            body: JSON.stringify({
                                name,
                                description,
                            }),
                        }
                    );

                const data =
                    await response.json();

                console.log(
                    "[NOVA PROJECTS] create response",
                    data
                );

                if (
                    !response.ok ||
                    !data.ok
                ) {
                    throw new Error(
                        data.error ||
                        "Project creation failed"
                    );
                }

                if (newProjectModal) {
                    newProjectModal.hidden = true;
                }

                if (newProjectName) {
                    newProjectName.value = "";
                }

                if (newProjectDescription) {
                    newProjectDescription.value = "";
                }

                await loadProjects();

                if (data.project?.id) {
                    await activateProject(
                        data.project.id
                    );
                }

            } catch (error) {
                console.error(
                    "[Nova Projects] create failed",
                    error
                );

                setProjectStatus(
                    error.message ||
                    "Project creation failed"
                );

            } finally {
                createNewProjectButton.disabled = false;
            }
        }
    );
}

window.NovaDesktopProjects = {
    loadProjects,
    activateProject,
    loadProjectWorkspace,
    renderProjects,
    continueProject,
    runAllProject,
    controlProjectExecution,
};



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

    await controlProjectExecution(
        projectId,
        "continue"
    );
}


async function runAllProject(projectId) {
    if (!projectId) {
        return;
    }

setProjectStatus(
    "Running all project tasks..."
);

setProjectExecutionStatus(
    "Running project workflow...",
    "running"
);

    try {
        const response =
            await fetch(
                `/api/projects/${encodeURIComponent(
                    projectId
                )}/run-all`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json",
                    },
                }
            );

        const data =
            await response.json();

        if (
            !response.ok ||
            !data.ok
        ) {
            throw new Error(
                data.error ||
                "Run all project tasks failed."
            );
        }

        console.log(
            "[NOVA PROJECT RUN ALL]",
            data
        );

        setProjectStatus(
            data.message ||
            "Project execution completed."
        );

setProjectExecutionStatus(
    "Completed",
    "completed"
);

        await loadProjectWorkspace(
            projectId
        );

        await loadProjectIntelligence(
            projectId
        );

        if (
            typeof loadProjects ===
            "function"
        ) {
            await loadProjects();
        }

    } catch (error) {
        console.error(
            "[NOVA PROJECT RUN ALL ERROR]",
            error
        );

        setProjectStatus(
            error.message ||
            "Run all project tasks failed."
        );
    }
}


async function controlProjectExecution(
    projectId,
    action
) {
    if (!projectId) {
        return;
    }

setProjectStatus(
    "Executing..."
);

setProjectExecutionStatus(
    `Execution ${action}...`,
    "running"
);

    try {
        const response =
            await fetch(
                `/api/projects/${encodeURIComponent(
                    projectId
                )}/execution/control`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json",
                    },
                    body: JSON.stringify({
                        action,
                    }),
                }
            );

        const data =
            await response.json();

        if (
            !response.ok ||
            !data.ok
        ) {
            throw new Error(
                data.error ||
                `Execution ${action} failed.`
            );
        }

        console.log(
            "[NOVA PROJECT EXECUTION]",
            data
        );

        setProjectStatus(
            data.message ||
            `Project execution ${action}.`
        );

setProjectExecutionStatus(
    action === "continue"
        ? "Continuing workflow"
        : "Execution updated",
    "completed"
);

        await loadProjectWorkspace(
            projectId
        );

        await loadProjectIntelligence(
            projectId
        );

    } catch (error) {
        console.error(
            "[NOVA PROJECT EXECUTION ERROR]",
            error
        );

        setProjectStatus(
            error.message ||
            "Project execution failed."
        );
    }
}

async function controlProjectExecution(
    projectId,
    action
) {
    if (!projectId) {
        return;
    }

    setProjectStatus(
        "Executing..."
    );

    try {
        const response =
            await fetch(
                `/api/projects/${encodeURIComponent(
                    projectId
                )}/execution/control`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json",
                    },
                    body: JSON.stringify({
                        action,
                    }),
                }
            );

        const data =
            await response.json();

        if (
            !response.ok ||
            !data.ok
        ) {
            throw new Error(
                data.error ||
                `Execution ${action} failed.`
            );
        }

        console.log(
            "[NOVA PROJECT EXECUTION]",
            data
        );

        setProjectStatus(
            data.message ||
            `Project execution ${action}.`
        );

        await loadProjectWorkspace(
            projectId
        );

        await loadProjectIntelligence(
            projectId
        );

    } catch (error) {
        console.error(
            "[NOVA PROJECT EXECUTION ERROR]",
            error
        );

        setProjectStatus(
            error.message ||
            "Project execution failed."
        );
    }
}


const projectUploadButton =
    $("desktopProjectUploadButton");

const projectFileInput =
    $("desktopProjectFileInput");

if (
    projectUploadButton &&
    projectFileInput
) {
    projectUploadButton.addEventListener(
        "click",
        () => {
            projectFileInput.click();
        }
    );
}

if (projectFileInput) {
    projectFileInput.addEventListener(
        "change",
        async () => {
            const file =
                projectFileInput.files?.[0];

            const projectId =
                window.__NOVA_PROJECT_STATE
                    ?.activeProjectId;

            if (
                !file ||
                !projectId
            ) {
                return;
            }

            const formData =
                new FormData();

            formData.append(
                "file",
                file
            );

            formData.append(
                "project_id",
                projectId
            );

            try {
                setProjectStatus(
                    "Uploading file..."
                );

                const response =
                    await fetch(
                        "/api/upload",
                        {
                            method: "POST",
                            body: formData,
                        }
                    );

                const data =
                    await response.json();

                if (
                    !response.ok ||
                    !data.ok
                ) {
                    throw new Error(
                        data.error ||
                        "Upload failed"
                    );
                }

                await loadProjectFiles(
                    projectId
                );

                await loadProjectNotes(
                    projectId
                );

                await loadProjectIntelligence(
                    projectId
                );

                setProjectStatus(
                    "File uploaded"
                );

            } catch (error) {
                console.error(
                    "[Nova Projects] file upload failed",
                    error
                );

                setProjectStatus(
                    error.message ||
                    "File upload failed"
                );

            } finally {
                projectFileInput.value = "";
            }
        }
    );
}


const addNoteButton =
    $("desktopProjectAddNoteButton");

const noteEditor =
    $("desktopProjectNoteEditor");

const noteTitle =
    $("desktopProjectNoteTitle");

const noteContent =
    $("desktopProjectNoteContent");

const saveNoteButton =
    $("desktopProjectSaveNote");

const cancelNoteButton =
    $("desktopProjectCancelNote");

if (
    addNoteButton &&
    noteEditor &&
    noteTitle &&
    noteContent &&
    saveNoteButton &&
    cancelNoteButton
) {
    addNoteButton.addEventListener(
        "click",
        () => {
            noteTitle.value = "";
            noteContent.value = "";

            noteEditor.hidden = false;

            noteTitle.focus();
        }
    );

    cancelNoteButton.addEventListener(
        "click",
        () => {
            noteEditor.hidden = true;

            noteTitle.value = "";
            noteContent.value = "";
        }
    );

    saveNoteButton.addEventListener(
        "click",
        async () => {
            const projectId =
                window.__NOVA_PROJECT_STATE
                    ?.activeProjectId;

            if (!projectId) {
                return;
            }

            const title =
                noteTitle.value.trim();

            const content =
                noteContent.value.trim();

            if (
                !title &&
                !content
            ) {
                return;
            }

            try {
                setProjectStatus(
                    "Saving note..."
                );

                const response =
                    await fetch(
                        `/api/projects/${projectId}/notes`,
                        {
                            method: "POST",
                            headers: {
                                "Content-Type":
                                    "application/json",
                            },
                            body: JSON.stringify({
                                title:
                                    title ||
                                    "Untitled Note",
                                content,
                            }),
                        }
                    );

                const data =
                    await response.json();

                if (
                    !response.ok ||
                    !data.ok
                ) {
                    throw new Error(
                        data.error ||
                        "Could not save note"
                    );
                }

                noteEditor.hidden = true;
                noteTitle.value = "";
                noteContent.value = "";

                await loadProjectNotes(
                    projectId
                );

                await loadProjectIntelligence(
                    projectId
                );

                setProjectStatus(
                    "Note saved"
                );

            } catch (error) {
                console.error(
                    "[Nova Projects] note save failed",
                    error
                );

                setProjectStatus(
                    error.message ||
                    "Note save failed"
                );
            }
        }
    );
}


function bindProjectButtons() {
    if (window.__NOVA_PROJECT_BUTTONS_BOUND) {
        return;
    }

    const newProjectBtn =
        document.getElementById(
            "newProjectBtn"
        );

    if (!newProjectBtn) {
        console.warn(
            "[NOVA PROJECTS] project controls not found"
        );
    }

    window.__NOVA_PROJECT_BUTTONS_BOUND = true;

    console.log(
        "[NOVA PROJECTS] project buttons bound"
    );
}

document.addEventListener(
    "DOMContentLoaded",
    bindProjectButtons
);


})();
