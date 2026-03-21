(() => {
"use strict";

const statusText = document.getElementById("backendStatusText");
const statusDot = document.getElementById("backendStatusDot");

if(!statusText || !statusDot){
  return;
}

function setStatus(connected, authenticated = false){
  if(connected){
    statusDot.style.background = "#10a37f";
    statusText.textContent = authenticated
      ? "Backend connected • logged in"
      : "Backend connected";
    return;
  }

  statusDot.style.background = "#ff6b6b";
  statusText.textContent = "Backend offline";
}

async function checkBackend(){
  try{
    const response = await fetch("/api/health", {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
    });

    if(!response.ok){
      setStatus(false, false);
      return;
    }

    const data = await response.json();
    setStatus(Boolean(data.ok), Boolean(data.authenticated));
  }catch(_error){
    setStatus(false, false);
  }
}

checkBackend();
setInterval(checkBackend, 15000);
})();