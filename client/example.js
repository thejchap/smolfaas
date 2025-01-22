import { run } from ".";

function hello(world, exclamation) {
    return `Hello, ${world}${exclamation}`;
}

console.log(await run(hello, "world", 3));
