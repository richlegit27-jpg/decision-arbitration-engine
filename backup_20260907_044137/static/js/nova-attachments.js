window.Nova = window.Nova || {};
window.Nova.addAttachment = function(url, type = "image") {
  const msgDiv = document.createElement("div");
  msgDiv.className = "nova-msg-attachment";
  let el;
  if (type === "image") el = document.createElement("img"), el.src = url;
  else if (type === "video") el = document.createElement("video"), el.src = url, el.controls = true;
  else el = document.createElement("iframe"), el.src = url;
  msgDiv.appendChild(el);
  document.getElementById("messages").appendChild(msgDiv);
};

