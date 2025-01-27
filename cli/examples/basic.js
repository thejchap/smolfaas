let count = 0;

export default async function handler() {
    count++;
    console.log(`Request count: ${count}`);
    return {
        result: "hello" + count,
    };
}
