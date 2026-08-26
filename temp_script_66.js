
document.addEventListener(
    "DOMContentLoaded",
    function () {

        console.log(
            "[Nova Menu Controller] loaded"
        );


        const novaMenuBtn =
            document.getElementById(
                "novaMenuBtn"
            );

        const novaMenuPanel =
            document.getElementById(
                "novaMenuPanel"
            );


        const novaSettingsBtn =
            document.getElementById(
                "novaSettingsBtn"
            );

        const novaAboutBtn =
            document.getElementById(
                "novaAboutBtn"
            );


        if (novaMenuBtn) {

            novaMenuBtn.onclick = function (event) {

                event.stopPropagation();

                console.log(
                    "[Nova Menu] PANEL TOGGLE"
                );

                if (novaMenuPanel) {

                    novaMenuPanel.hidden =
                        !novaMenuPanel.hidden;

                }

            };

        }


        if (novaSettingsBtn) {

            novaSettingsBtn.onclick = function () {

                console.log(
                    "[Nova Menu] Settings OPEN"
                );

                const modal =
                    document.getElementById(
                        "novaSettingsModal"
                    );

                if (modal) {

                    modal.removeAttribute(
                        "hidden"
                    );

                }

            };

        }


        if (novaAboutBtn) {

            novaAboutBtn.onclick = function () {

                console.log(
                    "[Nova Menu] About OPEN"
                );

                const modal =
                    document.getElementById(
                        "novaAboutModal"
                    );

                if (modal) {

                    modal.removeAttribute(
                        "hidden"
                    );

                }

            };

        }


        document.addEventListener(
            "click",
            function (event) {

                if (!novaMenuPanel) {
                    return;
                }


                if (
                    event.target.closest(
                        "#novaMenuBtn"
                    )
                ) {
                    return;
                }


                if (
                    novaMenuPanel.contains(
                        event.target
                    )
                ) {
                    return;
                }


                novaMenuPanel.hidden = true;

            }
        );


        const novaSettingsClose =
            document.getElementById(
                "novaSettingsClose"
            );


        if (novaSettingsClose) {

            novaSettingsClose.onclick = function () {

                document
                    .getElementById(
                        "novaSettingsModal"
                    )
                    .setAttribute(
                        "hidden",
                        ""
                    );

            };

        }


        if (novaAboutClose) {

            novaAboutClose.onclick = function () {

                console.log(
                    "[Nova Menu] About CLOSE"
                );

                document
                    .getElementById(
                        "novaAboutModal"
                    )
                    .setAttribute(
                        "hidden",
                        ""
                    );

            };

        }


    }
);

