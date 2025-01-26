let count = 0;

export default async function handler() {
    count++;
    return count.toString();
}
