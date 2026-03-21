document.addEventListener("DOMContentLoaded", () => {
    const sidebar = document.getElementById("sidebar");
    const toggleBtn = document.getElementById("toggleSidebar");

    const isMobile = () => window.innerWidth <= 900;

    toggleBtn.addEventListener("click", () => {
        if(isMobile()){
            sidebar.classList.toggle("expanded");
        } else {
            if(sidebar.classList.contains("collapsed")){
                sidebar.classList.remove("collapsed");
                sidebar.style.width = "220px";
            } else {
                sidebar.classList.add("collapsed");
                sidebar.style.width = "50px";
            }
        }
    });

    window.addEventListener("resize", () => {
        if(isMobile()){
            sidebar.classList.remove("collapsed");
            sidebar.classList.remove("expanded");
            sidebar.style.left = "-220px";
            sidebar.style.width = "220px";
        } else {
            sidebar.classList.remove("expanded");
            sidebar.style.left = "0";
        }
    });
});