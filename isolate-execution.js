const fs = require("fs");
const vm = require("vm");

const file = ".\\static\\js\\nova-composer-bundle.js";
let source = fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "");

const lines = source.split(/\r?\n/);

/*
 * Temporarily remove the execution section.
 *
 * The execution additions begin around the section containing:
 *   /api/execution/stream
 *
 * We locate it by source text rather than guessing a line number.
 */

const startMarker = 'fetch("/api/execution/stream"';

const start = source.indexOf(startMarker);

if (start < 0) {
    console.log("COULD NOT FIND EXECUTION STREAM MARKER");
    process.exit(1);
}

console.log("EXECUTION MARKER CHARACTER:", start);
console.log(
    "EXECUTION MARKER LINE:",
    source.slice(0, start).split(/\r?\n/).length
);

/*
 * Find the function/block containing the execution stream.
 * We remove from the beginning of the enclosing function
 * through the final execution additions before runExec.
 */
const markerLine = source.slice(0, start).split(/\r?\n/).length;

let removeStart = source.lastIndexOf(
    "async function",
    start
);

if (removeStart < 0) {
    removeStart = source.lastIndexOf(
        "function",
        start
    );
}

const removeEnd = source.lastIndexOf(
    "function runExec"
);

if (removeStart < 0 || removeEnd < 0 || removeEnd <= removeStart) {
    console.log("COULD NOT DETERMINE EXECUTION BLOCK");
    console.log("removeStart:", removeStart);
    console.log("removeEnd:", removeEnd);
    process.exit(1);
}

console.log(
    "REMOVING CHARACTERS:",
    removeStart,
    "through",
    removeEnd
);

source =
    source.slice(0, removeStart) +
    "\n" +
    source.slice(removeEnd);

/*
 * Remove the runExec tail too.
 */
const runExecStart = source.lastIndexOf("function runExec");

if (runExecStart >= 0) {
    source =
        source.slice(0, runExecStart) +
        "\n";
}

source += "\n})();\n";

try {
    new vm.Script(source, {
        filename: "nova-composer-bundle-no-execution.js"
    });

    console.log("");
    console.log("RESULT: CLEAN WITHOUT EXECUTION SECTION");
} catch (e) {
    console.log("");
    console.log("RESULT: STILL BROKEN WITHOUT EXECUTION SECTION");
    console.log("ERROR:", e.message);
    console.log(e.stack);
}
