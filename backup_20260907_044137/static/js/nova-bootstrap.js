(() => {
"use strict"

async function waitForNovaAPIs(timeout=3000){
  const start=Date.now()
  while(Date.now()-start<timeout){
    if(window.NovaChatState && window.NovaChatStorage) return { chatStateApi:window.NovaChatState, chatStorageApi:window.NovaChatStorage }
    await new Promise(r=>setTimeout(r,100))
  }
  throw new Error("Nova APIs not ready")
}



(async function launchNovaModules(){
  let apis
  try{ apis = await waitForNovaAPIs() }catch(err){ console.error("Nova bootstrap failed:",err); return }
  const { chatStateApi, chatStorageApi } = apis
  if(window.NovaSidebar) window.NovaSidebar.init({chatStateApi,chatStorageApi})
  if(window.NovaComposer) window.NovaComposer.init({chatStateApi,chatStorageApi})
  if(window.NovaMemoryPanel) window.NovaMemoryPanel.init({chatStateApi})
  if(window.NovaFilesPanel) window.NovaFilesPanel.init({chatStateApi})
  if(window.NovaApp) window.NovaApp.init({chatStateApi,chatStorageApi})
  console.log("Nova frontend fully initialized âœ…")
})()
})();


