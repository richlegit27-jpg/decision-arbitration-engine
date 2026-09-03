const fs = require("fs");
const vm = require("vm");

const file = ".\\static\\js\\nova-composer-bundle.js";
const source = fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "");

const lines = source.split(/\r?\n/);

function test(end) {
    const text = lines.slice(0, end).join("\n");

    try {
        new vm.Script(text);
        return true;
    } catch (e) {
        return false;
    }
}

let lastGood = 0;

for (let i = 1; i <= lines.length; i++) {
    if (test(i)) {
        lastGood = i;
    }
}

console.log("TOTAL LINES:", lines.length);
console.log("LAST PARSABLE PREFIX:", lastGood);

for (
    let i = Math.max(1, lastGood - 10);
    i <= Math.min(lines.length, lastGood + 30);
    i++
) {
    console.log(
        String(i).padStart(6) + ": " + lines[i - 1]
    );
}
