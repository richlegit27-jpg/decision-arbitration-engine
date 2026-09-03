const fs = require("fs");
const vm = require("vm");

const file = ".\\static\\js\\nova-composer-bundle.js";
const source = fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "");
const lines = source.split(/\r?\n/);

function checkRange(start, end) {
    let text = lines.slice(start - 1, end).join("\n");

    text = `
(function () {
${text}
})();
`;

    try {
        new vm.Script(text);
        return true;
    } catch (e) {
        return false;
    }
}

const ranges = [
    [1, 329],
    [330, 450],
    [451, 800],
    [801, 1200],
    [1201, 1600],
    [1601, 2000],
    [2001, 2400],
    [2401, 2800],
    [2801, 3200],
    [3201, 3600],
    [3601, 4000],
    [4001, 4400],
    [4401, 4800],
    [4801, 5200],
    [5201, 5600],
    [5601, 6000],
    [6001, 6400],
    [6401, 6800],
    [6801, 7200],
    [7201, 7600],
    [7601, 7811]
];

for (const [start, end] of ranges) {
    console.log(
        start + "-" + end + ":",
        checkRange(start, end) ? "OK" : "FAIL"
    );
}
