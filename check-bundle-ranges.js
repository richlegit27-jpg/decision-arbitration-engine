const fs = require("fs");
const vm = require("vm");

const file = ".\\static\\js\\nova-composer-bundle.js";
const source = fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "");
const lines = source.split(/\r?\n/);

function test(start, end) {
    let text = lines.slice(start - 1, end).join("\n");

    text =
        "(function () {\n" +
        text +
        "\n})();";

    try {
        new vm.Script(text);
        return true;
    } catch (e) {
        return false;
    }
}

const ranges = [
    [2580, 2745],
    [2746, 2850],
    [2851, 3000],
    [3001, 3200],
    [3201, 3400],
    [3401, 3600],
    [3601, 3800],
    [3801, 4000],
    [4001, 4200],
    [4201, 4400],
    [4401, 4600],
    [4601, 4800],
    [4801, 5000],
    [5001, 5200],
    [5201, 5400],
    [5401, 5600],
    [5601, 5800],
    [5801, 6000],
    [6001, 6200],
    [6201, 6400],
    [6401, 6600],
    [6601, 6800],
    [6801, 7000],
    [7001, 7200],
    [7201, 7400],
    [7401, 7600],
    [7601, 7810]
];

for (const [start, end] of ranges) {
    console.log(
        start + "-" + end + ":",
        test(start, end) ? "OK" : "FAIL"
    );
}
