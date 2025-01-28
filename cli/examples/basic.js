let count = 0;

export default async function handler(payload) {
    count++;
    console.log(`Request count: ${count}`);
    return {
        result: "hello" + count + " " + payload.name,
    };
}
