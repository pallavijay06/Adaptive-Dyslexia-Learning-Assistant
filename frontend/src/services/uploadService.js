import api from '../config/api';

export const uploadService = {
  /**
   * Upload a document file to POST /upload.
   * Returns the full backend response data on success.
   * Throws an Error with a user-friendly message on failure.
   */
  uploadDocument: async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000, // document processing can take time
    });

    if (!response.data?.success) {
      throw new Error(response.data?.error || 'Upload failed.');
    }

    return response.data;
  },
};
