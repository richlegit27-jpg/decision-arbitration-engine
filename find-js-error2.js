const fs = require("fs");
const vm = require("vm");

const file = ".\\static\\js\\nova-composer-bundle.js";
const source = fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "");
const lines = source.split(/\r?\n/);

function test(end) {
    let text = lines.slice(0, end).join("\n");

    if (!text.includes("})();")) {
        text += "\n})();";
    }

    try {
        new vm.Script(text);
        return true;
    } catch (e) {
        return false;
    }
}

let lo = 1;
let hi = lines.length;

while (lo < hi) {
    const mid = Math.floor((lo + hi + 1) / 2);

    if (test(mid)) {
        lo = mid;
    } else {
        hi = mid - 1;
    }
}

console.log("TOTAL LINES:", lines.length);
console.log("LAST VALID SECTION:", lo);
console.log("NEXT SECTION:", lo + 1);

console.log("");
console.log("CONTEXT:");

for (
    let i = Math.max(1, lo - 15);
    i <= Math.min(lines.length, lo + 20);
    i++
) {
    console.log(
        String(i).padStart(6) + ": " + lines[i - 1]
    );
}
