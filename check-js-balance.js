const fs = require("fs");

const file = "C:\\Users\\Owner\\nova\\static\\js\\nova-composer-bundle.js";
const s = fs.readFileSync(file, "utf8");

let stack = [];
let line = 1;
let quote = null;
let template = false;
let escaped = false;
let lineComment = false;
let blockComment = false;

for (let i = 0; i < s.length; i++) {
    const c = s[i];
    const n = s[i + 1];

    if (lineComment) {
        if (c === "\n") {
            lineComment = false;
            line++;
        }
        continue;
    }

    if (blockComment) {
        if (c === "*" && n === "/") {
            blockComment = false;
            i++;
            continue;
        }

        if (c === "\n") {
            line++;
        }

        continue;
    }

    if (quote) {
        if (escaped) {
            escaped = false;
            continue;
        }

        if (c === "\\") {
            escaped = true;
            continue;
        }

        if (c === quote) {
            quote = null;
        }

        continue;
    }

    if (template) {
        if (escaped) {
            escaped = false;
            continue;
        }

        if (c === "\\") {
            escaped = true;
            continue;
        }

        if (c === "`") {
            template = false;
        }

        continue;
    }

    if (c === "/" && n === "/") {
        lineComment = true;
        i++;
        continue;
    }

    if (c === "/" && n === "*") {
        blockComment = true;
        i++;
        continue;
    }

    if (c === "'" || c === '"') {
        quote = c;
        continue;
    }

    if (c === "`") {
        template = true;
        continue;
    }

    if (c === "{" || c === "(" || c === "[") {
        stack.push({
            char: c,
            line: line,
            index: i
        });
        continue;
    }

    if (c === "}" || c === ")" || c === "]") {
        const expected = {
            "}": "{",
            ")": "(",
            "]": "["
        }[c];

        if (stack.length === 0) {
            console.log("EXTRA:", c, "at line", line);
            continue;
        }

        const top = stack[stack.length - 1];

        if (top.char !== expected) {
            console.log(
                "MISMATCH:",
                "found",
                c,
                "at line",
                line,
                "opened:",
                top.char,
                "at line",
                top.line
            );
        }

        stack.pop();
    }

    if (c === "\n") {
        line++;
    }
}

console.log("");
console.log("TOTAL LINES:", s.split("\n").length);
console.log("UNMATCHED OPENINGS:", stack.length);
console.log("");

for (const x of stack) {
    console.log(
        "OPEN",
        x.char,
        "at line",
        x.line,
        "index",
        x.index
    );
}

console.log("");
console.log("quote:", quote);
console.log("template:", template);
console.log("blockComment:", blockComment);
console.log("lineComment:", lineComment);
