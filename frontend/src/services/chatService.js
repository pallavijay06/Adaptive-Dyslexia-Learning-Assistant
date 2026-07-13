import api from '../config/api';

export const chatService = {
  sendMessage: async ({ message, document_id, user_id }) => {
    const payload = { message };

    const parsedDocId = document_id != null ? parseInt(document_id, 10) : NaN;
    if (!Number.isNaN(parsedDocId)) payload.document_id = parsedDocId;

    const parsedUserId = user_id != null ? parseInt(user_id, 10) : NaN;
    if (!Number.isNaN(parsedUserId)) payload.user_id = parsedUserId;

    const response = await api.post('/chat', payload, {
      timeout: 120000,
      headers: { 'Content-Type': 'application/json' },
    });

    if (response.data?.error) {
      throw new Error(response.data.error);
    }

    return response.data;
  },
};
