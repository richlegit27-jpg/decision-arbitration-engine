const fs = require("fs");

const s = fs.readFileSync("./static/js/nova-chat-stream.js", "utf8");

let stack = [];
let inStr = null;
let esc = false;

const pairs = {
  ")": "(",
  "}": "{",
  "]": "["
};

for (let i = 0; i < s.length; i++) {
  const c = s[i];

  if (inStr) {
    if (esc) {
      esc = false;
      continue;
    }

    if (c === "\\") {
      esc = true;
      continue;
    }

    if (c === inStr) {
      inStr = null;
    }

    continue;
  }

  if (c === '"' || c === "'" || c === "`") {
    inStr = c;
    continue;
  }

  if (c === "(" || c === "{" || c === "[") {
    stack.push([c, i]);
  }

  if (c === ")" || c === "}" || c === "]") {
    const x = stack.pop();

    if (!x || x[0] !== pairs[c]) {
      console.log("BAD", c, "at", i);
      console.log(s.slice(i - 150, i + 150));
      process.exit();
    }
  }
}

console.log("remaining:", stack);