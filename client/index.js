import axios from "axios";

const BASE_URL = import.meta.env.BASE_URL || "http://localhost:8000";
const CLIENT = axios.create({
    baseURL: BASE_URL,
    headers: { "content-type": "application/json" },
});

export async function run(func, ...args) {
    const { status, data } = await CLIENT.post(`${BASE_URL}/run`, {
        func: func.toString(),
        args,
    });
    if (status !== 200) {
        throw new Error(`failed to run function: ${await res.text()}`);
    }
    return data.result;
}

export async function deploy(name, func) {
    const { status, data } = await CLIENT.post(
        `${BASE_URL}/functions/${name}/deploy`,
        {
            func: func.toString(),
        },
    );
    if (status !== 200) {
        throw new Error(`failed to deploy function: ${await res.text()}`);
    }
    return data.result;
}
