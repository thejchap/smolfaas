const baseUrl = "http://localhost:8000";

export async function run(fn, ...args) {
    const res = await fetch(`${baseUrl}/run`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            func: fn.toString(),
            args,
        }),
    });
    if (!res.ok) {
        throw new Error(`failed to run function: ${await res.text()}`);
    }
    const { result } = await res.json();
    return result;
}
