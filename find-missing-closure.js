const fs = require("fs");
const vm = require("vm");

const file = ".\\static\\js\\nova-composer-bundle.js";

let source = fs.readFileSync(file, "utf8")
    .replace(/^\uFEFF/, "")
    .trimEnd();

console.log("ORIGINAL LINES:", source.split(/\r?\n/).length);
console.log("ORIGINAL END:");
console.log(source.slice(-300));

const tests = [
    "",
    "\n}",
    "\n});",
    "\n})();",
    "\n}\n})();",
    "\n}\n}\n})();",
    "\n}\n}\n}\n})();"
];

for (const suffix of tests) {
    try {
        new vm.Script(source + suffix, {
            filename: "nova-composer-test.js"
        });

        console.log("");
        console.log("PARSES WITH SUFFIX:");
        console.log(JSON.stringify(suffix));

        process.exit(0);
    } catch (e) {
        console.log(
            "FAIL:",
            JSON.stringify(suffix),
            "|",
            e.message
        );
    }
}

console.log("");
console.log("NONE OF THE SIMPLE CLOSURES FIXED IT.");
