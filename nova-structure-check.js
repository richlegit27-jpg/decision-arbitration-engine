const fs = require("fs");

const file = ".\\static\\js\\nova-composer-bundle.js";
const source = fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "");

let stack = [];

let state = "code";
let quote = null;
let escape = false;
let regexCharClass = false;

let line = 1;
let column = 0;

function position() {
    return {
        line,
        column
    };
}

function advance(c) {
    if (c === "\n") {
        line++;
        column = 0;
    } else {
        column++;
    }
}

function add(type, c) {
    stack.push({
        type,
        char: c,
        line,
        column
    });
}

function remove(expected, c) {
    if (!stack.length) {
        console.log(
            "EXTRA CLOSER:",
            c,
            "at",
            line + ":" + column
        );
        return;
    }

    const top = stack[stack.length - 1];

    if (top.type !== expected) {
        console.log("");
        console.log("STRUCTURAL MISMATCH");
        console.log(
            "Found:",
            c,
            "at",
            line + ":" + column
        );
        console.log(
            "Expected close for:",
            top.char,
            "opened at",
            top.line + ":" + top.column
        );
        console.log("");
    }

    stack.pop();
}

for (let i = 0; i < source.length; i++) {
    const c = source[i];
    const n = source[i + 1];

    if (state === "lineComment") {
        if (c === "\n") {
            state = "code";
        }

        advance(c);
        continue;
    }

    if (state === "blockComment") {
        if (c === "*" && n === "/") {
            advance(c);
            i++;
            advance("/");
            state = "code";
            continue;
        }

        advance(c);
        continue;
    }

    if (state === "string") {
        if (escape) {
            escape = false;
            advance(c);
            continue;
        }

        if (c === "\\") {
            escape = true;
            advance(c);
            continue;
        }

        if (c === quote) {
            state = "code";
            quote = null;
        }

        advance(c);
        continue;
    }

    if (state === "template") {
        if (escape) {
            escape = false;
            advance(c);
            continue;
        }

        if (c === "\\") {
            escape = true;
            advance(c);
            continue;
        }

        if (c === "`") {
            state = "code";
            advance(c);
            continue;
        }

        advance(c);
        continue;
    }

    if (state === "regex") {
        if (escape) {
            escape = false;
            advance(c);
            continue;
        }

        if (c === "\\") {
            escape = true;
            advance(c);
            continue;
        }

        if (c === "[") {
            regexCharClass = true;
            advance(c);
            continue;
        }

        if (c === "]") {
            regexCharClass = false;
            advance(c);
            continue;
        }

        if (c === "/" && !regexCharClass) {
            state = "code";
            advance(c);

            while (/[a-z]/i.test(source[i + 1] || "")) {
                i++;
                advance(source[i]);
            }

            continue;
        }

        advance(c);
        continue;
    }

    if (c === "/" && n === "/") {
        state = "lineComment";
        advance(c);
        i++;
        advance("/");
        continue;
    }

    if (c === "/" && n === "*") {
        state = "blockComment";
        advance(c);
        i++;
        advance("*");
        continue;
    }

    if (c === "'" || c === '"') {
        state = "string";
        quote = c;
        advance(c);
        continue;
    }

    if (c === "`") {
        state = "template";
        advance(c);
        continue;
    }

    if (c === "{") {
        add("}", c);
    } else if (c === "(") {
        add(")", c);
    } else if (c === "[") {
        add("]", c);
    } else if (c === "}") {
        remove("}", c);
    } else if (c === ")") {
        remove(")", c);
    } else if (c === "]") {
        remove("]", c);
    }

    advance(c);
}

console.log("");
console.log("========================================");
console.log("NOVA JS STRUCTURE CHECK");
console.log("========================================");
console.log("Lines:", line);
console.log("Characters:", source.length);
console.log("Final parser state:", state);
console.log("Open structures:", stack.length);
console.log("");

if (stack.length) {
    console.log("UNMATCHED OPEN STRUCTURES:");

    for (const item of stack) {
        console.log(
            item.char +
            " opened at line " +
            item.line +
            ", column " +
            item.column
        );
    }

    console.log("");
    console.log("LAST UNMATCHED STRUCTURE:");

    const last = stack[stack.length - 1];

    console.log(
        "Character:",
        last.char
    );

    console.log(
        "Line:",
        last.line
    );

    console.log(
        "Column:",
        last.column
    );

    const lines = source.split(/\r?\n/);

    console.log("");
    console.log("CONTEXT:");

    for (
        let i = Math.max(1, last.line - 12);
        i <= Math.min(lines.length, last.line + 20);
        i++
    ) {
        console.log(
            String(i).padStart(6) +
            ": " +
            lines[i - 1]
        );
    }
} else {
    console.log("NO UNMATCHED BRACES/PARENS/BRACKETS FOUND.");
}

console.log("");
console.log("========================================");
