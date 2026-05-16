(() => {
"use strict";

// Ambient blobs
const blobs = document.createElement("div");
blobs.className = "ambient-blobs";
document.body.appendChild(blobs);

for(let i=0;i<6;i++){
    const blob = document.createElement("div");
    blob.className = "blob";
    blob.style.background = `radial-gradient(circle, rgba(16,163,127,0.25), transparent)`;
    blob.style.position = "absolute";
    blob.style.width = `${100+Math.random()*100}px`;
    blob.style.height = `${100+Math.random()*100}px`;
    blob.style.top = `${Math.random()*100}%`;
    blob.style.left = `${Math.random()*100}%`;
    blob.style.filter = "blur(80px)";
    blob.style.pointerEvents = "none";
    blob.style.transition = "all 0.6s ease";
    blobs.appendChild(blob);
}

// Composer bar pulse effect
const composer = document.querySelector(".composer");
if (composer) {
    let pulse = 0;
    setInterval(() => {
        pulse += 0.02;
        const glow = 0.15 + Math.sin(pulse) * 0.05;
        composer.style.boxShadow = `0 0 30px rgba(16,163,127,${glow})`;
    }, 16);
}
})();