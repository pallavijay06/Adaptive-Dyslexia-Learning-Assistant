import api from '../config/api';

export const chatService = {
  sendMessage: async ({ message, document_id, user_id }) => {
    const payload = { message };

    // Only forward a numeric document id. Avoid parseInt on GUIDs which would
    // incorrectly coerce values like "2d555..." -> 2. Prefer integers passed
    // from the backend (saved DB id) or numeric-strings consisting only of digits.
    if (document_id != null) {
      if (Number.isInteger(document_id)) {
        payload.document_id = document_id;
      } else if (typeof document_id === 'string' && /^\d+$/.test(document_id)) {
        payload.document_id = parseInt(document_id, 10);
      }
    }

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
