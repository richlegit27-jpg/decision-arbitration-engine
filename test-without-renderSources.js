const fs = require("fs");
const vm = require("vm");

const file = ".\\static\\js\\nova-composer-bundle.js";
let source = fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "");

const startMarker = "function renderSources(";
const start = source.indexOf(startMarker);

if (start < 0) {
    console.log("renderSources START NOT FOUND");
    process.exit(1);
}

const endMarker = "\n  function linkifyText(";
const end = source.indexOf(endMarker, start);

if (end < 0) {
    console.log("renderSources END NOT FOUND");
    process.exit(1);
}

console.log("renderSources START CHARACTER:", start);
console.log("renderSources END CHARACTER:", end);

const replacement =
    "function renderSources(assistantText, meta = {}) {" +
    "\n  return renderMarkdown(String(assistantText || \"\"));" +
    "\n}";

const testSource =
    source.slice(0, start) +
    replacement +
    source.slice(end);

try {
    new vm.Script(testSource, {
        filename: "nova-composer-bundle-test.js"
    });

    console.log("RESULT: CLEAN");
    console.log("renderSources() is NOT the syntax-error source.");
} catch (e) {
    console.log("RESULT: STILL BROKEN");
    console.log("ERROR:", e.message);
    console.log(e.stack);
}
