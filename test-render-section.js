const fs = require("fs");
const vm = require("vm");

const file = ".\\static\\js\\nova-composer-bundle.js";
const source = fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "");

const lines = source.split(/\r?\n/);

const start = 2580;
const end = 2720;

const chunk = lines.slice(start - 1, end).join("\n");

const test =
    "(function () {\n" +
    "function renderTest() {\n" +
    chunk +
    "\n}\n" +
    "})();";

try {
    new vm.Script(test, {
        filename: "nova-render-test.js"
    });

    console.log("RESULT: SECTION PARSES");
} catch (e) {
    console.log("RESULT: SECTION FAILS");
    console.log("ERROR:", e.message);
    console.log(e.stack);
}
