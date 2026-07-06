export async function withRetry(fn, { attempts = 3, baseDelayMs = 300, label = "operation" } = {}) {
    let lastError;
    for (let i = 0; i < attempts; i++) {
        try {
            return await fn();
        } catch (error) {
            lastError = error;
            if (i < attempts - 1) {
                const delay = baseDelayMs * (i + 1);
                console.warn(`Retry ${i + 1}/${attempts - 1} for ${label} after error: ${error.message}`);
                await new Promise((resolve) => setTimeout(resolve, delay));
            }
        }
    }
    throw lastError;
}
