(function () {

    const MARK =
        "[NOVA COMMAND CENTER]";


    async function loadStatus() {

        try {

            const response =
                await fetch(
                    "/api/backend/readiness",
                    {
                        credentials:
                            "include"
                    }
                );


            const data =
                await response.json();


            renderStatus(data);


        } catch (error) {

            console.error(
                MARK,
                error
            );

            renderOffline();

        }

    }



    function renderStatus(data) {

        const container =
            document.getElementById(
                "nova-status-grid"
            );


        if (!container) {

            return;

        }


        const items = [

            [
                "Backend",
                data.overall_backend_readiness
            ],

            [
                "Memory",
                data.memory_percent
            ],

            [
                "Sessions",
                data.session_percent
            ],

            [
                "Execution",
                data.execution_percent
            ],

            [
                "Planner",
                data.planner_percent
            ]

        ];


        container.innerHTML = "";


        items.forEach(
            function (item) {

                const card =
                    document.createElement(
                        "div"
                    );


                card.className =
                    "telemetry-card";


                card.innerHTML =

                    "<h3>"
                    + item[0]
                    + "</h3>"
                    +

                    "<strong>"
                    + item[1]
                    + "%</strong>";


                container.appendChild(
                    card
                );

            }
        );

    }



    function renderOffline() {

        const container =
            document.getElementById(
                "nova-status-grid"
            );


        if (!container) {

            return;

        }


        container.innerHTML =

            "<div class='telemetry-card'>"
            +
            "<h3>Status</h3>"
            +
            "<strong>Offline</strong>"
            +
            "</div>";

    }



    document.addEventListener(
        "DOMContentLoaded",
        loadStatus
    );


})();