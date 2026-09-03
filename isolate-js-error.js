const fs = require("fs");
const vm = require("vm");

const file = ".\\static\\js\\nova-composer-bundle.js";
let source = fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "");

/*
 * Temporarily replace the suspicious renderedText cleanup chain.
 */
source = source.replace(
    /renderedText = String\(renderedText \|\| ""\)[\s\S]*?\.replace\(\/href=""\/g, 'href="#"'\);/,
    'renderedText = String(renderedText || "");'
);

/*
 * Temporarily replace the imageHtml template.
 */
source = source.replace(
    /const imageHtml = imageUrl[\s\S]*?: "";/,
    'const imageHtml = "";'
);

try {
    new vm.Script(source, {
        filename: "nova-composer-bundle-test.js"
    });

    console.log("RESULT: CLEAN AFTER REMOVING BOTH SUSPECT BLOCKS");
} catch (e) {
    console.log("RESULT: STILL BROKEN");
    console.log("ERROR:", e.message);
    console.log(e.stack);
}
