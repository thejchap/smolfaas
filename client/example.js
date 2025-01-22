import { run } from ".";

function hello(world, exclamation) {
    return `Hello, ${world}${exclamation}`;
}
const result = await run(hello, "world", 3);

console.log(result);
