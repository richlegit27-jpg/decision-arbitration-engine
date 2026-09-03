const fs = require("fs");

const file = ".\\static\\js\\nova-composer-bundle.js";
const source = fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "");

let stack = [];

let quote = null;
let template = false;
let blockComment = false;
let lineComment = false;
let escape = false;

function lineAt(pos) {
    return source.slice(0, pos).split(/\r?\n/).length;
}

function push(c, pos) {
    stack.push({
        char: c,
        line: lineAt(pos),
        pos: pos
    });
}

function showContext(pos) {
    const lines = source.split(/\r?\n/);
    const line = lineAt(pos);

    console.log("");
    console.log("========== CONTEXT ==========");

    for (
        let i = Math.max(1, line - 12);
        i <= Math.min(lines.length, line + 12);
        i++
    ) {
        console.log(
            String(i).padStart(6) + ": " + lines[i - 1]
        );
    }

    console.log("=============================");
}

for (let i = 0; i < source.length; i++) {
    const c = source[i];
    const n = source[i + 1];

    if (lineComment) {
        if (c === "\n") {
            lineComment = false;
        }
        continue;
    }

    if (blockComment) {
        if (c === "*" && n === "/") {
            blockComment = false;
            i++;
        }
        continue;
    }

    if (quote) {
        if (escape) {
            escape = false;
            continue;
        }

        if (c === "\\") {
            escape = true;
            continue;
        }

        if (c === quote) {
            quote = null;
        }

        continue;
    }

    if (template) {
        if (escape) {
            escape = false;
            continue;
        }

        if (c === "\\") {
            escape = true;
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

    if (c === '"' || c === "'") {
        quote = c;
        continue;
    }

    if (c === "`") {
        template = true;
        continue;
    }

    if (c === "{" || c === "(" || c === "[") {
        push(c, i);
        continue;
    }

    if (c === "}" || c === ")" || c === "]") {
        const expected =
            c === "}" ? "{" :
            c === ")" ? "(" :
            "[";

        if (stack.length === 0) {
            console.log(
                "EXTRA CLOSING:",
                c,
                "at line",
                lineAt(i)
            );
            showContext(i);
            continue;
        }

        const top = stack[stack.length - 1];

        if (top.char !== expected) {
            console.log("");
            console.log("========== MISMATCH ==========");
            console.log(
                "Found:",
                c,
                "at line",
                lineAt(i)
            );
            console.log(
                "Expected close for:",
                top.char,
                "opened at line",
                top.line
            );
            console.log("Opening character position:", top.pos);
            console.log("Closing character position:", i);
            console.log("==============================");

            showContext(i);

            stack.pop();
            continue;
        }

        stack.pop();
    }
}

console.log("");
console.log("========== FINAL RESULT ==========");
console.log("TOTAL CHARACTERS:", source.length);
console.log("TOTAL LINES:", source.split(/\r?\n/).length);
console.log("OPEN CONSTRUCTS:", stack.length);
console.log("QUOTE:", quote || "none");
console.log("TEMPLATE:", template);
console.log("BLOCK COMMENT:", blockComment);
console.log("LINE COMMENT:", lineComment);
console.log("");

if (stack.length) {
    console.log("========== UNMATCHED OPENINGS ==========");

    for (const item of stack) {
        console.log(
            item.char +
            " opened at line " +
            item.line +
            " character " +
            item.pos
        );
    }

    console.log("");
    console.log("========== LAST UNMATCHED OPENING ==========");

    const last = stack[stack.length - 1];

    showContext(last.pos);
} else {
    console.log("BALANCE: CLEAN");
}
