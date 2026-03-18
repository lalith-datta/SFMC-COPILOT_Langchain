const API_BASE_URL = 'http://localhost:8080/api';

/**
 * Send a chat message to the backend
 * @param {string} message - The user's message
 * @param {string} conversationId - Conversation identifier
 * @param {string} preferredModel - LLM preference: "auto" or "gemini"
 * @returns {Promise<{text: string, model: string}>}
 */
export async function sendMessage(message, conversationId = 'default', preferredModel = 'auto') {
    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message,
                conversationId,
                preferredModel,
            }),
        });

        if (!response.ok) {
            const errorBody = await response.text();
            throw new Error(`API error ${response.status}: ${errorBody}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

/**
 * Confirm an action (e.g., user approves creating a Data Extension)
 */
export async function confirmAction(actionId, confirmed) {
    const response = await fetch(`${API_BASE_URL}/chat/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ actionId, confirmed }),
    });

    return await response.json();
}

/**
 * Check backend health status
 * @returns {Promise<{status: string, service: string}>}
 */
export async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (!response.ok) throw new Error(`Health check failed: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('Health check failed:', error);
        return { status: 'DOWN', service: 'SFMC Copilot Backend' };
    }
}
