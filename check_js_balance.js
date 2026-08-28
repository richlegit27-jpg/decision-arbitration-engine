const fs = require("fs");

const s = fs.readFileSync("./static/js/nova-chat-stream.js","utf8");

let stack = [];
let i = 0;

let state = "normal";

while(i < s.length){

    let c = s[i];
    let n = s[i+1];

    if(state === "linecomment"){
        if(c === "\n") state="normal";
        i++;
        continue;
    }

    if(state === "blockcomment"){
        if(c==="*" && n==="/"){
            state="normal";
            i += 2;
            continue;
        }
        i++;
        continue;
    }

    if(state === "string"){
        if(c==="\\"){
            i += 2;
            continue;
        }
        if(c === '"'){
            state="normal";
        }
        i++;
        continue;
    }

    if(state === "template"){
        if(c==="\\"){
            i += 2;
            continue;
        }
        if(c==="`"){
            state="normal";
        }
        i++;
        continue;
    }

    if(c==="/" && n==="/"){
        state="linecomment";
        i+=2;
        continue;
    }

    if(c==="/" && n==="*"){
        state="blockcomment";
        i+=2;
        continue;
    }

    if(c==='"'){
        state="string";
        i++;
        continue;
    }

    if(c==="`"){
        state="template";
        i++;
        continue;
    }

    if(c==="(" || c==="{" || c==="["){
        stack.push({
            char:c,
            pos:i
        });
    }

    if(c===")" || c==="}" || c==="]"){

        let expected =
            c===")" ? "(" :
            c==="}" ? "{" :
            "[";

        let last = stack.pop();

        if(!last || last.char !== expected){
            console.log("BAD CLOSE",c,"at",i);
            console.log(
                s.slice(Math.max(0,i-100),i+100)
            );
            process.exit();
        }
    }

    i++;
}

console.log("Remaining:");
console.log(stack.slice(-10));