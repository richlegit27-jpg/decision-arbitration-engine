// C:\Users\Owner\nova\static\js\image-lightbox.js

(() => {
"use strict"

let initialized = false

function ensureLightbox(){
  let root = document.getElementById("novaImageLightbox")

  if(root){
    return root
  }

  root = document.createElement("div")
  root.id = "novaImageLightbox"
  root.className = "nova-image-lightbox"
  root.hidden = true

  root.innerHTML = `
    <div class="nova-image-lightbox-backdrop" data-lightbox-close="true"></div>
    <div class="nova-image-lightbox-dialog" role="dialog" aria-modal="true" aria-label="Image preview">
      <button
        type="button"
        class="nova-image-lightbox-close"
        data-lightbox-close="true"
        aria-label="Close image preview"
      >
        ✕
      </button>
      <img
        id="novaImageLightboxImg"
        class="nova-image-lightbox-img"
        src=""
        alt=""
      >
    </div>
  `

  document.body.appendChild(root)
  return root
}

function getImageSource(anchor){
  if(!anchor){
    return ""
  }

  return String(
    anchor.getAttribute("href") ||
    anchor.dataset.lightboxSrc ||
    ""
  ).trim()
}

function getImageAlt(anchor){
  if(!anchor){
    return "image preview"
  }

  const img = anchor.querySelector("img")
  if(img && img.getAttribute("alt")){
    return String(img.getAttribute("alt") || "").trim() || "image preview"
  }

  return String(anchor.dataset.lightboxAlt || "image preview").trim()
}

function openLightbox(src, alt){
  const root = ensureLightbox()
  const img = root.querySelector("#novaImageLightboxImg")

  if(!img){
    return
  }

  img.src = String(src || "")
  img.alt = String(alt || "image preview")
  root.hidden = false
  document.body.classList.add("nova-lightbox-open")
}

function closeLightbox(){
  const root = document.getElementById("novaImageLightbox")
  if(!root){
    return
  }

  const img = root.querySelector("#novaImageLightboxImg")
  if(img){
    img.src = ""
    img.alt = ""
  }

  root.hidden = true
  document.body.classList.remove("nova-lightbox-open")
}

function bindEvents(){
  if(initialized){
    return
  }

  document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null
    if(!target){
      return
    }

    const closeTarget = target.closest("[data-lightbox-close='true']")
    if(closeTarget){
      event.preventDefault()
      closeLightbox()
      return
    }

    const imageAnchor = target.closest(".message-image")
    if(imageAnchor){
      event.preventDefault()

      const src = getImageSource(imageAnchor)
      if(!src){
        return
      }

      openLightbox(src, getImageAlt(imageAnchor))
    }
  })

  document.addEventListener("keydown", (event) => {
    if(event.key === "Escape"){
      closeLightbox()
    }
  })

  initialized = true
}

function init(){
  ensureLightbox()
  bindEvents()
}

window.NovaImageLightbox = {
  init,
  open: openLightbox,
  close: closeLightbox,
}

})()