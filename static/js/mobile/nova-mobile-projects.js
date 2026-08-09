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
`;

                button.addEventListener(
                    "click",
                    () => {
                        window.location.href =
                            `/mobile?project_id=${encodeURIComponent(project.id)}`;
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

    window.NovaLoadMobileProjects =
        loadMobileProjects;

    document.addEventListener(
        "DOMContentLoaded",
        loadMobileProjects
    );
})();