import axios from "axios";

const BASE_URL = import.meta.env.BASE_URL || "http://localhost:8000";
const CLIENT = axios.create({
    baseURL: BASE_URL,
    headers: { "Content-Type": "application/json" },
});

export async function run(fn, ...args) {
    const { status, data } = await CLIENT.post(`${BASE_URL}/run`, {
        func: fn.toString(),
        args,
    });
    if (status !== 200) {
        throw new Error(`failed to run function: ${await res.text()}`);
    }
    return data.result;
}
