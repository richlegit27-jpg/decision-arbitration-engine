const fs = require("fs");
const vm = require("vm");

const file = ".\\static\\js\\nova-composer-bundle.js";

let source = fs.readFileSync(file, "utf8")
    .replace(/^\uFEFF/, "")
    .trim();

const lines = source.split(/\r?\n/);

console.log("LINES:", lines.length);
console.log("START:", JSON.stringify(source.slice(0, 40)));
console.log("END:", JSON.stringify(source.slice(-80)));

const firstLine = lines[0];

if (!firstLine.includes("(function () {")) {
    console.log("UNEXPECTED IIFE START:", firstLine);
    process.exit(1);
}

/*
 * Keep the IIFE wrapper so top-level return statements remain legal.
 * Remove only the final wrapper closure and replace it with our own.
 */

let body = source.slice("(function () {".length);

const endMarker = "})();";
const end = body.lastIndexOf(endMarker);

if (end < 0) {
    console.log("FINAL IIFE CLOSURE NOT FOUND");
    process.exit(1);
}

body = body.slice(0, end);

/*
 * Re-wrap the body.
 */
const testSource =
    "(function () {\n" +
    body +
    "\n})();\n";

try {
    new vm.Script(testSource, {
        filename: "nova-composer-wrapper-test.js"
    });

    console.log("");
    console.log("RESULT: CLEAN");
    console.log("The complete bundle parses successfully.");
} catch (e) {
    console.log("");
    console.log("RESULT: BROKEN");
    console.log("ERROR:", e.message);
    console.log("STACK:");
    console.log(e.stack);
}
