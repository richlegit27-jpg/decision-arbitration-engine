const fs = require("fs");
const vm = require("vm");

const file = ".\\static\\js\\nova-composer-bundle.js";

let source = fs.readFileSync(file, "utf8")
    .replace(/^\uFEFF/, "")
    .trim();

console.log("LINES:", source.split(/\r?\n/).length);
console.log("START:", JSON.stringify(source.slice(0, 40)));
console.log("END:", JSON.stringify(source.slice(-80)));

const start = source.indexOf("(function () {");

if (start !== 0) {
    console.log("UNEXPECTED IIFE START");
    process.exit(1);
}

/*
 * Remove the opening wrapper.
 */
let body = source.slice("(function () {".length);

/*
 * Remove the final wrapper closure if present.
 */
const endMarker = "})();";
const end = body.lastIndexOf(endMarker);

if (end >= 0) {
    body = body.slice(0, end);
}

/*
 * Parse the body as ordinary JavaScript.
 */
try {
    new vm.Script(body, {
        filename: "nova-composer-body.js"
    });

    console.log("");
    console.log("RESULT: BODY PARSES CLEAN");
    console.log("The problem is in the IIFE wrapper/closure.");
} catch (e) {
    console.log("");
    console.log("RESULT: BODY STILL BROKEN");
    console.log("ERROR:", e.message);
    console.log(e.stack);
}
