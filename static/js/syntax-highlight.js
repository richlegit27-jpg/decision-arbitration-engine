/* notepad C:\Users\Owner\nova\static\js\syntax-highlight.js */

(() => {
"use strict";

function highlightCode(){

  const blocks = document.querySelectorAll(".nova-code-block pre code");

  blocks.forEach(block => {

    let text = block.innerText;

    text = text
      .replace(/(function|const|let|var|return|if|else|for|while|class)/g,
      '<span style="color:#8b5cf6">$1</span>')

      .replace(/(".*?"|'.*?')/g,
      '<span style="color:#22c55e">$1</span>')

      .replace(/([0-9]+)/g,
      '<span style="color:#f59e0b">$1</span>');

    block.innerHTML = text;

  });

}

/* run after messages render */

const observer = new MutationObserver(() => {
  highlightCode();
});

observer.observe(document.body,{
  childList:true,
  subtree:true
});

})();