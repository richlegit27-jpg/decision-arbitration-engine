const fs = require("fs");
const vm = require("vm");

const file = ".\\static\\js\\nova-composer-bundle.js";
const source = fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "");

const lines = source.split(/\r?\n/);

function check(text) {
    try {
        new vm.Script(text);
        return true;
    } catch (_) {
        return false;
    }
}

console.log("TOTAL LINES:", lines.length);

const ranges = [
    [1, 1000],
    [1, 2000],
    [1, 3000],
    [1, 4000],
    [1, 5000],
    [1, 6000],
    [1, 6500],
    [1, 7000],
    [1, 7200],
    [1, 7300],
    [1, 7350],
    [1, 7400],
    [1, 7450],
    [1, 7500],
    [1, 7550],
    [1, 7600],
    [1, 7650],
    [1, 7700],
    [1, 7750],
    [1, 7800],
    [1, 7811]
];

for (const [start, end] of ranges) {
    const text = lines.slice(start - 1, end).join("\n");

    console.log(
        start + "-" + end + ":",
        check(text) ? "PARSES" : "FAILS"
    );
}
