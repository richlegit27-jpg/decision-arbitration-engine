
(function () {

const novaSettingsClose =

    document.getElementById(
        "novaSettingsClose"
    );


if (novaSettingsClose) {

    novaSettingsClose.onclick = function () {

        const modal =
            document.getElementById(
                "novaSettingsModal"
            );

        if (modal) {

            modal.setAttribute(
                "hidden",
                ""
            );

        }

    };

}

const novaAboutClose =
    document.getElementById(
        "novaAboutClose"
    );

if (novaAboutClose) {

    novaAboutClose.onclick = function () {

        const modal =
            document.getElementById(
                "novaAboutModal"
            );

        if (modal) {
            modal.setAttribute(
                "hidden",
                ""
            );
        }

    };

}

})();
