import { deploy } from "..";

function handler(event) {
    console.log(event);
}

await deploy("example", handler);
