(() => {
"use strict";
if(window.__novaThemeLoaded) return;
window.__novaThemeLoaded=true;

const STORAGE_KEY="nova_theme";
const root=document.documentElement;

function getSavedTheme(){ try{return localStorage.getItem(STORAGE_KEY)||"dark"}catch(e){return"dark"} }
function saveTheme(theme){ try{localStorage.setItem(STORAGE_KEY,theme)}catch(e){} }
function applyTheme(theme){ root.setAttribute("data-theme",theme); }

let theme = getSavedTheme();
applyTheme(theme);

window.toggleTheme = ()=>{
    theme = theme==="dark"?"light":"dark";
    applyTheme(theme);
    saveTheme(theme);
};
})();